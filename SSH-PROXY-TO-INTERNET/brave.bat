@echo off
title Brave SSH Proxy Launcher

:: 1. Закрываем зависшие процессы туннеля
taskkill /F /IM ssh.exe >nul 2>&1

:: 2. Запускаем туннель на стабильном 443 порту
echo [1/3] Starting SSH tunnel...
start /min "SSHTunnel" ssh -p 443 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -D 9090 -N kai@89.125.188.172

:: 3. Ждем готовности порта 9090
echo [2/3] Waiting for port 9090...
:wait_port
timeout /t 1 /nobreak >nul
netstat -ano | findstr 127.0.0.1:9090 | findstr LISTENING >nul
if errorlevel 1 goto wait_port

:: 4. Запускаем изолированный Brave и ждем закрытия окна
echo [3/3] Brave Proxy Profile is running. Close it to exit...
powershell -NoProfile -Command "$p = Start-Process 'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe' -ArgumentList '--proxy-server=\"socks5://127.0.0.1:9090\"', '--user-data-dir=\"%~dp0brave_proxy_profile\"' -PassThru; $p.WaitForExit()"

:: 5. После закрытия браузера завершаем SSH
echo Brave closed. Terminating SSH tunnel...
taskkill /F /IM ssh.exe >nul 2>&1
echo Done.