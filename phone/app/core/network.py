# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/network.py
import os
import platform
import re
import subprocess
import sys
import time
from functools import lru_cache

from log.log import get_logger

logger = get_logger(__name__)


def is_termux() -> bool:
    """
    Определяет, работает ли код в Termux на Android
    """
    checks = []

    # 1. Проверка переменных окружения Termux
    termux_env_checks = [
        os.environ.get('TERMUX_VERSION'),
        os.environ.get('TERMUX_APP_PID'),
        os.environ.get('PREFIX', '').startswith(
            '/data/data/com.termux/files/usr'),
        any('termux' in path.lower() for path in sys.path)
    ]
    checks.append(any(termux_env_checks))

    # 2. Проверка пути PREFIX (специфично для Termux)
    termux_prefix = '/data/data/com.termux/files/usr'
    checks.append(os.path.exists(termux_prefix))

    # 3. Проверка наличия специфичных файлов Termux
    termux_files = [
        '/data/data/com.termux/files/home/.termux',
        '/data/data/com.termux/files/usr/bin/login',
        '/data/data/com.termux/files/usr/etc/termux.properties'
    ]
    checks.append(any(os.path.exists(f) for f in termux_files))

    # 4. Проверка через ps или proc (Android специфика)
    try:
        # В Android есть специфичные процессы
        result = subprocess.run(
            ['ps', '-A'],
            capture_output=True,
            text=True,
            timeout=3
        )
        checks.append('com.termux' in result.stdout)
    except:
        checks.append(False)

    # 5. Проверка архитектуры (Android обычно arm/aarch64)
    machine = platform.machine().lower()
    android_arches = ['arm', 'arm64', 'aarch64', 'armv7l', 'armv8l']
    checks.append(any(arch in machine for arch in android_arches))

    # 6. Проверка через uname
    try:
        result = subprocess.run(
            ['uname', '-a'],
            capture_output=True,
            text=True,
            timeout=3
        )
        checks.append('android' in result.stdout.lower())
    except:
        checks.append(False)

    # 7. Проверка свойств Android через getprop
    try:
        result = subprocess.run(
            ['getprop', 'ro.build.version.sdk'],
            capture_output=True,
            text=True,
            timeout=3
        )
        checks.append(result.returncode ==
                      0 and result.stdout.strip().isdigit())
    except:
        checks.append(False)

    # Если хотя бы 3 проверки прошли - это Termux
    return sum(checks) >= 3


