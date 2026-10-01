#!/data/data/com.termux/files/usr/bin/python3
# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/restart_service.py
# restart_service.py
import os
import signal
import subprocess
import sys
import time


def restart():
    # Путь к текущему скрипту
    current_dir = os.path.dirname(os.path.abspath(__file__))
    run_py = os.path.join(current_dir, "run.py")
    
    # Читаем текущий PID
    pid_file = os.path.join(current_dir, "api.pid")
    if os.path.exists(pid_file):
        with open(pid_file, "r") as f:
            old_pid = int(f.read().strip())
        
        # Пытаемся мягко остановить старый процесс
        try:
            os.kill(old_pid, signal.SIGTERM)
            print(f"Отправлен SIGTERM процессу {old_pid}")
            time.sleep(2)
            
            # Если процесс еще жив, убиваем жестко
            try:
                os.kill(old_pid, 0)  # Проверяем, существует ли процесс
                os.kill(old_pid, signal.SIGKILL)
                print(f"Отправлен SIGKILL процессу {old_pid}")
            except OSError:
                pass  # Процесс уже завершился
                
        except ProcessLookupError:
            print(f"Процесс {old_pid} не найден")
    
    # Запускаем новый процесс
    print("Запускаем новый процесс...")
    process = subprocess.Popen(
        [sys.executable, run_py],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Сохраняем новый PID
    with open(pid_file, "w") as f:
        f.write(str(process.pid))
    
    print(f"Новый процесс запущен с PID: {process.pid}")
    return process.pid

if __name__ == "__main__":
    restart()