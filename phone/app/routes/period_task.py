# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/routes/period_task.py
import fastapi
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import sys
# import requests
from datetime import datetime

# Используем новую перезагружаемую конфигурацию
from config.config import Config  # Это теперь ReloadableConfig
from core import ensure_tunnel, send_messege_to_boot, ping_services, get_current_time, EmailCreate, myEmail, getEmailSender
from log.log import get_logger

# Флаг для остановки фоновых задач
background_tasks = []

# Фоновая задача по обновлению сетевой информации
logger = get_logger(__name__)

# async def task_update_network_info():
#     # from core.telegram.telega import send_messege_to_boot
#     """Фоновая задача по обновлению информации о сети"""
#     while True:
#         # Получаем текущие значения из конфигурации
#         period_minutes = int(Config.PERIOD_MINUTES_UPDATE_NETWORKINFO)
#         message = f"Запуск фоновой задачи UPDATE_NETWORKINFO в {datetime.now()} каждые {period_minutes} минуты"
#         logger.info(message)

#         try:
#             # from core.common import actualeNetworkInfo
#             # Обновляем информацию отправителя
#             # TODO ip адрес вряд ли будет меняться, поэтому вырубил -оставил пустышку для интереса
#             # actualeNetworkInfo()
#             pass
#         except Exception as e:
#             message=f"⚠️Ошибка при обновлении сетевой информации: {e}"
#             logger.error(message)
#         finally:
#             if Config.get("LOG_TELEGRAM"):send_messege_to_boot(message)
#         # Используем текущий интервал из конфигурации
#         await asyncio.sleep(60 * period_minutes)

# TODO Фоновая задача по обновлению конфигурации. она и так перегружается каждые 300 секунд(self._cache_duration = timedelta(seconds=300) )


async def task_update_configuration():
    """Фоновая задача по обновлению конфигурации"""
    # from core.telegram.telega import send_messege_to_boot
    while True:
        try:
            # Получаем текущие значения из конфигурации
            period_minutes = int(Config.PERIOD_MINUTES_UPDATE_CONFIGURATION)
            message = f"Запуск фоновой задачи UPDATE_CONFIGURATION в {datetime.now().isoformat()} каждые {period_minutes} минуты"
            logger.info(message)
            # TODO оставил для баловства
            Config.reload()
            message = f"Выполнили фоновую задачу UPDATE_CONFIGURATION. Теперь ждем {period_minutes} минут"
            logger.info(message)
        except Exception as e:
            message = str(e)
            logger.error(
                f"⚠️Ошибка в фоновой задаче UPDATE_CONFIGURATION: {message}", exc_info=True)
        finally:
            if Config.get("LOG_TELEGRAM"):
                send_messege_to_boot(message)
        # Используем текущий интервал из конфигурации
        await asyncio.sleep(60 * period_minutes)

# Фоновая задача по информированию заинтересованных(workers и пока orders) о существовании executor на телефонах


async def task_ping():
    """Фоновая задача по отправке ping"""
    # from core.ping import ping_services
    # from core.telegram.telega import send_messege_to_boot
    while True:
        try:
            # Получаем текущие значения из конфигурации
            period_seconds = Config.PING_TIMEOUT_SECONDS
            message = f"Запуск фоновой задачи PING в {datetime.now().isoformat()} каждые {period_seconds} секунды"
            logger.info(message)
            result = ping_services()
            message = f"Выполнили фоновую задачу PING. Теперь ждем {period_seconds} секунд. Результат: {result}"
            logger.info(message)
        except Exception as e:
            message = "⚠️Ошибка в фоновой задаче PING:"+str(e)
            logger.error(message)
        finally:
            if Config.get("LOG_TELEGRAM"):
                send_messege_to_boot(message)
        # Используем текущий интервал из конфигурации
        await asyncio.sleep(period_seconds)


async def task_canary():
    """Фоновая задача по обновлению информации о сети"""
    while True:
        if Config.get('PERIOD_MINUTES_CANARY'):
            # Получаем текущие значения из конфигурации
            period_minutes = int(Config.PERIOD_MINUTES_CANARY)
            mess = f"Запуск канарейки в {datetime.now()} каждые {period_minutes} минуты"
            logger.info(mess)

            try:
                # TODO
                # from core.telegram.telega import send_messege_to_boot
                # from core.common import get_current_time
                # from core.email import EmailCreate,myEmail,getEmailSender
                sender = Config.SENDER
                data = EmailCreate(
                    toEmail="kaiby@yandex.ru", subject=f"{get_current_time()}. {sender.name}. Канарейка", body="Проверка связи")
                email = myEmail()
                if not data.sender:
                    # Теперь getEmailSender найден, так как импортирован
                    data.sender = getEmailSender()
                result = email.send(data)
                message = f"{get_current_time()}. {sender.name}. EMAIL.Канарейка. Результат:{result}"
                # from_phone_number=data.from_number_phone if data.from_number_phone else ''
            except Exception as e:
                message = f"⚠️Ошибка при запуске канарейки email: {e}"
                logger.error(message)
            finally:
                if Config.get("LOG_TELEGRAM"):
                    send_messege_to_boot(message)

            try:
                from models.phone import SMSRequest
                from core.phone import Phone
                # sim = Phone.getSim(data)
                for sim in sender.sims:
                    message = f"{get_current_time()}. {sender.name}.{sim.number}. SMS.Канарейка"
                    data: SMSRequest = SMSRequest(
                        to_phone_number="+79175729812", from_phone_number=sim.number, message=message)
                    if sim.status == "active":
                        Phone.sendSMS(data, sim)
            except Exception as e:
                message = f"⚠️Ошибка при запуске канарейки sim: {e}"
                logger.error(message)
            finally:
                if Config.get("LOG_TELEGRAM"):
                    send_messege_to_boot(message)
            # Используем текущий интервал из конфигурации
            await asyncio.sleep(60 * period_minutes)
        else:
            break


