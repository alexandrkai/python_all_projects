Если ключ ещё не сгенерирован и не скопирован на сервер, выполните в PowerShell:
PowerShell



ssh-keygen -t ed25519
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh kai@89.125.188.172 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

Как проверить: выполните ssh kai@89.125.188.172 — вход должен происходить мгновенно без запроса пароля.


3Создание отдельного профиля — лучший подход: ваш основной Firefox останется со стандартным интернетом, а профиль для туннеля будет ходить исключительно через сервер. Они смогут работать даже одновременно.1.Создайте новый профиль Firefox:Нажмите сочетание клавиш Win + R.Введите команду и нажмите Enter:DOS
firefox -P
В открывшемся менеджере профилей нажмите Создать... (Create Profile).Нажмите Далее, в поле имени введите, например: ProxyProfile.Завершите мастер кнопкой Готово.Выберите созданный ProxyProfile и нажмите Запустить Firefox.2.Настройте SOCKS5 внутри нового профиля:В открывшемся окне нового профиля настройте маршрутизацию:Перейдите в Настройки → прокрутите вниз до Параметры сети → нажмите Настроить...Выберите Ручная настройка прокси.Заполните строку Узел SOCKS:Сервер: 127.0.0.1Порт: 9090Тип: SOCKS v5Включите галочку: «Отправлять DNS-запросы через прокси при использовании SOCKS v5» (Proxy DNS when using SOCKS v5).Нажмите ОК и закройте это окно Firefox.3.Соберите итоговый .bat скрипт:Создайте или обновите ваш файл start_tunnel.bat.Параметр -P "ProxyProfile" указывает запускать настроенный профиль, а ключ -no-remote позволяет запустить его параллельно с уже открытым основным Firefox в независимом процессе:DOS

@echo off
title Tunnel Manager

echo [1/3] Starting SSH tunnel...
start /min "SSHTunnel" ssh -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -D 9090 -C -N kai@89.125.188.172

echo [2/3] Waiting for connection...
timeout /t 3 /nobreak >nul

echo [3/3] Launching Proxy Firefox profile...
start /wait "" "C:\Program Files\Mozilla Firefox\firefox.exe" -P "ProxyProfile" -no-remote

echo Closing SSH tunnel...
taskkill /FI "WINDOWTITLE eq SSHTunnel*" /T /F >nul 2>&1