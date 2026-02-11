import os
import sqlite3
import subprocess
import time
import threading
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="SSH Ultimate Pro API")
DB_PATH = "users.db"

# --- مرحله ۱: آماده‌سازی دیتابیس ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, expiry_date TEXT, 
                  traffic_limit_gb INTEGER, used_traffic_mb REAL, is_active INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- مرحله ۲: توابع مدیریت سیستم (Linux Interface) ---
def manage_linux_user(username, password, action="add"):
    try:
        if action == "add":
            # ایجاد کاربر بدون شل با امنیت بالا
            subprocess.run(['sudo', 'useradd', '-m', '-s', '/usr/sbin/nologin', username], check=True)
            subprocess.run(['sh', '-c', f'echo "{username}:{password}" | sudo chpasswd'], check=True)
        elif action == "delete":
            subprocess.run(['sudo', 'userdel', '-r', '-f', username], check=True)
        elif action == "kill":
            subprocess.run(['sudo', 'pkill', '-u', username], check=True)
        return True
    except Exception as e:
        print(f"Linux Task Error for {username}: {e}")
        return False

# --- مرحله ۳: سیستم نظارت هوشمند (هر ۵ ثانیه) ---
def security_watcher():
    """
    این تابع وظیفه دارد:
    1. جلوی Multi-login را بگیرد (فقط یک نفر).
    2. یوزرهای منقضی شده را دیسکانکت کند.
    """
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()

            # بررسی اتصال همزمان
            who_proc = subprocess.Popen(['who'], stdout=subprocess.PIPE)
            awk_proc = subprocess.Popen(['awk', '{print $1}'], stdin=who_proc.stdout, stdout=subprocess.PIPE)
            who_proc.stdout.close()
            connected_users = awk_proc.communicate()[0].decode().split()

            user_counts = {}
            for u in connected_users:
                user_counts[u] = user_counts.get(u, 0) + 1
                if user_counts[u] > 1:
                    print(f"!!! Multi-login detected for {u}. Killing sessions...")
                    manage_linux_user(u, None, "kill")

            # بررسی انقضای تاریخ مصرف
            c.execute("SELECT username FROM users WHERE expiry_date < datetime('now') AND is_active = 1")
            expired_list = c.fetchall()
            for (u,) in expired_list:
                print(f"!!! User {u} expired. Disabling access...")
                manage_linux_user(u, None, "kill")
                c.execute("UPDATE users SET is_active = 0 WHERE username = ?", (u,))

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Watcher Error: {e}")
        
        time.sleep(5)

# اجرای ناظر امنیت در پس‌زمینه
threading.Thread(target=security_watcher, daemon=True).start()

# --- مرحله ۴: مدل‌های داده API ---
class UserIn(BaseModel):
    username: str
    password: str
    traffic_gb: int
    days: int

# --- مرحله ۵: نقاط اتصال API (Endpoints) ---

@app.post("/api/add")
def api_add_user(user: UserIn):
    # ابتدا در لینوکس ساخته شود
    if manage_linux_user(user.username, user.password, "add"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            # ذخیره در دیتابیس با محاسبه تاریخ انقضا
            c.execute("INSERT INTO users VALUES (?, ?, datetime('now', '+{} days'), ?, 0, 1)".format(user.days), 
                      (user.username, user.password, user.traffic_gb))
            conn.commit()
            return {"status": "success", "user": user.username}
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=400, detail="User already exists in Database")
        finally:
            conn.close()
    raise HTTPException(status_code=500, detail="Failed to create system user")

@app.get("/api/info/{username}")
def api_get_info(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    
    if row:
        return {
            "username": row[0],
            "expiry": row[2],
            "limit_gb": row[3],
            "used_mb": row[4],
            "is_active": bool(row[5])
        }
    raise HTTPException(status_code=404, detail="User not found")

@app.get("/api/status")
def server_status():
    return {"status": "online", "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

if __name__ == "__main__":
    import uvicorn
    # اجرا روی پورت ۵۰۰۰ برای پنل و اپلیکیشن
    uvicorn.run(app, host="0.0.0.0", port=5000)
