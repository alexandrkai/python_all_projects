pip install aiogram sqlalchemy asyncpg

Поднимите SSH-туннель в отдельном окне терминала:

bash
autossh -M 0 -N \
  -o ServerAliveInterval=15 \
  -o ServerAliveCountMax=3 \
  -o ExitOnForwardFailure=yes \
  -p 443 -D 0.0.0.0:1080 \
  kai@89.125.188.172

Окно оставьте открытым — туннель должен работать всё время, пока запущен бот.

Задайте переменные окружения (или отредактируйте значения по умолчанию в коде):

bash
$env:BOT_TOKEN="123456:ABC..."
$env:DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/botdb"
$env:ADMIN_IDS="123456789"
$env:PROXY_URL="socks5://127.0.0.1:1080"

docker build -t tg-bot .
docker run -d --name tg-bot --restart unless-stopped --add-host=host.docker.internal:host-gateway tg-bot