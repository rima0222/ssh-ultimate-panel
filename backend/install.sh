#!/bin/bash
# SSH Ultimate Installer - Fixed for Ubuntu 24.04
if [ "$EUID" -ne 0 ]; then 
  echo "لطفا با دسترسی روت (sudo) اجرا کنید."
  exit 1
fi

echo "--- در حال نصب پکیج‌های سیستم ---"
apt update -y
apt install -y python3 python3-pip vnstat sqlite3 psmisc bc curl

echo "--- نصب کتابخانه‌های پایتون (رفع تداخل سیستمی) ---"
# استفاده از --ignore-installed برای رد کردن خطای typing-extensions
pip3 install fastapi uvicorn pydantic starlette anyio --break-system-packages --ignore-installed

echo "--- تنظیمات vnstat ---"
systemctl start vnstat
systemctl enable vnstat

echo "--- نصب با موفقیت انجام شد ---"
