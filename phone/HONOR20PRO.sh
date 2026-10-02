/#!/data/data/com.termux/files/usr/bin/sh

# 1. Проверяем, передан ли аргумент имени телефона
# if [ -z "$1" ]; then
#     echo "⚠️ Ошибка: укажите имя телефона!"
#     echo "Использование: sh run.sh "
#     exit 1
# fi

# 2. Экспортируем имя телефона в переменную окружения
export PHONE_NAME="HONOR20PRO"

echo "🚀 Запуск приложения для телефона: $PHONE_NAME"

# 3. Запускаем приложение в фоне с передачей переменной окружения
nohup python app/run.py > api.log 2>&1 &
PID=$!

echo "✅ Приложение запущено в фоне (PID: $PID)"
echo "📝 Логи пишутся в api.log"