async def task_autossh_tunnel():
    """Фоновая задача по обновлению информации о сети"""
    sender = Config.SENDER
    while True:
        if Config.get('PERIOD_MINUTES_CHECK_AUTOSSH'):
            # Получаем текущие значения из конфигурации
            period_minutes = int(Config.PERIOD_MINUTES_CHECK_AUTOSSH)
            message = f"Запуск проверки работоспособности autossh {datetime.now()} каждые {period_minutes} минуты"
            # print(mess)
            logger.info(message)

            try:
                # TODO
                from core.telegram.telega import send_messege_to_boot
                from core.common import get_current_time
                message = f"{get_current_time()}. {sender.name}. AUTOSSH работает"
                # запуск autossh
                if Config.get("LOG_TELEGRAM"):
                    if Config.get("IP_ADDRESS_VPN_SERVER") and Config.get("PORT_VPN_SERVER") and Config.get("USERNAME_VPN_SERVER"):
                        # def ensure_tunnel(port=9090, remote="89.125.188.172", user="kai"):
                        ensure_tunnel(
                            port=Config.PORT_VPN_SERVER, remote=Config.IP_ADDRESS_VPN_SERVER, user="kai")
                pass
            except Exception as e:
                message = f"⚠️Ошибка проверки работоспособности autossh: {e}"
                logger.error(message)
            finally:
                if Config.get("LOG_TELEGRAM"):
                    send_messege_to_boot(message)

            # Используем текущий интервал из конфигурации
            await asyncio.sleep(60 * period_minutes)
        else:
            break


# Lifespan контекстный менеджер
@asynccontextmanager
async def lifespan(app):
    """
    Lifespan context manager для управления фоновыми задачами
    """
    # Startup
    logger.info("="*60)
    logger.info("ЗАПУСК ПРИЛОЖЕНИЯ")
    logger.info("="*60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"FastAPI version: {fastapi.__version__}")

    logger.info("Запускаем фоновые задачи")
    # task1 = asyncio.create_task(task_update_network_info())
    # background_tasks.append(task1)

    task2 = asyncio.create_task(task_update_configuration())
    background_tasks.append(task2)

    task3 = asyncio.create_task(task_ping())
    background_tasks.append(task3)

    task4 = asyncio.create_task(task_canary())
    background_tasks.append(task4)

    task5 = asyncio.create_task(task_autossh_tunnel())
    background_tasks.append(task5)

    logger.info("✓ Фоновые задачи запущены")
    logger.info("="*60)

    yield  # Приложение работает

    # Shutdown
    logger.info("="*60)
    logger.info("ОСТАНОВКА ПРИЛОЖЕНИЯ")
    logger.info("="*60)

    # Останавливаем фоновые задачи
    for task in background_tasks:
        task.cancel()

    # Ждем завершения всех задач
    await asyncio.gather(*background_tasks, return_exceptions=True)
    logger.info("Все задачи остановлены")


def create_router_for_management():
    """Создает роутер для управления конфигурацией"""
    from fastapi import APIRouter
    logger.info("Создаем роуты")

    router = APIRouter(prefix="/config", tags=["Configuration"])

    @router.post("/reload-config")
    async def reload_config():
        """
        Принудительная перезагрузка конфигурации.
        Возвращает все доступные параметры динамически.
        """
        # 1. Перезагружаем конфигурацию из файлов
        logger.info(
            "Принудительная перезагрузка конфигурации сервиса из конфигурационных файлов")
        Config.reload()
        config = Config.getItems().copy()
        config.update({"config_file": Config._env_file,
                       "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None})
        return {
            "message": "Конфигурация перезагружена",
            # "count": len(config_data),
            # "config": config_data
            "config": config
        }

    @router.get("/current")
    async def get_current_config():
        """Получить текущие значения конфигурации"""
        config = Config.getItems().copy()
        config.update({"config_file": Config._env_file,
                       "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None})
        return config

    return router


def create_app():
    from fastapi.middleware.cors import CORSMiddleware
    """Создание FastAPI приложения с lifespan"""
    config = Config.getItems().copy()
    logger.info("Создание приложения")
    app = FastAPI(
        title=f"{config['PHONE_NAME']}.API для отправки сообщений",
        version="1.0.0",
        description="Сервис для работы с СМС и наверное не только",
        openapi_version="3.1.0",
        lifespan=lifespan
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Добавляем роутер для управления конфигурации
    config_router = create_router_for_management()
    app.include_router(config_router)

    return app


if __name__ == "__main__":
    pass
    # print("Тестирование конфигурации...")
    # print(
    #     f"Начальный период обновления сети: {Config.PERIOD_MINUTES_UPDATE_NETWORKINFO}")
    # Config.reload()
    # print(
    #     f"После перезагрузки период обновления сети: {Config.PERIOD_MINUTES_UPDATE_NETWORKINFO}")
