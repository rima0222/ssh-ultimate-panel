#!/bin/bash

# ====================================================
# SSH Ultimate Panel - Installer & Auto-Config
# ====================================================

# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then 
  echo "Error: Please run as root (use sudo)."
  exit 1
fi

echo "------------------------------------------"
echo "Step 1: Updating System & Installing Tools"
echo "------------------------------------------"
apt update -y
apt install -y python3 python3-pip vnstat sqlite3 psmisc bc curl git

# نصب کتابخانه‌های پایتون مورد نیاز برای FastAPI
echo "Step 2: Installing Python Dependencies"
pip3 install fastapi uvicorn pydantic

# تنظیمات Vnstat برای مانیتورینگ حجم
echo "Step 3: Configuring Traffic Monitor"
systemctl start vnstat
systemctl enable vnstat

echo "------------------------------------------"
echo "Step 4: Database & User Recovery"
echo "------------------------------------------"

# بررسی وجود دیتابیس برای بازیابی یوزرها (Migration Support)
if [ -f "users.db" ]; then
    echo "[!] Backup found. Restoring users to Linux system..."
    # استخراج یوزرها از دیتابیس و ساخت مجدد در لینوکس
    # فرمت خروجی sqlite: username|password
    sqlite3 users.db "SELECT username, password FROM users;" | while read -r line; do
        user=$(echo "$line" | cut -d'|' -f1)
        pass=$(echo "$line" | cut -d'|' -f2)
        
        if ! id "$user" &>/dev/null; then
            useradd -m -s /usr/sbin/nologin "$user"
            echo "$user:$pass" | chpasswd
            echo "Successfully restored user: $user"
        else
            echo "User $user already exists, skipping..."
        fi
    done
else
    echo "[+] No backup found. Starting with a clean database."
fi

echo "------------------------------------------"
echo "Step 5: Setting Permissions"
echo "------------------------------------------"
# اجازه دسترسی به پورت ۵۰۰۰ در فایروال (در صورت فعال بودن)
if command -v ufw > /dev/null; then
    ufw allow 5000/tcp
fi

chmod +x main.py

echo "------------------------------------------"
echo "INSTALLATION COMPLETE!"
echo "------------------------------------------"
echo "To start the server, run:"
echo "python3 main.py"
echo "------------------------------------------"
