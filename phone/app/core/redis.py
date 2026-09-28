# app/core/redis.py
import json
import threading
import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Any

import redis
from redis import ConnectionPool
from redis.exceptions import WatchError


class MyRedis:
    """Синглтон-обёртка над connection pool redis-py.

    Использование:
        MyRedis.initialize(Config.REDIS_URL)   # один раз при старте
        r = MyRedis.get_client()               # короткоживущий клиент
        with MyRedis.session() as r:           # контекстный менеджер
            r.set("k", "v")
        # FastAPI:
        def route(r: redis.Redis = Depends(MyRedis.dependency)):
            ...
    """

    _instance = None
    _pool: ConnectionPool | None = None
    _redis_url: str | None = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------------------------------------------------------------ #
    #                       ИНИЦИАЛИЗАЦИЯ ПУЛА                            #
    # ------------------------------------------------------------------ #
    @classmethod
    def initialize(cls, redis_url: str, force: bool = False) -> None:
        """Создаёт пул соединений. Идемпотентно.

        force=True — пересоздать пул (например, если REDIS_URL поменялся
        в конфиге и вы сделали Config.reload()).
        """
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
            raise RuntimeError(
                "MyRedis не инициализирован. Вызовите MyRedis.initialize(url) "
                "при старте приложения."
            )
        return cls._pool

    # ------------------------------------------------------------------ #
    #                            КЛИЕНТЫ                                  #
    # ------------------------------------------------------------------ #
    @classmethod
    def get_client(cls) -> redis.Redis:
        """Новый клиент на общем пуле. Закрывать не обязательно —
        соединение вернётся в пул, но при желании можно r.close()."""
        return redis.Redis(connection_pool=cls._ensure_pool())

    @classmethod
    def dependency(cls) -> Generator[redis.Redis, None, None]:
        """FastAPI-зависимость: Depends(MyRedis.dependency).
        Без аргументов — поэтому корректно работает с Depends."""
        client = cls.get_client()
        try:
            yield client
        finally:
            client.close()

    @classmethod
    @contextmanager
    def session(cls) -> Generator[redis.Redis, None, None]:
        """Контекстный менеджер: with MyRedis.session() as r: ..."""
        client = cls.get_client()
        try:
            yield client
        finally:
            client.close()


# ---------------------------------------------------------------------- #
#                      ГЛОБАЛЬНЫЙ КЛИЕНТ ДЛЯ ХЕЛПЕРОВ                     #
# ---------------------------------------------------------------------- #
_default_client: redis.Redis | None = None
_default_client_lock = threading.Lock()


def get_default_client() -> redis.Redis:
    """Ленивый глобальный клиент — берётся из пула MyRedis."""
    global _default_client
    if _default_client is None:
        with _default_client_lock:
            if _default_client is None:
                _default_client = MyRedis.get_client()
    return _default_client


def _get_active_client(client: redis.Redis | None) -> redis.Redis:
    return client if client is not None else get_default_client()


# ---------------------------------------------------------------------- #
#                             CRUD-ХЕЛПЕРЫ                                #
# ---------------------------------------------------------------------- #
def write_value(
    key: str,
    obj: dict,
    expires_in_seconds: int | None = None,
    client: redis.Redis | None = None,
) -> dict[str, Any]:
    """Сохраняет объект. Без expires_in_seconds — ключ бессрочный."""
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
) -> dict:
    """Читает и десериализует значение по ключу."""
    r = _get_active_client(client)
    raw_data = r.get(key)
    if not raw_data:
        raise ValueError("Срок действия ключа истек или токен недействителен")
    return json.loads(raw_data)


def update_value(
    key: str,
    modifier_fn: Callable[[dict], dict],
    max_retries: int = 10,
    retry_delay: float = 0.05,
    client: redis.Redis | None = None,
) -> dict:
    """Атомарно модифицирует ключ (optimistic locking, WATCH/MULTI/EXEC).
    TTL ключа сохраняется."""
    r = _get_active_client(client)

    for attempt in range(max_retries):
        with r.pipeline() as pipe:
            try:
                pipe.watch(key)
                raw_data = pipe.get(key)
                if not raw_data:
                    pipe.unwatch()
                    raise ValueError(
                        "Срок действия ключа истек или токен недействителен")

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
                    raise RuntimeError(
                        f"Не удалось обновить ключ {key} из-за высокой "
                        f"конкуренции ({max_retries} попыток)"
                    )
                time.sleep(retry_delay)


@contextmanager
def redis_lock(
    lock_name: str,
    timeout: int = 10,
    blocking_timeout: int = 5,
    client: redis.Redis | None = None,
):
    """Пессимистическая блокировка. Пример:
        with redis_lock("sms_session:123"):
            ...
    """
    r = _get_active_client(client)
    lock = r.lock(f"lock:{lock_name}", timeout=timeout,
                  blocking_timeout=blocking_timeout)
    acquired = lock.acquire()
    if not acquired:
        raise TimeoutError(f"Не удалось захватить блокировку для {lock_name}")
    try:
        yield
    finally:
        try:
            lock.release()
        except redis.exceptions.LockError:
            pass


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