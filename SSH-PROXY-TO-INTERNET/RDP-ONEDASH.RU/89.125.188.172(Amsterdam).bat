echo off
title SSH Proxy Launcher

:: 1. Очищаем старые сессии туннеля
taskkill /F /IM ssh.exe >nul 2>&1

:: 2. Запускаем туннель
echo [1/3] Starting SSH tunnel...
start /min "SSHTunnel" ssh -p 443 -o ServerAliveInterval=15 -o ServerAliveCountMax=3 -D 9090 -N kai@89.125.188.172

:: 3. Ждем готовности порта 9090
echo [2/3] Waiting for port 9090...
:wait_port
timeout /t 1 /nobreak >nul
netstat -ano | findstr 127.0.0.1:9090 | findstr LISTENING >nul
if errorlevel 1 goto wait_port

:: 4. Запускаем изолированное окно Firefox
echo [3/3] Launching Firefox...
start "" "C:\Program Files\Mozilla Firefox\firefox.exe" -P "ProxyProfile" -no-remote

:: 5. Пауза 3 секунды, чтобы процесс Firefox успел гарантированно появиться в системе
timeout /t 3 /nobreak >nul

:: 6. Цикл отслеживания: пока процесс firefox.exe живет, скрипт ждет
echo Proxy is working. Close Firefox to exit...
:wait_firefox
timeout /t 2 /nobreak >nul
tasklist /FI "IMAGENAME eq firefox.exe" 2>nul | find /I "firefox.exe" >nul
if not errorlevel 1 goto wait_firefox

:: 7. Браузер закрыт — гасим туннель
echo Firefox closed. Terminating SSH tunnel...
taskkill /F /IM ssh.exe >nul 2>&1
echo Done.