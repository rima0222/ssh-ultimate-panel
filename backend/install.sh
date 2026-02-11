#!/bin/bash
# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then 
  echo "لطفا با sudo اجرا کنید"
  exit 1
fi

echo "--- در حال نصب پیش‌نیازهای سیستم ---"
apt update -y
apt install -y python3 python3-pip vnstat sqlite3 psmisc bc curl

# نصب کتابخانه‌های پایتون با متد دور زدن محدودیت اوبونتو جدید
echo "--- نصب کتابخانه‌های پایتون ---"
pip3 install fastapi uvicorn pydantic --break-system-packages

# فعال‌سازی vnstat
systemctl start vnstat
systemctl enable vnstat

echo "--- بررسی دیتابیس برای بازیابی کاربران ---"
if [ -f "users.db" ]; then
    sqlite3 users.db "SELECT username, password FROM users;" | while read -r line; do
        user=$(echo "$line" | cut -d'|' -f1)
        pass=$(echo "$line" | cut -d'|' -f2)
        if ! id "$user" &>/dev/null; then
            useradd -m -s /usr/sbin/nologin "$user"
            echo "$user:$pass" | chpasswd
            echo "کاربر $user بازیابی شد."
        fi
    done
fi

echo "--- نصب با موفقیت تمام شد ---"
