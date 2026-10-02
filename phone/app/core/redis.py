# app/core/redis.py
import json
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

import redis
from core.log.log import get_logger
from redis import ConnectionPool
from redis.exceptions import WatchError

logger = get_logger(__name__)


class MyRedis:
    """Синглтон-обёртка над connection pool redis-py."""

    _instance = None
    _pool: ConnectionPool | None = None
    _redis_url: str | None = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def initialize(cls, redis_url: str, force: bool = False) -> None:
        with cls._lock:
            if cls._pool is not None and not force:
                return
            cls._redis_url = redis_url
            cls._pool = ConnectionPool.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
                protocol=2,
            )

    @classmethod
    def _ensure_pool(cls) -> ConnectionPool:
        if cls._pool is None:
            error_message = "⚠️ MyRedis не инициализирован. Вызовите MyRedis.initialize(url) при старте приложения."
            logger.warning(error_message)
            raise RuntimeError(error_message)
        return cls._pool

    @classmethod
    def get_client(cls) -> redis.Redis:
        return redis.Redis(connection_pool=cls._ensure_pool())

    @classmethod
    def dependency(cls) -> Generator[redis.Redis, None, None]:
        client = cls.get_client()
        try:
            yield client
        finally:
            client.close()

    @classmethod
    @contextmanager
    def session(cls) -> Generator[redis.Redis, None, None]:
        client = cls.get_client()
        try:
            yield client
        finally:
            client.close()

    @classmethod
    def ping(cls) -> bool:
        """Проверяет доступность Redis сервера."""
        try:
            with cls.session() as r:
                return bool(r.ping())
        except Exception:
            return False

    @classmethod
    def get_raw(cls, key: str) -> str | None:
        """Читает строковое значение без JSON-десериализации."""
        try:
            with cls.session() as r:
                return r.get(key)
        except Exception as e:
            logger.error(f"❌ Ошибка MyRedis.get_raw для ключа {key}: {e}")
            return None

    @classmethod
    def set_raw(cls, key: str, value: str, expires_in_seconds: int | None = None) -> bool:
        """Записывает строковое значение без JSON-сериализации."""
        try:
            with cls.session() as r:
                if expires_in_seconds:
                    r.setex(name=key, time=expires_in_seconds, value=value)
                else:
                    r.set(name=key, value=value)
                return True
        except Exception as e:
            logger.error(f"❌ Ошибка MyRedis.set_raw для ключа {key}: {e}")
            return False


# ---------------------------------------------------------------------- #
#                        ГЛОБАЛЬНЫЙ КЛИЕНТ ДЛЯ ХЕЛПЕРОВ                  #
# ---------------------------------------------------------------------- #
_default_client: redis.Redis | None = None
_default_client_lock = threading.Lock()


def get_default_client() -> redis.Redis:
    global _default_client
    if _default_client is None:
        with _default_client_lock:
            if _default_client is None:
                _default_client = MyRedis.get_client()
    return _default_client


def _get_active_client(client: redis.Redis | None) -> redis.Redis:
    return client if client is not None else get_default_client()


# ---------------------------------------------------------------------- #
#                             CRUD-ХЕЛПЕРЫ                               #
# ---------------------------------------------------------------------- #
def write_value(
    key: str,
    obj: Any,
    expires_in_seconds: int | None = None,
    client: redis.Redis | None = None,
) -> dict[str, Any]:
    r = _get_active_client(client)
    payload = json.dumps(obj)
    if expires_in_seconds:
        r.setex(name=key, time=expires_in_seconds, value=payload)
    else:
        r.set(name=key, value=payload)
    return {"key": key, "value": payload}


def read_value(
    key: str,
    client: redis.Redis | None = None,
) -> Any:
    r = _get_active_client(client)
    raw_data = r.get(key)
    if not raw_data:
        error_message = f"⚠️ Срок действия ключа {key} истек или ключ недействителен"
        logger.warning(error_message)
        raise ValueError(error_message)
    return json.loads(raw_data)


def update_value(
    key: str,
    modifier_fn: Callable[[dict], dict],
    max_retries: int = 10,
    retry_delay: float = 0.05,
    client: redis.Redis | None = None,
) -> dict:
    r = _get_active_client(client)

    for attempt in range(max_retries):
        with r.pipeline() as pipe:
            try:
                pipe.watch(key)
                raw_data = pipe.get(key)
                if not raw_data:
                    pipe.unwatch()
                    error_message = f"⚠️ Ключ {key} не найден при обновлении"
                    logger.warning(error_message)
                    raise ValueError(error_message)

                current_ttl = pipe.ttl(key)
                current_data = json.loads(raw_data)
                updated_data = modifier_fn(current_data)

                pipe.multi()
                if current_ttl > 0:
                    pipe.setex(key, current_ttl, json.dumps(updated_data))
                else:
                    pipe.set(key, json.dumps(updated_data))
                pipe.execute()
                return updated_data

            except WatchError:
                if attempt == max_retries - 1:
                    error_message = f"⚠️ Не удалось обновить ключ {key} из-за высокой конкуренции ({max_retries} попыток)"
                    logger.warning(error_message)
                    raise RuntimeError(error_message)
                time.sleep(retry_delay)


@contextmanager
def redis_lock(
    lock_name: str,
    timeout: int = 10,
    blocking_timeout: int = 5,
    client: redis.Redis | None = None,
):
    r = _get_active_client(client)
    lock = r.lock(f"lock:{lock_name}", timeout=timeout, blocking_timeout=blocking_timeout)
    acquired = lock.acquire()
    if not acquired:
        error_message = f"⚠️ Не удалось захватить блокировку для {lock_name}"
        logger.warning(error_message)
        raise TimeoutError(error_message)
    try:
        yield
    finally:
        try:
            lock.release()
        except redis.exceptions.LockError:
            logger.warning("⚠️ Ошибка освобождения блокировки")


def delete_value(
    key: str,
    client: redis.Redis | None = None,
) -> None:
    r = _get_active_client(client)
    r.delete(key)


def check_exists(
    key: str,
    client: redis.Redis | None = None,
) -> bool:
    r = _get_active_client(client)
    return bool(r.exists(key))