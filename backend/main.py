import os
import sqlite3
import subprocess
import time
from fastapi import FastAPI
from pydantic import BaseModel
import threading

app = FastAPI()
DB_PATH = "users.db"

# ایجاد دیتابیس در صورت عدم وجود
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, expiry_date TEXT, 
                  traffic_limit INTEGER, used_traffic INTEGER, is_active INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- بخش مدیریت یوزرهای لینوکس ---
def add_linux_user(username, password):
    try:
        # ساخت یوزر بدون دسترسی به شل برای امنیت
        subprocess.run(['sudo', 'useradd', '-m', '-s', '/usr/sbin/nologin', username], check=True)
        subprocess.run(['echo', f'{username}:{password}', '|', 'sudo', 'chpasswd'], shell=True, check=True)
        return True
    except:
        return False

# --- واچ‌داگ برای جلوگیری از مولتی لاگین (هر ۵ ثانیه) ---
def multi_login_checker():
    while True:
        # این دستور یوزرهایی که بیش از یک بار وصل شدن رو پیدا میکنه
        p1 = subprocess.Popen(['who'], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['awk', '{print $1}'], stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        users_list = p2.communicate()[0].decode().split()
        
        counts = {}
        for u in users_list:
            counts[u] = counts.get(u, 0) + 1
            if counts[u] > 1: # اگر بیش از یک اتصال داشت
                # قطع کردن تمام اتصالات یوزر متخلف
                subprocess.run(['sudo', 'pkill', '-u', u])
                print(f"User {u} killed due to multi-login!")
        
        time.sleep(5)

# اجرای واچ‌داگ در پس‌زمینه
threading.Thread(target=multi_login_checker, daemon=True).start()

# --- API ها برای اپلیکیشن و پنل ---
@app.post("/add_user")
def create_user(username: str, password: str, traffic: int, days: int):
    if add_linux_user(username, password):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?, datetime('now', '+{} days'), ?, 0, 1)".format(days), 
                  (username, password, traffic))
        conn.commit()
        conn.close()
        return {"status": "success"}
    return {"status": "failed"}

@app.get("/user_info/{username}")
def get_info(username: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    user = c.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    conn.close()
    if user:
        return {"username": user[0], "expiry": user[2], "traffic_limit": user[3], "used": user[4]}
    return {"status": "not_found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
