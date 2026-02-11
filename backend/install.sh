#!/bin/bash

# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then 
  echo "لطفا اسکریپت را با دسترسی root اجرا کنید (sudo)."
  exit
fi

echo "--- شروع نصب پکیج‌های مورد نیاز ---"
apt update
apt install -y python3 python3-pip vnstat sqlite3 psmisc bc

# نصب کتابخانه‌های پایتون
pip3 install fastapi uvicorn

# راه‌اندازی vnstat برای مانیتورینگ کارت شبکه
systemctl start vnstat
systemctl enable vnstat

echo "--- بررسی و بازیابی بک‌آپ ---"
if [ -f "users.db" ]; then
    echo "فایل دیتابیس پیدا شد. در حال بازسازی یوزرهای سیستم..."
    # استخراج یوزر و پسورد از دیتابیس و ساخت مجدد در لینوکس
    users=$(sqlite3 users.db "SELECT username, password FROM users;")
    for row in $users; do
        user=$(echo $row | cut -d'|' -f1)
        pass=$(echo $row | cut -d'|' -f2)
        if ! id "$user" &>/dev/null; then
            useradd -m -s /usr/sbin/nologin "$user"
            echo "$user:$pass" | chpasswd
            echo "یوزر $user با موفقیت بازیابی شد."
        fi
    done
else
    echo "دیتابیس قبلی یافت نشد. یک دیتابیس جدید ساخته خواهد شد."
fi

echo "--- نصب به پایان رسید ---"
echo "حالا می‌توانید با دستور زیر سرور را اجرا کنید:"
echo "python3 main.py"
