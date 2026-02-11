#!/bin/bash
# SSH Ultimate Installer - Optimized for Ubuntu 24.04
if [ "$EUID" -ne 0 ]; then 
  echo "Error: Please run as root (sudo)."
  exit 1
fi

echo "--- Installing System Packages ---"
apt update -y
apt install -y python3 python3-pip vnstat sqlite3 psmisc bc curl

echo "--- Installing Python Libraries (PEP 668 Fix) ---"
pip3 install fastapi uvicorn pydantic --break-system-packages

echo "--- Enabling Services ---"
systemctl start vnstat
systemctl enable vnstat

echo "--- Setup Complete ---"
