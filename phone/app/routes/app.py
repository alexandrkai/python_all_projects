import asyncio
import sys
from contextlib import asynccontextmanager

import fastapi
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.config import Config
from app.core.log.log import critical_error_logger, get_logger

from .period_task import task_autossh_tunnel, task_canary, task_update_configuration

logger = get_logger(__name__)

# Список фоновых задач приложения
background_tasks: list[asyncio.Task] = []

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

    return app