class NetworkInterfaceScanner:
    """Сканер сетевых интерфейсов с кэшированием"""

    def __init__(self, cache_ttl: int = 60):
        self.cache_ttl = cache_ttl
        self._cache = {}
        self._cache_time = {}

    def _is_cache_valid(self, key: str) -> bool:
        """Проверяет актуальность кэша"""
        if key not in self._cache_time:
            return False
        return (time.time() - self._cache_time[key]) < self.cache_ttl

    def get_ip_and_mac(self) -> tuple[str | None, str | None]:
        """Основной метод получения IP и MAC"""
        cache_key = "ip_mac"

        if self._is_cache_valid(cache_key):
            return self._cache[cache_key]

        ip, mac = self._get_ip_and_mac_impl()

        self._cache[cache_key] = (ip, mac)
        self._cache_time[cache_key] = time.time()

        return ip, mac

    def _get_ip_and_mac_impl(self) -> tuple[str | None, str | None]:
        """Реализация получения IP и MAC"""

        if is_termux():
            return self._get_termux()

        system = platform.system().lower()

        if system == "windows":
            return self._get_windows_ip_mac()
        elif system == "darwin":  # macOS
            return self._get_macos_ip_mac()
        else:  # Linux, Android, etc.
            return self._get_linux_ip_mac()

    def _get_linux_ip_mac(self) -> tuple[str | None, str | None]:
        """Для Linux/Android систем"""
        try:
            # Пробуем ifconfig
            result = subprocess.run(
                ['ifconfig'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return self._parse_ifconfig_linux(result.stdout)

            # Если ifconfig нет, пробуем ip
            result = subprocess.run(
                ['ip', 'addr', 'show'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return self._parse_ip_addr(result.stdout)

        except Exception as e:
            logger.error(f"⚠️Ошибка при получении сетевых интерфейсов: {e}")

        # Фолбэк: пробуем получить через socket
        return self._get_fallback_ip_mac()

    def _parse_ifconfig_linux(self, output: str) -> tuple[str | None, str | None]:
        """Парсинг ifconfig для Linux"""
        interfaces = output.split('\n\n')

        for block in interfaces:
            if not block.strip():
                continue

            # Пропускаем loopback
            if 'LOOPBACK' in block or 'lo:' in block:
                continue

            # Ищем MAC
            mac_match = re.search(
                r'ether\s+([0-9a-f:]{17})', block, re.IGNORECASE)
            mac = mac_match.group(1).lower() if mac_match else None

            # Ищем IPv4
            ip_match = re.search(
                r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', block)
            ip = ip_match.group(1) if ip_match else None

            if ip and not ip.startswith('127.'):
                return ip, mac

        return None, None

    def _parse_ip_addr(self, output: str) -> tuple[str | None, str | None]:
        """Парсинг ip addr для Linux"""
        lines = output.split('\n')
        current_mac = None

        for line in lines:
            line = line.strip()

            # MAC адрес
            mac_match = re.search(
                r'link/ether\s+([0-9a-f:]{17})', line, re.IGNORECASE)
            if mac_match:
                current_mac = mac_match.group(1).lower()

            # IPv4 адрес (не localhost)
            ip_match = re.search(
                r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line)
            if ip_match:
                ip = ip_match.group(1)
                if not ip.startswith('127.'):
                    return ip, current_mac

        return None, None

    def _get_windows_ip_mac(self) -> tuple[str | None, str | None]:
        """Для Windows систем"""
        try:
            # Получаем IP через ipconfig
            ip_result = subprocess.run(
                ['ipconfig'],
                capture_output=True,
                text=True,
                encoding='cp866',
                timeout=5
            )

            if ip_result.returncode == 0:
                # Ищем IPv4 адрес
                ip_match = re.search(
                    r'IPv4[^\d]+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})',
                    ip_result.stdout
                )
                ip = ip_match.group(1) if ip_match else None

                # Получаем MAC через getmac
                mac_result = subprocess.run(
                    ['getmac'],
                    capture_output=True,
                    text=True,
                    encoding='cp866',
                    timeout=5
                )

                mac = None
                if mac_result.returncode == 0:
                    mac_match = re.search(
                        r'([0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2}-[0-9A-F]{2})',
                        mac_result.stdout
                    )
                    if mac_match:
                        mac = mac_match.group(1).replace('-', ':').lower()

                return ip, mac

        except Exception as e:
            logger.error(
                f"⚠️Ошибка при получении сетевых интерфейсов Windows: {e}")

        return None, None

    def _get_macos_ip_mac(self) -> tuple[str | None, str | None]:
        """Для macOS систем"""
        try:
            result = subprocess.run(
                ['ifconfig'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return self._parse_ifconfig_macos(result.stdout)

        except Exception as e:
            logger.error(
                f"⚠️Ошибка при получении сетевых интерфейсов macOS: {e}")

        return None, None

    def _parse_ifconfig_macos(self, output: str) -> tuple[str | None, str | None]:
        """Парсинг ifconfig для macOS"""
        interfaces = output.split('\n\n')

        for block in interfaces:
            if not block.strip():
                continue

            # Пропускаем loopback
            if 'lo0:' in block or 'flags=8049<' in block:
                continue

            # Ищем MAC
            mac_match = re.search(r'ether\s+([0-9a-f:]{17})', block)
            mac = mac_match.group(1).lower() if mac_match else None

            # Ищем IPv4
            ip_match = re.search(
                r'inet\s+(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', block)
            ip = ip_match.group(1) if ip_match else None

            if ip and not ip.startswith('127.'):
                return ip, mac

        return None, None

    def _get_fallback_ip_mac(self) -> tuple[str | None, str | None]:
        """Фолбэк методы"""
        # Получаем IP через socket
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
        except:
            ip = None

        # MAC через /sys/class/net (только Linux)
        mac = None
        try:
            import os
            net_dir = '/sys/class/net/'
            if os.path.exists(net_dir):
                for interface in os.listdir(net_dir):
                    if interface == 'lo':
                        continue
                    mac_file = os.path.join(net_dir, interface, 'address')
                    if os.path.exists(mac_file):
                        with open(mac_file, 'r') as f:
                            mac = f.read().strip()
                            if mac and mac != '00:00:00:00:00:00':
                                break
        except:
            pass

        return ip, mac

    def _get_termux(self) -> tuple[str | None, str | None]:
        """Для Linux/Android систем"""
        try:
            import json
            result = subprocess.run(
                ['termux-wifi-connectioninfo'],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.debug(result.stdout)
                wifi_info = json.loads(result.stdout)

                # Получаем IP из WiFi информации
                if 'ip' in wifi_info:
                    ip_address = str(wifi_info['ip'])
                    logger.info(f"IP из termux-wifi: {ip_address}")

                # Получаем BSSID (MAC точки доступа)
                if 'bssid' in wifi_info:
                    mac_address = wifi_info['mac_address'].lower()
                    logger.info(f"BSSID из termux-wifi: {mac_address}")
                return ip_address, mac_address
        except Exception as e:
            logger.debug(f"termux-wifi-connectioninfo не доступен: {e}")

        return None, None


# Синглтон для использования
network_scanner = NetworkInterfaceScanner()

# Функция для обратной совместимости


def get_ip_and_mac_ifconfig() -> tuple[str | None, str | None]:
    """Основная функция для получения IP и MAC"""
    return network_scanner.get_ip_and_mac()


def actualeNetworkInfo():
    """Обновляет конфигурацию сети и перезагружает Config."""
    network_data = get_ip_and_mac_ifconfig()

    # Проверяем, что результат не None
    ip_address = None
    mac_address = None
    if network_data is not None:
        ip_address, mac_address = network_data

    # # 1. Получаем текущий объект PhoneSender из Config (это вызовет @property SENDER)
    # current_sender = Config.SENDER

    # # 2. Создаем копию объекта с обновленными полями.
    # # model_copy - безопасный способ изменить "замороженный" Pydantic объект.
    # updated_sender = current_sender.model_copy(update={
    #     "ip": ip_address if ip_address else "unknown",
    #     "mac": mac_address if mac_address else "unknown",
    # })

    # # 3. Формируем и обновляем URL
    # if updated_sender.ip and updated_sender.ip != "unknown":
    #     updated_url = f"http://{updated_sender.ip}:{updated_sender.port}"
    # else:
    #     updated_url = f"http://localhost:{updated_sender.port}"

    # # Обновляем URL в объекте (создаем финальную копию)
    # final_sender = updated_sender.model_copy(update={"url": updated_url})

    # # 4. Сохраняем в файл whoami.json
    # path_to_data = os.path.join(Config.PATH_APPLICATION_FOLDER, "data", "whoami.json")
    # os.makedirs(os.path.dirname(path_to_data), exist_ok=True)

    # with open(path_to_data, "w", encoding="utf-8") as file:
    #     # model_dump_json() сериализует Pydantic модель в JSON строку
    #     file.write(final_sender.model_dump_json(indent=4))

    # # 5. Перезагружаем конфигурацию, чтобы Config перечитал whoami.json
    # # Теперь Config.SENDER будет возвращать обновленные данные
    # Config.reload()

    # return Config
    return ip_address, mac_address


# Пример использования
if __name__ == "__main__":
    pass
    # print("Тестирование получения сетевых интерфейсов...")

    # # Основной способ
    # ip, mac = get_ip_and_mac_ifconfig()
    # print(f"IP: {ip}")
    # print(f"MAC: {mac}")

    # # Через класс
    # scanner = NetworkInterfaceScanner()
    # ip2, mac2 = scanner.get_ip_and_mac()
    # print(f"Через класс - IP: {ip2}, MAC: {mac2}")
