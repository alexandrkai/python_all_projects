import subprocess
import time
from log.log import get_logger

logger=get_logger(__name__)

def is_tunnel_running(port, remote):
    """
    Проверяет, запущен ли SSH-туннель с указанным портом и удалённым хостом.
    Использует pgrep (если есть) или ps aux | grep.
    """
    # Способ 1: pgrep (обычно доступен в Termux после pkg install procps)
    try:
        result = subprocess.run(
            ["pgrep", "-f", f"ssh.*-D {port}.*{remote}"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True
    except FileNotFoundError:
        # pgrep нет, используем ps
        pass

    # Способ 2: ps aux | grep (универсальный)
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if "ssh" in line and f"-D {port}" in line and remote in line:
                if "grep" not in line:   # исключаем сам grep
                    return True
    except Exception:
        pass
    return False

def start_tunnel(port, remote, user):
    """
    Запускает autossh (если установлен) или обычный ssh с keep-alive.
    Возвращает True при успешном запуске.
    """
    # Проверяем, есть ли autossh
    try:
        subprocess.run(["autossh", "--version"], capture_output=True, check=True)
        use_autossh = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        use_autossh = False
        logger.warning("⚠️ autossh не найден, используется обычный ssh (без автоматического перезапуска).")

    if use_autossh:
        cmd = [
            "autossh", "-M", "0", "-f", "-N",
            "-D", str(port),
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            f"{user}@{remote}"
        ]
    else:
        cmd = [
            "ssh", "-N",
            "-D", str(port),
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            f"{user}@{remote}"
        ]

    try:
        # Запускаем процесс в фоне, перенаправляя stdout/stderr в /dev/null
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info(f"🚀 Туннель запущен (порт {port})")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка запуска туннеля: {e}")
        return False

def ensure_tunnel(port=9090, remote="89.125.188.172", user="kai"):
    """Главная функция: проверяет и при необходимости запускает туннель."""
    if not is_tunnel_running(port, remote):
        logger.info("🔍 Туннель не найден, запускаем...")
        start_tunnel(port, remote, user)
        time.sleep(2)  # Даём время на установку соединения
        if is_tunnel_running(port, remote):
            logger.info("✅ Туннель успешно запущен.")
        else:
            logger.error("❌ Не удалось запустить туннель. Проверьте доступность сервера и пароль.")
    else:
        logger.info("✅ Туннель уже работает.")

# Пример использования (можно вызвать при старте бота)
if __name__ == "__main__":
    ensure_tunnel()