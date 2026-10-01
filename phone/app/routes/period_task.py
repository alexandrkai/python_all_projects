# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/routes/period_task.py
import asyncio
import sys
from contextlib import asynccontextmanager
from datetime import datetime

import fastapi

# Используем актуальные методы логирования и отправки сообщений
from config.config import (
    Config,
    get_full_error_message,
    send_message_to_telegram,
)
from core.autossh import ensure_tunnel
from core.common import get_current_datetime_str
from core.email import myEmail
from core.phone import Phone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from log.log import get_logger
from schemas import EmailRequest, MessagePayload, SimStatus, SMSRequest

logger = get_logger(__name__)

# Список фоновых задач приложения
background_tasks: list[asyncio.Task] = []


async def task_update_configuration():
    """Фоновая задача по периодической перезагрузке конфигурации."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_UPDATE_CONFIGURATION")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(f"ℹ️ Запуск фоновой задачи - обновления конфигурации каждые {period_minutes} минут")

        try:
            Config.reload()
            logger.debug(f"✅ Выполнили фоновую задачу обновления конфигурации. Ждем {period_minutes} минут")
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Сбой перезагрузки конфигурации",
                prefix="UPDATE_CONFIG",
            )
            logger.error(full_msg, exc_info=True)
            send_message_to_telegram(full_msg)

        await asyncio.sleep(60 * period_minutes)


async def task_canary():
    """Фоновая задача-канарейка (периодическая проверка отправки Email и SMS)."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_CANARY")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(f"ℹ️ Запуск фоновой задачи - отправка канареек каждые {period_minutes} минут")

        sender = Config.SENDER

        # 1. Проверка отправки Email
        try:
            sender_name = getattr(sender, "name", "DEVICE")
            email_data = EmailRequest(
                to_email="kaiby@yandex.ru",
                message=MessagePayload(
                    title=f"{get_current_datetime_str()}. {sender_name}. Канарейка",
                    body="Проверка связи канарейки",
                    footer="Сервис мониторинга",
                ),
            )
            result = myEmail.send(email_data)
            logger.info(f"✅ EMAIL Канарейка успешно отработала: {result}")
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка при отправке канареечного email",
                prefix="CANARY_EMAIL",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)

        # 2. Проверка активных SIM-карт
        try:
            available_sims = getattr(sender, "sims", []) or []
            active_sims = [sim for sim in available_sims if sim.status == SimStatus.ACTIVE]

            for sim in active_sims:
                sms_text = f"{get_current_datetime_str()}. {getattr(sender, 'name', '')}. {sim.number}. SMS.Канарейка"
                sms_data = SMSRequest(
                    number="+79175729812",
                    message=sms_text,
                    sim_slot=sim.slot,
                )
                Phone.send_sms(sms_data)
                logger.info(f"✅ SMS Канарейка отправлена со слота {sim.slot} ({sim.number})")

        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка при отправке канареечного SMS",
                prefix="CANARY_SMS",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
        logger.debug(f"✅ Выполнили фоновую задачу отправок канареек. Ждем {period_minutes} минут")
        await asyncio.sleep(60 * period_minutes)


async def task_autossh_tunnel():
    """Фоновая задача контроля SSH/SOCKS5-туннеля."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_CHECK_AUTOSSH")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(f"ℹ️ Запуск фоновой задачи - проверка autossh каждые {period_minutes} минут")

        try:
            remote_ip = Config.get("IP_ADDRESS_SSH_SERVER")
            ssh_port = Config.get("SSH_PORT", 22)
            remote_user = Config.get("USERNAME_SSH_SERVER")
            local_tunnel_port = Config.get("PORT_SSH_SERVER", 9090)

            if remote_ip and remote_user:
                ensure_tunnel(
                    port=local_tunnel_port, 
                    remote=remote_ip,
                    user=remote_user,
                    ssh_port=ssh_port,
                )
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка проверки autossh-туннеля",
                prefix="AUTOSSH",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)

        await asyncio.sleep(60 * period_minutes)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Контекстный менеджер управления жизненным циклом фоновых задач."""
    logger.info("=" * 60)
    logger.info("ЗАПУСК ПРИЛОЖЕНИЯ")
    logger.info("=" * 60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"FastAPI version: {fastapi.__version__}")

    logger.info("Запуск фоновых задач...")
    background_tasks.append(asyncio.create_task(task_update_configuration()))
    background_tasks.append(asyncio.create_task(task_canary()))
    background_tasks.append(asyncio.create_task(task_autossh_tunnel()))
    logger.info("Фоновые задачи успешно запущены")
    logger.info("=" * 60)

    yield  # Время работы приложения

    logger.info("=" * 60)
    logger.info("ОСТАНОВКА ПРИЛОЖЕНИЯ: остановка фоновых задач")
    logger.info("=" * 60)

    for task in background_tasks:
        task.cancel()

    await asyncio.gather(*background_tasks, return_exceptions=True)
    background_tasks.clear()
    logger.info("Все фоновые задачи остановлены")


def create_router_for_management():
    """Создает роутер для управления конфигурацией."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/config", tags=["Configuration"])

    @router.post("/reload-config")
    async def reload_config():
        """Принудительная перезагрузка конфигурации из файлов и Redis."""
        logger.info("Принудительная перезагрузка конфигурации через API")
        Config.reload()
        config_data = Config.getItems().copy()
        config_data.update({
            "config_file": Config._env_file,
            "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None,
        })
        return {
            "message": "Конфигурация перезагружена",
            "config": config_data,
        }

    @router.get("/current")
    async def get_current_config():
        """Получить текущие параметры конфигурации."""
        config_data = Config.getItems().copy()
        config_data.update({
            "config_file": Config._env_file,
            "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None,
        })
        return config_data

    return router


def create_app() -> FastAPI:
    """Фабрика приложения FastAPI."""
    phone_name = Config.get("PHONE_NAME", "GATEWAY")
    app = FastAPI(
        title=f"{phone_name}. API для отправки сообщений",
        version="1.0.0",
        description="Шлюз SMS, Email и Telegram уведомлений",
        openapi_version="3.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(create_router_for_management())
    return app