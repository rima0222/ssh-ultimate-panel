import os
import sqlite3
import subprocess
import time
import threading
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime

app = FastAPI()
DB_PATH = "users.db"

# --- مقداردهی اولیه دیتابیس ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, expiry_date TEXT, 
                  traffic_limit_gb INTEGER, used_traffic_mb REAL, is_active INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- توابع مدیریت سیستم لینوکس ---
def manage_linux_user(username, password, action="add"):
    try:
        if action == "add":
            subprocess.run(['useradd', '-m', '-s', '/usr/sbin/nologin', username], check=True)
            subprocess.run(['sh', '-c', f'echo "{username}:{password}" | chpasswd'], check=True)
        elif action == "delete":
            subprocess.run(['userdel', '-r', '-f', username], check=True)
        return True
    except Exception as e:
        print(f"Error managing user {username}: {e}")
        return False

def kill_user_sessions(username):
    subprocess.run(['pkill', '-u', username])

# --- واچ‌داگ (هر ۵ ثانیه چک می‌کند) ---
def security_watchdog():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            
            # ۱. چک کردن مولتی لاگین (فقط یک نفر مجاز است)
            # خروجی دستور 'who' لیست افراد متصل را می‌دهد
            who_output = subprocess.check_output(['who']).decode()
            connected_users = [line.split()[0] for line in who_output.splitlines()]
            
            counts = {}
            for u in connected_users:
                counts[u] = counts.get(u, 0) + 1
                if counts[u] > 1:
                    print(f"Violation: {u} tried multi-login. Killing sessions...")
                    kill_user_sessions(u)

            # ۲. چک کردن تاریخ انقضا و حجم (ساده شده)
            # در نسخه پیشرفته‌تر باید خروجی vnstat را برای هر یوزر پارس کنید
            # فعلا یوزرهایی که انقضا یافته‌اند را غیرفعال می‌کنیم
            c.execute("SELECT username FROM users WHERE expiry_date < datetime('now') AND is_active = 1")
            expired_users = c.fetchall()
            for (u,) in expired_users:
                print(f"User {u} expired. Disabling...")
                kill_user_sessions(u)
                c.execute("UPDATE users SET is_active = 0 WHERE username = ?", (u,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Watchdog error: {e}")
        
        time.sleep(5)

# اجرای واچ‌داگ در ترد جداگانه
threading.Thread(target=security_watchdog, daemon=True).start()

# --- مدل‌های داده برای API ---
class UserCreate(BaseModel):
    username: str
    password: str
    traffic_gb: int
    days: int

# --- API Endpoints ---

@app.post("/add_user")
def add_user(user: UserCreate):
    if manage_linux_user(user.username, user.password, "add"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?, ?, datetime('now', '+{} days'), ?, 0, 1)".format(user.days), 
                      (user.username, user.password, user.traffic_gb))
            conn.commit()
            return {"status": "success", "message": f"User {user.username} created"}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="User already exists")
        finally:
            conn.close()
    return {"status": "error", "message": "Failed to create Linux user"}

@app.get("/user_info/{username}")
def get_user(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    
    if row:
        return {
            "username": row[0],
            "expiry": row[2],
            "limit_gb": row[3],
            "used_mb": row[4],
            "status": "Active" if row[5] == 1 else "Expired/Disabled"
        }
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/admin/backup")
def download_db():
    # در فلاتر می‌توانید این فایل را مستقیما دانلود کنید
    if os.path.exists(DB_PATH):
        return {"db_url": f"http://YOUR_SERVER_IP:5000/static/{DB_PATH}"} # نیاز به StaticFiles دارد
    return {"error": "File not found"}

if __name__ == "__main__":
    import uvicorn
    # اجرا روی پورت ۵۰۰۰
    uvicorn.run(app, host="0.0.0.0", port=5000)
