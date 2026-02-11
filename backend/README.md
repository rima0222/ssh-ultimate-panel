:

```bash
cd ~ && rm -rf ssh-ultimate-panel && git clone [https://github.com/rima0222/ssh-ultimate-panel.git](https://github.com/rima0222/ssh-ultimate-panel.git) && cd ssh-ultimate-panel/backend && chmod +x install.sh && sudo ./install.sh && pip3 install fastapi uvicorn pydantic --break-system-packages && python3 main.py
