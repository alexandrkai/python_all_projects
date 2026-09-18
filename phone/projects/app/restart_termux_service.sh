#!/data/data/com.termux/files/usr/bin/bash
# restart_termux_service.sh

# Останавливаем все python процессы сервиса
pkill -f "python.*run.py"
pkill -f "uvicorn"

# Ждем
sleep 2

# Запускаем заново
cd /path/to/your/project/app
nohup python run.py > api.log 2>&1 &

echo "Termux сервис перезапущен"