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

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (username TEXT PRIMARY KEY, password TEXT, expiry_date TEXT, 
                  traffic_limit_gb INTEGER, used_traffic_mb REAL, is_active INTEGER)''')
    conn.commit()
    conn.close()

init_db()

def manage_user(username, password=None, action="add"):
    try:
        if action == "add":
            subprocess.run(['sudo', 'useradd', '-m', '-s', '/usr/sbin/nologin', username], check=True)
            subprocess.run(['sh', '-c', f'echo "{username}:{password}" | sudo chpasswd'], check=True)
        elif action == "kill":
            subprocess.run(['sudo', 'pkill', '-u', username])
        return True
    except: return False

def security_watcher():
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Multi-login prevention
            who_out = subprocess.check_output(['who']).decode()
            connected = [line.split()[0] for line in who_out.splitlines()]
            counts = {}
            for u in connected:
                counts[u] = counts.get(u, 0) + 1
                if counts[u] > 1: manage_user(u, action="kill")
            # Expiry check
            c.execute("SELECT username FROM users WHERE expiry_date < datetime('now') AND is_active = 1")
            for (u,) in c.fetchall():
                manage_user(u, action="kill")
                c.execute("UPDATE users SET is_active = 0 WHERE username = ?", (u,))
            conn.commit()
            conn.close()
        except: pass
        time.sleep(5)

threading.Thread(target=security_watcher, daemon=True).start()

class UserIn(BaseModel):
    username: str
    password: str
    traffic_gb: int
    days: int

@app.post("/api/add")
def add_user(user: UserIn):
    if manage_user(user.username, user.password, "add"):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users VALUES (?, ?, datetime('now', '+{} days'), ?, 0, 1)".format(user.days), 
                      (user.username, user.password, user.traffic_gb))
            conn.commit()
            return {"status": "success"}
        except: return {"status": "exists"}
        finally: conn.close()
    return {"status": "error"}

@app.get("/api/status")
def get_status():
    return {"status": "online", "server_time": str(datetime.now())}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
