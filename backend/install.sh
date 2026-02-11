#!/bin/bash

# خروج از اسکریپت در صورت بروز خطا
set -e

echo "--- شروع نصب پیش‌نیازهای پنل مدیریت SSH ---"

# مرحله ۱: آپدیت مخازن
echo "[1/5] Updating system..."
sudo apt update -y

# مرحله ۲: نصب ابزارهای مورد نیاز
echo "[2/5] Installing requirements (Python, Vnstat, SQLite)..."
sudo apt install -y python3 python3-pip vnstat sqlite3 bc psmisc

# مرحله ۳: نصب کتابخانه‌های پایتون
echo "[3/5] Installing Python libraries..."
pip3 install fastapi uvicorn

# مرحله ۴: تنظیمات Vnstat (برای محاسبه ترافیک)
echo "[4/5] Starting Vnstat service..."
sudo systemctl start vnstat
sudo systemctl enable vnstat

# مرحله ۵: بررسی فایل بک‌آپ و بازیابی یوزرهای لینوکس
if [ -f "users.db" ]; then
    echo "[!] Backup found! Restoring users to Linux system..."
    # خواندن یوزرها و پسوردها از دیتابیس و ساخت مجدد آن‌ها در لینوکس
    sqlite3 users.db "SELECT username, password FROM users;" | while read -r line; do
        user=$(echo $line | cut -d'|' -f1)
        pass=$(echo $line | cut -d'|' -f2)
        if ! id "$user" &>/dev/null; then
            sudo useradd -m -s /usr/sbin/nologin "$user"
            echo "$user:$pass" | sudo chpasswd
            echo "User $user restored."
        fi
    done
else
    echo "[5/5] No backup found. Starting fresh."
fi

echo "--- نصب با موفقیت انجام شد! ---"
echo "برای اجرا دستور زیر را بزنید:"
echo "python3 main.py"
