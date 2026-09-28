# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/config/config.py
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from core.redis import MyRedis, check_exists, read_value, write_value
from dotenv import dotenv_values, load_dotenv
from log.log import get_logger
from schemas import PhoneSender

logger = get_logger(__name__)

current_file = Path(__file__).resolve()
PATH_APPLICATION_FOLDER = current_file.parent.parent
PATH_CONFIG_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "config")
PATH_DATA_FOLDER = os.path.join(PATH_APPLICATION_FOLDER, "data")


def getApplicationRootFolderFromNameApplicationFolder(
    nameRootApplicationFolder: str, file: str = __file__
) -> str:
    current_dir = os.path.dirname(file)
    parts = current_dir.split(os.sep)
    try:
        index = next(
            i for i, part in enumerate(parts)
            if part.lower() == nameRootApplicationFolder.lower()
        ) + 1
    except StopIteration:
        error_msg = f"⚠️Не найдена директория '{nameRootApplicationFolder}' в пути {current_dir}"
        logger.error(error_msg)
        raise Exception(error_msg)

    application_folder = os.sep.join(parts[:index])
    if application_folder not in sys.path:
        sys.path.insert(0, application_folder)
    return application_folder


class ReloadableConfig(dict):
    """Конфигурация с возможностью перезагрузки (Singleton)."""

    _instance = None
    _initialized = False

    REDIS_OVERRIDE_KEYS = (
        "EMAIL_SENDERS",
        "REDIS_URL",
    )

    # ------------------------------------------------------------------ #
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, env_file: str | None = None):
        if ReloadableConfig._initialized:
            if env_file and env_file != self._env_file:
                self._env_file = env_file
                self.reload()
            return

        current_file = Path(__file__).resolve()
        self.PATH_APPLICATION_FOLDER = current_file.parent.parent
        self._env_file = env_file or os.path.join(
            PATH_CONFIG_FOLDER, "envs", ".env")
        self._last_load_time = None
        self._cache_duration = timedelta(seconds=300)
        self._env_file_mtime = None

        self._redis_client = None
        self._redis_snapshot = None
        self._last_redis_check = None
        self._redis_check_interval = timedelta(seconds=5)

        self._load_config()
        ReloadableConfig._initialized = True

    # ------------------------------------------------------------------ #
    def _read_env_file(self) -> dict:
        if not os.path.exists(self._env_file):
            error_message = f"Файл .env не найден: {self._env_file}"
            logger.critical(error_message)
            raise Exception(error_message)

        load_dotenv(self._env_file, override=True)
        env_values = dotenv_values(self._env_file)
        self._env_file_mtime = os.path.getmtime(self._env_file)
        return env_values

    # ------------------------------------------------------------------ #
    def _apply_redis_overrides(self, env_values: dict) -> dict:
        redis_url = env_values.get("REDIS_URL")
        if not redis_url:
            logger.warning(
                "⚠️ REDIS_URL отсутствует в .env — Redis-переопределения пропущены")
            return env_values

        MyRedis.initialize(redis_url)

        try:
            if self._redis_client is None:
                self._redis_client = MyRedis.get_client()
            self._redis_client.ping()
        except Exception as e:
            logger.error(
                f"❌ Не удалось подключиться к Redis ({redis_url}): {e}")
            self._redis_client = None
            return env_values

        for key in self.REDIS_OVERRIDE_KEYS:
            if key not in env_values:
                logger.debug(f"Ключ {key} отсутствует в .env — пропускаем")
                continue

            try:
                redis_value = self._redis_client.get(f"config:{key}")
            except Exception as e:
                logger.error(f"❌ Ошибка чтения {key} из Redis: {e}")
                continue

            if redis_value is None:
                try:
                    self._redis_client.set(f"config:{key}", env_values[key])
                    logger.info(f"💾 {key} сохранён в Redis из .env")
                except Exception as e:
                    logger.error(f"❌ Не удалось сохранить {key} в Redis: {e}")
            else:
                env_values[key] = redis_value
                logger.info(f"🔁 {key} прочитан из Redis (переопределяет .env)")

        try:
            self._redis_snapshot = {
                key: self._redis_client.get(f"config:{key}")
                for key in self.REDIS_OVERRIDE_KEYS
                if key in env_values
            }
        except Exception as e:
            logger.error(f"❌ Не удалось снять снапшот Redis: {e}")
            self._redis_snapshot = None

        return env_values

    # ------------------------------------------------------------------ #
    def _env_file_changed(self) -> bool:
        if self._env_file_mtime is None:
            return True
        try:
            return os.path.getmtime(self._env_file) != self._env_file_mtime
        except OSError:
            return True

    def _cache_expired(self) -> bool:
        if not self._last_load_time:
            return True
        return datetime.now() - self._last_load_time >= self._cache_duration

    def _redis_overrides_changed(self) -> bool:
        # ← FIX: убрана проверка `redis is None`, модуль redis тут не импортирован
        if self._redis_client is None or self._redis_snapshot is None:
            return False

        now = datetime.now()
        if self._last_redis_check and \
                (now - self._last_redis_check) < self._redis_check_interval:
            return False
        self._last_redis_check = now

        try:
            self._redis_client.ping()
        except Exception as e:
            logger.warning(f"⚠️ Redis недоступен при проверке изменений: {e}")
            self._redis_client = None
            return False

        try:
            for key, old_value in self._redis_snapshot.items():
                new_value = self._redis_client.get(f"config:{key}")
                if new_value != old_value:
                    logger.info(f"🔔 Значение {key} изменилось в Redis")
                    return True
        except Exception as e:
            logger.error(f"❌ Ошибка при проверке Redis: {e}")

        return False

    def ensure_fresh(self) -> None:
        if (self._cache_expired()
                or self._env_file_changed()
                or self._redis_overrides_changed()):
            logger.info("🔄 Обновление кэша конфигурации (env + Redis)")
            self._load_config(force=True)

    # ------------------------------------------------------------------ #
    def _setParameter(self, key, value):
        if isinstance(value, str):
            value = value.strip()
            if (value.startswith("{") and value.endswith("}")) or \
                    (value.startswith("[") and value.endswith("]")):
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(
                        f"⚠️ Значение {key} похоже на JSON, но не парсится")

            if isinstance(value, str):
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                match key:
                    case ("PERIOD_MINUTES_UPDATE_NETWORKINFO"
                          | "PERIOD_MINUTES_UPDATE_CONFIGURATION"
                          | "PING_TIMEOUT_SECONDS"
                          | "PORT_VPN_SERVER"
                          | "SMTP_PORT"
                          | "PORT_APPLICATION"
                          | "PERIOD_MINUTES_CANARY"
                          | "PERIOD_MINUTES_CHECK_AUTOSSH"
                          | "SSH_PORT"):
                        try:
                            value = int(value)
                        except ValueError:
                            pass

        setattr(self, key, value)
        self[key] = value

    def _read_telegram_chat_ids(self):
        path_chat_ids = os.path.join(
            self.PATH_APPLICATION_FOLDER, "data", "msgprobot_chat_ids.json")
        if not os.path.exists(path_chat_ids):
            error_msg = f"⚠️Файл c chat_id не найден: {path_chat_ids}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

        with open(path_chat_ids, "r", encoding="utf-8") as file:
            return json.load(file)

    def _read_info_senders(self):
        path_to_senders = os.path.join(
            self.PATH_APPLICATION_FOLDER, "data", "senders.json")
        if not os.path.exists(path_to_senders):
            error_msg = f"⚠️Файл отправителей не найден: {path_to_senders}"
            logger.error(error_msg, exc_info=True)
            raise Exception(error_msg)

        with open(path_to_senders, "r", encoding="utf-8") as file:
            return json.load(file)

    def _read_info_phone_sender(self, data):
        # ← FIX: локальный импорт, чтобы не ловить циклический импорт
        from core.network import actualeNetworkInfo

        phone_name = self.PHONE_NAME
        for phone in data["phones"]:
            if phone["name"] == phone_name:
                # ← FIX: не мутируем входной data
                phone = dict(phone)
                if hasattr(self, "DESCRIPTION"):
                    phone["description"] = self.DESCRIPTION
                phone["port"] = self.PORT_APPLICATION
                ip_address, mac_address = actualeNetworkInfo()
                phone['ip'] = ip_address
                phone['mac'] = mac_address
                phone['url'] = f"http://{phone['ip']}:{phone['port']}"
                return phone
        error_msg = f"Не найден телефон {phone_name}"
        logger.error(error_msg)
        raise Exception(error_msg)

    def _read_info_email_senders(self, data):
        return data.get("emails", [])

    # ------------------------------------------------------------------ #
    def _load_config(self, force: bool = False) -> None:
        now = datetime.now()

        if not force:
            if (not self._cache_expired()
                    and not self._env_file_changed()
                    and not self._redis_overrides_changed()):
                return

        env_values = self._read_env_file()
        env_values = self._apply_redis_overrides(env_values)

        if "REDIS_CHECK_INTERVAL_SECONDS" in env_values:
            try:
                self._redis_check_interval = timedelta(
                    seconds=int(env_values["REDIS_CHECK_INTERVAL_SECONDS"]))
            except (ValueError, TypeError):
                pass

        for key, value in env_values.items():
            self._setParameter(key, value)

        # Загружаем информацию о телефоне-отправителе
        data = self._read_info_senders()
        sender_data = self._read_info_phone_sender(data)
        sender_obj = PhoneSender(**sender_data)
        self._setParameter('SENDER', sender_obj)

        # ← FIX: EMAIL_SENDERS уже мог прийти из Redis/env.
        # Используем senders.json только как fallback.
        if not getattr(self, "EMAIL_SENDERS", None):
            self._setParameter(
                'EMAIL_SENDERS', self._read_info_email_senders(data))

        # Номера без '+'
        phones = [sim.number[1:] for sim in self.SENDER.sims if sim.number]
        logger.info(f"Получены номера телефонов: {phones}")

        # chat_ids
        chat_ids_all = self._read_telegram_chat_ids()
        chat_ids = {phone: chat_ids_all.get(phone, "5151092623")
                    for phone in phones}
        self._setParameter('CHAT_IDS', chat_ids)

        self.active_sims = [
            sim for sim in self.SENDER.sims if sim.status == "active"]
        if len(self.active_sims) == 0:
            raise Exception("Нет активных слотов в телефоне!!!")

        self._last_load_time = now

        # ← FIX: корректное «создать-или-обновить» через write_value
        if self._redis_client is not None:
            try:
                phone_name = self.PHONE_NAME

                # mode="json" — иначе datetime не пройдёт json.dumps в write_value
                if hasattr(self.SENDER, "model_dump"):
                    sender_dict = self.SENDER.model_dump(mode="json")
                else:
                    # запасной путь для pydantic v1
                    sender_dict = self.SENDER.dict()

                # читаем существующее значение (устойчиво к отсутствию)
                try:
                    phone_senders = read_value("config:PHONE_SENDERS")
                    if not isinstance(phone_senders, dict):
                        logger.warning(
                            f"⚠️ config:PHONE_SENDERS не словарь "
                            f"({type(phone_senders).__name__}), пересоздаю"
                        )
                        phone_senders = {}
                except ValueError:
                    # ключа нет — первый запуск
                    phone_senders = {}

                phone_senders[phone_name] = sender_dict

                write_value("config:PHONE_SENDERS", phone_senders)
                logger.info(f"📤 SENDER '{phone_name}' сохранён в Redis")

            except Exception as e:
                logger.error(
                    f"❌ Не удалось обновить PHONE_SENDERS: {e}", exc_info=True
                )
    # ------------------------------------------------------------------ #
    def reload(self):
        self._redis_client = None
        self._redis_snapshot = None
        self._last_redis_check = None
        self._load_config(force=True)

    def getItems(self):
        self.ensure_fresh()
        return self

    def get(self, key, default=None):
        self.ensure_fresh()
        return getattr(self, key, default)

    def __getitem__(self, key):
        self.ensure_fresh()
        return super().__getitem__(key)


Config = ReloadableConfig()