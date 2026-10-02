# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/config/config.py
import json
import os
from datetime import datetime, timedelta

from core.network import actualeNetworkInfo
from core.redis import MyRedis, check_exists, read_value, write_value
from core.telegram.telega import DEFAULT_CHAT_ID, __send_message_to_telegram
from dotenv import dotenv_values, load_dotenv
from schemas import PhoneSender, Senders, SimStatus

from core.log.config_logger import config_logger

from .project_folders import (
    PATH_APPLICATION_FOLDER,
    PATH_CONFIG_FOLDER,
    PATH_LOG_FOLDER,
)

PHONE_NAME = os.getenv("PHONE_NAME")


logger = config_logger(PATH_LOG_FOLDER,__file__)

class ReloadableConfig(dict):
    """Конфигурация с возможностью перезагрузки через MyRedis (Singleton)."""

    _instance = None
    _initialized = False

    REDIS_OVERRIDE_KEYS = (
        "EMAIL_SENDERS",
        "REDIS_URL",
    )

    INT_KEYS = {
        "PERIOD_MINUTES_UPDATE_NETWORKINFO",
        "PERIOD_MINUTES_UPDATE_CONFIGURATION",
        "PING_TIMEOUT_SECONDS",
        "PORT_VPN_SERVER",
        "SMTP_PORT",
        "PORT_APPLICATION",
        "PERIOD_MINUTES_CANARY",
        "PERIOD_MINUTES_CHECK_AUTOSSH",
        "SSH_PORT",
    }

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

        self.PATH_APPLICATION_FOLDER = PATH_APPLICATION_FOLDER
        self._env_file = env_file or os.path.join(
            PATH_CONFIG_FOLDER, "envs", f"{PHONE_NAME}.env")
        if not os.path.exists(self._env_file):
            raise Exception(
                f"Не найден конфигурационный файл {self._env_file}!!!")
        self._last_load_time = None
        self._cache_duration = timedelta(seconds=300)
        self._env_file_mtime = None

        self._redis_snapshot: dict[str, str | None] | None = None
        self._last_redis_check = None
        self._redis_check_interval = timedelta(seconds=5)

        self.SENDER: PhoneSender | None = None

        self.IP_ADDRESS_SSH_SERVER: str | None = None
        self.PORT_SSH_SERVER: int | None = None
        self.SSH_PORT: int | None = None
        self.USERNAME_SSH_SERVER: str | None = None

        self.DEFAULT_CHAT_ID = DEFAULT_CHAT_ID

        self.StartSSHTunnel = False
        self._load_config()
        
        ReloadableConfig._initialized = True

    # ------------------------------------------------------------------ #
    def _read_env_file(self) -> dict:
        if not os.path.exists(self._env_file):
            error_message = f"Файл .env не найден: {self._env_file}"
            logger.critical(error_message)
            raise FileNotFoundError(error_message)

        load_dotenv(self._env_file, override=True)
        env_values = dotenv_values(self._env_file)
        self._env_file_mtime = os.path.getmtime(self._env_file)
        return env_values

    # ------------------------------------------------------------------ #
    def _apply_redis_overrides(self, env_values: dict) -> dict:
        redis_url = env_values.get("REDIS_URL")
        if not redis_url:
            msg = "💀 REDIS_URL отсутствует в .env"
            logger.critical(msg)
            self._notify_telegram(msg)
            return env_values

        MyRedis.initialize(redis_url)
        if not MyRedis.ping():
            msg = f"💀 Не удалось подключиться к Redis ({redis_url})"
            logger.critical(msg)
            self._notify_telegram(msg)
            return env_values

        for key in self.REDIS_OVERRIDE_KEYS:
            if key not in env_values:
                continue

            redis_value = MyRedis.get_raw(f"config:{key}")
            if redis_value is None:
                MyRedis.set_raw(f"config:{key}", str(env_values[key]))
                logger.info(f"💾 {key} сохранён в Redis из .env")
            else:
                env_values[key] = redis_value
                logger.info(f"🔁 {key} прочитан из Redis (переопределяет .env)")

        self._redis_snapshot = {
            key: MyRedis.get_raw(f"config:{key}")
            for key in self.REDIS_OVERRIDE_KEYS
            if key in env_values
        }

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
        if self._redis_snapshot is None:
            return False

        now = datetime.now()
        if self._last_redis_check and (now - self._last_redis_check) < self._redis_check_interval:
            return False
        self._last_redis_check = now

        if not MyRedis.ping():
            logger.critical(
                "⚠️ Redis недоступен при проверке изменений через MyRedis")
            return False

        for key, old_value in self._redis_snapshot.items():
            new_value = MyRedis.get_raw(f"config:{key}")
            if new_value != old_value:
                logger.info(f"🔔 Значение {key} изменилось в Redis")
                return True

        return False

    def ensure_fresh(self) -> None:
        if self._cache_expired() or self._env_file_changed() or self._redis_overrides_changed():
            logger.info("🔄 Обновление кэша конфигурации (env + Redis)")
            self._load_config(force=True)

    # ------------------------------------------------------------------ #
    def _setParameter(self, key: str, value: Any):
        if isinstance(value, str):
            val_stripped = value.strip()
            if (val_stripped.startswith("{") and val_stripped.endswith("}")) or \
               (val_stripped.startswith("[") and val_stripped.endswith("]")):
                try:
                    value = json.loads(val_stripped)
                except json.JSONDecodeError:
                    logger.warning(
                        f"⚠️️ Значение {key} похоже на JSON, но не парсится")

            if isinstance(value, str):
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif key in self.INT_KEYS:
                    try:
                        value = int(value)
                    except ValueError:
                        pass

        setattr(self, key, value)
        self[key] = value

    # def _read_telegram_chat_ids(self) -> dict:
    #     path_chat_ids = os.path.join(self.PATH_APPLICATION_FOLDER, "data", "msgprobot_chat_ids.json")
    #     if not os.path.exists(path_chat_ids):
    #         error_msg = f"⚠️ Файл c chat_id не найден: {path_chat_ids}"
    #         logger.error(error_msg, exc_info=True)
    #         raise FileNotFoundError(error_msg)

    #     with open(path_chat_ids, "r", encoding="utf-8") as file:
    #         return json.load(file)

    def _read_info_senders(self) -> Senders:
        path_to_senders = os.path.join(
            self.PATH_APPLICATION_FOLDER, "data", "senders.json")
        if not os.path.exists(path_to_senders):
            error_msg = f"⚠️️ Файл отправителей не найден: {path_to_senders}"
            logger.error(error_msg, exc_info=True)
            raise FileNotFoundError(error_msg)

        with open(path_to_senders, "r", encoding="utf-8") as file:
            return Senders.model_validate_json(file.read())

    def _read_info_phone_sender(self, data: Senders) -> PhoneSender:
        phone_name = getattr(self, "PHONE_NAME", None)
        if not phone_name:
            error_msg = "В конфигурации не указан PHONE_NAME"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Список телефонов может быть None, если в json поле пустое
        phones_list = data.phones or []

        for phone in phones_list:
            if phone.name == phone_name:
                ip_address, mac_address = actualeNetworkInfo()
                port = int(
                    getattr(self, "PORT_APPLICATION", phone.port or 8000))
                description = getattr(self, "DESCRIPTION", phone.description)

                # Обновляем поля Pydantic-модели через model_copy
                updated_phone = phone.model_copy(
                    update={
                        "name": phone_name,
                        "description": description,
                        "port": port,
                        "ip": ip_address,
                        "mac": mac_address,
                        "url": f"http://{ip_address}:{port}",
                        "updated_at": datetime.now(),
                    }
                )
                return updated_phone

        error_msg = f"Не найден телефон {phone_name}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    def _read_info_email_senders(self, data: dict) -> list:
        return data.get("emails", [])

    def _read_info_telegram_chat_ids(self, data: Senders) -> dict[str, str]:
        """Преобразует список TelegramChatId в словарь {phone: chat_id}."""
        chat_list = data.telegram_chat_ids or []
        return {item.phone: item.chat_id for item in chat_list if item.phone}

    # ------------------------------------------------------------------ #
    def _load_config(self, force: bool = False) -> None:
        now = datetime.now()

        if not force:
            if not self._cache_expired() and not self._env_file_changed() and not self._redis_overrides_changed():
                return

        env_values = self._read_env_file()
        env_values = self._apply_redis_overrides(env_values)

        if "REDIS_CHECK_INTERVAL_SECONDS" in env_values:
            try:
                self._redis_check_interval = timedelta(
                    seconds=int(env_values["REDIS_CHECK_INTERVAL_SECONDS"])
                )
            except (ValueError, TypeError):
                pass

        for key, value in env_values.items():
            self._setParameter(key, value)

        data_senders_from_json = self._read_info_senders()
        sender_obj = self._read_info_phone_sender(data_senders_from_json)

        sender_dict = (
            sender_obj.model_dump(mode="json")
            if hasattr(sender_obj, "model_dump")
            else sender_obj.dict()
        )

        # Сохранение телефона-отправителя через MyRedis
        if MyRedis.ping():
            try:
                phone_senders = read_value("config:PHONE_SENDERS") if check_exists(
                    "config:PHONE_SENDERS") else {}
            except Exception:
                phone_senders = {}

            phone_senders[sender_obj.name] = sender_dict
            write_value("config:PHONE_SENDERS", phone_senders)

        self._setParameter("SENDER", sender_obj)

        # Сохранение/чтение email-отправителей
        email_senders = None
        if MyRedis.ping():
            try:
                if check_exists("config:EMAIL_SENDERS"):
                    email_senders = read_value("config:EMAIL_SENDERS")
            except Exception:
                email_senders = None

        if not email_senders:
            email_senders = self._read_info_email_senders(
                data_senders_from_json)
            if MyRedis.ping():
                write_value("config:EMAIL_SENDERS", email_senders)

        if not getattr(self, "EMAIL_SENDERS", None):
            self._setParameter("EMAIL_SENDERS", email_senders)

        active_sims = [
            sim for sim in self.SENDER.sims if sim.status == SimStatus.ACTIVE]
        if not active_sims:
            raise RuntimeError("Нет активных симок в телефоне!")
        self.SENDER.sims = active_sims

        phones = [sim.number for sim in self.SENDER.sims if sim.number]
        logger.info(f"Получены номера телефонов: {phones}")

        # Получаем словарь {номер: chat_id} из конфигурации
        chat_ids_map = self._read_info_telegram_chat_ids(
            data_senders_from_json)

        # Сопоставляем номерам текущего телефона их chat_id (с fallback на DEFAULT_CHAT_ID)
        chat_ids = {
            phone: chat_ids_map.get(phone, DEFAULT_CHAT_ID)
            for phone in phones
        }

        self._setParameter("CHAT_IDS", chat_ids)

        self._last_load_time = now

    def reload(self):
        self._redis_snapshot = None
        self._last_redis_check = None
        self._load_config(force=True)

    def getItems(self):
        self.ensure_fresh()
        return self

    def get(self, key, default=None):
        self.ensure_fresh()
        if key in self:
            return self[key]
        return getattr(self, key, default)

    def __getitem__(self, key):
        self.ensure_fresh()
        return super().__getitem__(key)

    def _notify_telegram(self, message: str) -> None:
        """Безопасная отправка уведомлений из недр конфигуратора."""
        # Проверяем, успели ли мы прочитать переменные для бота
        token = getattr(self, "TELEGRAM_BOT_TOKEN",
                        None) or self.get("TELEGRAM_BOT_TOKEN")
        if not token:
            return

        try:
            # Передаем self, а не внешний Config
            send_error_text_to_telegram(
                error_text=message,
                config=self,
                chat_id=getattr(self, "ADMIN_CHAT_ID", DEFAULT_CHAT_ID),
            )
        except Exception as e:
            logger.error(
                f"Не удалось отправить алерт в Telegram из ReloadableConfig: {e}")


Config = ReloadableConfig()


# app/config/config.py

def get_full_error_message(e: Exception | None = None, error_message: str | None = None, prefix: str | None = None) -> str:
    date_str = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
    msg = error_message or ""
    pref = f".{prefix}" if prefix else ""
    e_str = f"\nДетали: {e}" if e else ""
    sender_name = getattr(Config.SENDER, "name", "DEVICE")
    sender_ip = getattr(Config.SENDER, "ip", "NO_IP")
    return f"❌{date_str}.{sender_name}({sender_ip}){pref}: {msg}{e_str}"


def send_message_to_telegram(text: str, chat_id: str | int = DEFAULT_CHAT_ID) -> dict | None:
    """Отправка сообщения в Telegram через бота."""
    port_ssh = Config.get("PORT_SSH_SERVER", 9090)
    if Config.StartSSHTunnel:
        return __send_message_to_telegram(message=text, chat_id=chat_id, port_ssh_tunnel=port_ssh)
