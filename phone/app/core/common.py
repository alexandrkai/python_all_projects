# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/common.py
import json
import os
import platform
import subprocess
from datetime import datetime

from log.log import get_logger
from schemas import Result, ResultStatus

logger = get_logger(__name__)


def get_current_time() -> datetime:
    return datetime.now()  # noqa: DTZ005


def get_current_time_str() -> str:
    return get_current_time().strftime("%d.%m.%Y %H:%M:%S")


def _decode_output(stdout: bytes, stderr: bytes) -> tuple[str, str]:
    """
    Вспомогательная функция для декодирования вывода команды.
    """
    if not stdout and not stderr:
        return "", ""

    # Определяем список кодировок в зависимости от платформы
    if platform.system() == "Windows":
        # Для Windows: стандартная консольная (cp866), ANSI (cp1251), и UTF-8
        encodings_to_try = ["cp866", "cp1251", "utf-8"]
    else:
        # Для Linux/Mac обычно UTF-8
        encodings_to_try = ["utf-8"]

    # last_exception = None

    for encoding in encodings_to_try:
        try:
            dec_stdout = stdout.decode(encoding) if stdout else ""
            dec_stderr = stderr.decode(encoding) if stderr else ""
            return dec_stdout, dec_stderr
        except (UnicodeDecodeError, LookupError) as e:
            # last_exception = e
            continue

    # Если ни одна кодировка не подошла (редкий случай), используем utf-8 с заменой ошибок
    return (
        stdout.decode("utf-8", errors="replace") if stdout else "",
        stderr.decode("utf-8", errors="replace") if stderr else ""
    )


def runShellCommand(command: list, timeout: int = 30) -> Result:
    """
    Выполняет shell команду и возвращает объект Result.
    """
    # from config.config import Config
    # Получаем отправителя из Config.
    # Config.SENDER теперь возвращает объект PhoneSender.
    # Используем model_copy(), чтобы зафиксировать состояние на момент вызова
    # и не зависеть от будущих изменений в конфиге.
    # sender_copy = Config.SENDER.model_copy()

    # Инициализируем результат с текущей датой
    result = Result(
        status=ResultStatus.ERROR,
        due_date=datetime.now(),
        # sender=sender_copy,
        detail="Команда даже не стартовала"
    )

    try:
        logger.debug(f"Выполняем команду {command}")
        # text=False позволяет получить bytes, которые мы потом декодируем сами в _decode_output
        process = subprocess.run(
            command, capture_output=True, text=False, timeout=timeout)

        # Декодируем вывод с помощью нашей вспомогательной функции
        out_str, err_str = _decode_output(process.stdout, process.stderr)

        logger.debug(f"process.stdout: {out_str}")
        logger.debug(f"process.stderr: {err_str}")

        if process.returncode == 0:
            result.status = ResultStatus.OK
            result.detail = None
            result.data = out_str
        else:
            result.status = ResultStatus.ERROR
            result.detail = f"Ошибка выполнения. stdout:{out_str}, stderr:{err_str}"
            result.data = out_str

    except subprocess.TimeoutExpired:
        mess = "⚠️Ошибка! Время выполнения истекло (timeout)."
        logger.error(mess, exc_info=True)
        result.detail = f"Ошибка: {mess}"
    except Exception as e:
        mess = str(e)
        logger.error("⚠️"+mess, exc_info=True)
        result.detail = f"Ошибка: {mess}"

    return result


def convertData(result: Result) -> Result:
    """
    Преобразует поле data (строку JSON) в словарь, если это возможно.
    """
    if result.data and isinstance(result.data, str):
        try:
            logger.debug(f"Пытаемся распарсить data: {result.data}")
            parsed_data = json.loads(result.data)
            result.data = parsed_data
        except json.JSONDecodeError:
            # Если не JSON, оставляем как строку или можно логировать warning
            logger.error(
                f"⚠️Warning: Data is not valid JSON. Leaving as string.", exc_info=True)
    return result


def batteryStatus() -> Result:
    """Статус батареи"""
    command = ["termux-battery-status"]
    result = convertData(runShellCommand(command))
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


def callLog(limit: int = 10, offset: int = 0) -> Result:
    """Список вызовов"""
    command = ["termux-call-log"]
    command.extend(["-l", str(limit)])
    command.extend(["-o", str(offset)])
    result = convertData(runShellCommand(command))
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


def contactList() -> Result:
    """Список контактов"""
    command = ["termux-contact-list"]
    result = convertData(runShellCommand(command))
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


