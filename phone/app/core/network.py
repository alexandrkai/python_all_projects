import json
import os
import socket
import subprocess
import time

from log.log import get_logger

logger = get_logger(__name__)


def is_termux() -> bool:
    """Быстрая проверка среды Termux по переменным окружения и путям."""
    return (
        "TERMUX_VERSION" in os.environ
        or os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
        or os.path.exists("/data/data/com.termux/files/usr")
    )


class NetworkInterfaceScanner:
    """Лаконичный сканер сетевых параметров с кэшированием."""

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._cache: tuple[str | None, str | None] | None = None
        self._cache_time: float = 0.0

    def get_ip_and_mac(self) -> tuple[str | None, str | None]:
        now = time.time()
        if self._cache and (now - self._cache_time) < self.cache_ttl:
            return self._cache

        ip, mac = self._resolve()
        self._cache = (ip, mac)
        self._cache_time = now
        return ip, mac

    def _resolve(self) -> tuple[str | None, str | None]:
        ip = self._get_local_ip()
        mac = None

        if is_termux():
            # Попытка получить данные через Termux:API (если установлен пакет termux-api)
            termux_ip, termux_mac = self._get_from_termux_api()
            ip = termux_ip or ip
            mac = termux_mac

        if not mac:
            mac = self._get_mac_address()

        return ip, mac

    @staticmethod
    def _get_local_ip() -> str | None:
        """Кроссплатформенное определение рабочего локального IPv4 через UDP-сокет."""
        try:
            # Соединение не отправляет реальных пакетов, но ОС выбирает нужный исходящий интерфейс
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                ip = s.getsockname()[0]
                if not ip.startswith("127."):
                    return ip
        except Exception:
            pass
        return None

    @staticmethod
    def _get_from_termux_api() -> tuple[str | None, str | None]:
        """Получение параметров через утилиту termux-wifi-connectioninfo."""
        try:
            res = subprocess.run(
                ["termux-wifi-connectioninfo"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                data = json.loads(res.stdout)
                ip = data.get("ip")
                # bssid — это MAC роутера; termux-api не отдает MAC самого телефона на современных Android
                bssid = data.get("bssid")
                return (str(ip) if ip else None, bssid.lower() if bssid else None)
        except Exception as e:
            logger.debug(f"termux-wifi-connectioninfo недоступен: {e}")
        return None, None

    @staticmethod
    def _get_mac_address() -> str | None:
        """
        Поиск MAC-адреса через стандартные средства системы.
        На Android 10+ без root вернет None или 02:00:00:00:00:00 из-за ограничений безопасности.
        """
        # 1. Попытка через стандартный uuid (работает на Windows/Linux/macOS)
        try:
            import uuid
            node = uuid.getnode()
            # Проверяем 41-й бит (multicast): если он 1, адрес сгенерирован случайно
            if (node >> 40) & 1 == 0:
                mac = ":".join(
                    f"{(node >> i) & 0xff:02x}" for i in range(40, -1, -8))
                if mac != "00:00:00:00:00:00" and mac != "02:00:00:00:00:00":
                    return mac
        except Exception:
            pass

        # 2. Фолбэк через /sys/class/net (Linux/старые Android/root)
        net_dir = "/sys/class/net"
        if os.path.exists(net_dir):
            try:
                for iface in os.listdir(net_dir):
                    if iface.startswith(("lo", "dummy", "tun")):
                        continue
                    addr_path = os.path.join(net_dir, iface, "address")
                    if os.path.isfile(addr_path):
                        with open(addr_path, "r", encoding="utf-8") as f:
                            mac = f.read().strip().lower()
                            if mac and mac not in ("00:00:00:00:00:00", "02:00:00:00:00:00"):
                                return mac
            except Exception:
                pass

        return None


# Экземпляр по умолчанию
network_scanner = NetworkInterfaceScanner()


def get_ip_and_mac_ifconfig() -> tuple[str | None, str | None]:
    """Обратная совместимость с существующими вызовами."""
    return network_scanner.get_ip_and_mac()


def actualeNetworkInfo() -> tuple[str | None, str | None]:
    return get_ip_and_mac_ifconfig()
