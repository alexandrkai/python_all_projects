import shutil
import subprocess
import time

from config.config import Config

from app.core.log.log import get_logger,critical_error_logger

logger = get_logger(__name__)


def check_autossh_available() -> bool:
    """Проверяет наличие autossh в системе."""
    # 1. Быстрая проверка наличия исполняемого файла в PATH
    if shutil.which("autossh") is None:
        return False

    # 2. Тестовый запуск с корректным флагом -V (не --version!)
    try:
        res = subprocess.run(
            ["autossh", "-V"],
            capture_output=True,
            text=True
        )
        # У autossh вывод версии может возвращать 0 или писать в stderr
        print((res.stdout + res.stderr).lower())
        return res.returncode == 0 or "autossh" in (res.stdout + res.stderr).lower()
    except Exception:
        critical_error_logger.error("Ошибка определения наличия autossh")
        return False

def is_tunnel_running(port, remote, ssh_port):
    """
    Проверяет, запущен ли SSH-туннель с указанным локальным портом,
    удалённым хостом и SSH-портом.
    Использует pgrep (если есть) или ps aux | grep.
    """
    ssh_port = int(ssh_port)

    # Способ 1: pgrep. Ищем одновременно: -D <port>, -p <ssh_port>, <remote>
    # Порядок флагов в командной строке может отличаться, поэтому ищем
    # каждый фрагмент отдельно, а не одной строкой шаблона.
    try:
        result = subprocess.run(
            ["pgrep", "-af", "ssh"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if (
                    f"-D {port}" in line
                    and f"-p {ssh_port}" in line
                    and remote in line
                ):
                    return True
            # pgrep сработал, но совпадений нет — можно сразу вернуть False,
            # однако оставим fallback на ps на случай особенностей Termux.
    except FileNotFoundError:
        # pgrep нет — используем ps
        pass

    # Способ 2: ps aux | grep (универсальный)
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True,
        )
        for line in result.stdout.splitlines():
            if (
                "ssh" in line
                and f"-D {port}" in line
                and f"-p {ssh_port}" in line
                and remote in line
                and "grep" not in line
            ):
                return True
    except Exception as e:
        logger.warning(f"⚠️ Не удалось проверить процессы через ps: {e}")

    return False


def start_tunnel(port, remote, user, ssh_port):
    """
    Запускает autossh (если установлен) или обычный ssh с keep-alive.
    Возвращает True при успешном запуске.
    """
    ssh_port = int(ssh_port)

    try:
        use_autossh = check_autossh_available()

        if not use_autossh:
            logger.warning("⚠️autossh не найден, используется обычный ssh (без автоматического перезапуска).")
        else:
            logger.info("🛠️ Используется autossh для поддержания туннеля.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        use_autossh = False
        logger.warning(
            "⚠️ autossh не найден, используется обычный ssh "
            "(без автоматического перезапуска)."
        )

    if use_autossh:
        cmd = [
            "autossh", "-M", "0", "-f", "-N",
            "-D", str(port),
            "-p", str(ssh_port),          # <-- SSH-порт сервера
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            "-o", "ExitOnForwardFailure=yes",
            f"{user}@{remote}",
        ]
    else:
        cmd = [
            "ssh", "-N",
            "-D", str(port),
            "-p", str(ssh_port),          # <-- SSH-порт сервера
            "-o", "ServerAliveInterval=30",
            "-o", "ServerAliveCountMax=3",
            f"{user}@{remote}",
        ]
    print("Выполняем команду"," ".join(cmd))
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        logger.info(
            f"🚀 Туннель запущен (локальный порт {port}, "
            f"ssh-порт {ssh_port}, {user}@{remote})"
        )
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка запуска туннеля: {e}")
        return False


def ensure_tunnel(port:int, remote:str, user:str, ssh_port:int):
    """Главная функция: проверяет и при необходимости запускает туннель."""
    ssh_port = int(ssh_port)
    
    if not is_tunnel_running(port, remote, ssh_port):
        logger.info(
            f"🔍 Туннель не найден, запускаем "
            f"(ssh-порт {ssh_port})..."
        )
        start_tunnel(port, remote, user, ssh_port)
        time.sleep(2)  # Даём время на установку соединения

        if is_tunnel_running(port, remote, ssh_port):
            logger.info("Туннель успешно запущен.")
            setattr(Config, "StartSSHTunnel", True)
        else:
            setattr(Config, "StartSSHTunnel", False)
            logger.error(
                "❌ Не удалось запустить туннель. "
                "Проверьте доступность сервера, порт и ключи/пароль."
            )
    else:
        logger.info("Туннель уже работает.")


# Пример использования (можно вызвать при старте бота)
# if __name__ == "__main__":
    # Для нестандартного SSH-порта:
    # ensure_tunnel(port=9090, remote="89.125.188.172", user="kai", ssh_port=2222)
    # ensure_tunnel()