def smsList(showDate: bool = True, limit: int = 10, showNumberPhone: bool = True,
            offset: int = 0, typeSMS: str = "all") -> Result:
    """Список СМС"""

    # Валидация типа SMS
    valid_types = ["all", "inbox", "sent", "draft", "outbox"]
    if typeSMS not in valid_types:
        logger.warning(
            f"Предупреждение: typeSMS должен быть одним из {valid_types}")
        typeSMS = "all"

    # Формируем команду
    command = ["termux-sms-list"]

    # Флаги (без значений)
    if showDate:
        command.append("-d")
    if showNumberPhone:
        command.append("-n")

    # Параметры с значениями (все значения как строки)
    command.extend(["-l", str(limit)])
    command.extend(["-o", str(offset)])
    command.extend(["-t", typeSMS])

    result = convertData(runShellCommand(command))
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


def startSSH() -> Result:
    command = ["sshd"]
    result: Result = runShellCommand(command)
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


def networkInfo() -> Result:
    command = ['termux-wifi-connectioninfo']
    result = convertData(runShellCommand(command))
    if result.is_ok:
        return result
    else:
        raise Exception(result.detail)


class Comments:
    # python common.py --dry-run /mnt/d/myprogramms/Python/Phones/POCOX3PRO/REQUIREMENTS/app
    # Comments.main()
    def process_py_files(self, directory="."):
        """
        Рекурсивно ищет файлы .py и обновляет комментарии с путями.
        """
        import re  # Добавлен import re, так как он используется в update_file_comment

        for root, dirs, files in os.walk(directory):
            # Пропускаем некоторые директории
            dirs[:] = [d for d in dirs if not d.startswith(
                '.') and d not in ['__pycache__', 'venv', 'env']]

            for file in files:
                if file.endswith('.py'):
                    full_path = os.path.abspath(os.path.join(root, file))
                    self.update_file_comment(full_path)

    def update_file_comment(self, file_path):
        """
        Обновляет комментарий с путем в файле.
        """
        import re  # Локальный импорт для безопасности, если метод вызывается отдельно

        try:
            # Пробуем разные кодировки
            for encoding in ['utf-8', 'cp1251', 'latin-1']:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                print(
                    f"✗ Не удалось прочитать файл {file_path} (проблема с кодировкой)")
                return
        except Exception as e:
            print(f"✗ Ошибка чтения {file_path}: {e}")
            return

        # Абсолютный путь к файлу
        abs_path = os.path.abspath(file_path)
        normalized_path = abs_path.replace(
            '\\', '/')  # Нормализуем разделители

        # Паттерны для поиска существующих комментариев с путями
        patterns = [
            r'^#\s*(.*\.py)$',           # # /path/file.py
            r'^#\s*File:\s*(.*\.py)$',   # # File: /path/file.py
            r'^#\s*Path:\s*(.*\.py)$',   # # Path: /path/file.py
            r'^#\s*Source:\s*(.*\.py)$',  # Source: /path/file.py
        ]

        new_comment = f"# {normalized_path}"
        updated = False
        action = None

        if lines:
            first_line = lines[0].rstrip('\n')

            # Проверяем, содержит ли первая строка путь к файлу
            path_found = False
            for pattern in patterns:
                match = re.match(pattern, first_line)
                if match:
                    old_path = match.group(1)
                    # Проверяем, указывает ли путь на текущий файл
                    if (os.path.basename(abs_path) == os.path.basename(old_path) or
                            os.path.exists(old_path) and os.path.samefile(old_path, abs_path)):
                        lines[0] = new_comment + '\n'
                        updated = True
                        action = "обновлен"
                        path_found = True
                        break

            if not path_found:
                if first_line.startswith('#!'):
                    lines.insert(1, new_comment + '\n')
                else:
                    lines.insert(0, new_comment + '\n')
                updated = True
                action = "добавлен"
        else:
            lines = [new_comment + '\n']
            updated = True
            action = "создан"

        if updated:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                print(f"✓ {file_path}: {action}")
            except Exception as e:
                print(f"✗ Ошибка записи {file_path}: {e}")

    def main(self):
        """Основная функция с обработкой аргументов."""
        import argparse
        import re  # Добавлен import re

        parser = argparse.ArgumentParser(
            description='Добавляет или обновляет комментарии с полными путями в .py файлах'
        )
        parser.add_argument(
            'directory',
            nargs='?',
            default='.',
            help='Директория для поиска (по умолчанию: текущая)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Показать что будет изменено без реальной записи'
        )

        args = parser.parse_args()

        if not os.path.exists(args.directory):
            print(f"Ошибка: директория '{args.directory}' не существует")
            return

        start_dir = os.path.abspath(args.directory)
        print(f"Поиск .py файлов в: {start_dir}")
        print("=" * 60)

        try:
            self.process_py_files(start_dir)
            print("=" * 60)
            print("Обработка завершена.")
        except KeyboardInterrupt:
            print("\nПрервано пользователем.")
        except Exception as e:
            print(f"\nНеожиданная ошибка: {e}")
            import traceback
            traceback.print_exc()
