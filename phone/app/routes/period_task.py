# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/routes/period_task.py
import asyncio

# Используем актуальные методы логирования и отправки сообщений
from config.config import (
    PATH_LOG_FOLDER,
    Config,
    get_full_error_message,
    send_message_to_telegram,
)
from core.autossh import ensure_tunnel
from core.common import get_current_datetime_str
from core.email import myEmail
from core.phone import Phone
from schemas import EmailRequest, MessagePayload, SimStatus, SMSRequest

from app.core.log.period_tasks import get_period_task_logger

logger = get_period_task_logger(PATH_LOG_FOLDER, __file__)


async def task_update_configuration():
    """Фоновая задача по периодической перезагрузке конфигурации."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_UPDATE_CONFIGURATION")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(
            f"ℹ️ Запуск фоновой задачи - обновления конфигурации каждые {period_minutes} минут")

        try:
            Config.reload()
            logger.debug(
                f"✅ Выполнили фоновую задачу обновления конфигурации. Ждем {period_minutes} минут")
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Сбой перезагрузки конфигурации",
                prefix="UPDATE_CONFIG",
            )
            logger.error(full_msg, exc_info=True)
            critical_error_logger.error(
                f"Не удалось перезагрузить конфигурацию:{str(e)}")
            send_message_to_telegram(full_msg)

        await asyncio.sleep(60 * period_minutes)


async def task_canary():
    """Фоновая задача-канарейка (периодическая проверка отправки Email и SMS)."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_CANARY")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(
            f"Запуск фоновой задачи - отправка канареек каждые {period_minutes} минут")

        sender = Config.SENDER

        # 1. Проверка отправки Email
        try:
            sender_name = getattr(sender, "name", "DEVICE")
            email_data = EmailRequest(
                to_email="kaiby@yandex.ru",
                message=MessagePayload(
                    title=f"{get_current_datetime_str()}. {sender_name}. EMAIL-Канарейка",
                    body="Проверка связи канарейки",
                    footer="Сервис мониторинга",
                ),
            )
            result = myEmail.send(email_data)
            message = f"✅ EMAIL Канарейка отправлена: {result['sender']}|{result['data']['sender_email']}->{result['data']['to']}"
            logger.info(message)
            send_message_to_telegram(message)
        except Exception as e:
            critical_error_logger.error(
                f"Не удалось отправить EMAIL-канарейку:{str(e)}")
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
            active_sims = [
                sim for sim in available_sims if sim.status == SimStatus.ACTIVE]

            for sim in active_sims:
                sms_text = f"{get_current_datetime_str()}. {getattr(sender, 'name', '')}. {sim.number}. SMS.Канарейка"
                sms_data = SMSRequest(
                    number="+79175729812",
                    message=sms_text,
                    sim_slot=sim.slot,
                )
                Phone.send_sms(sms_data)
                send_message_to_telegram(
                    f"✅ SMS Канарейка отправлена со слота {sim.slot} ({sim.number})")
                logger.info(
                    f"✅ SMS Канарейка {Config.SENDER.name}.{sim.slot}.({sim.number})->+79175729812")

        except Exception as e:
            critical_error_logger.error(
                f"Не удалось отправить SMS-канарейку:{str(e)}")
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка при отправке канареечного SMS",
                prefix="CANARY_SMS",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
        logger.debug(
            f"✅ Выполнили фоновую задачу отправок канареек. Ждем {period_minutes} минут")
        await asyncio.sleep(60 * period_minutes)


async def task_autossh_tunnel():
    """Фоновая задача контроля SSH/SOCKS5-туннеля."""
    while True:
        period_minutes = Config.get("PERIOD_MINUTES_CHECK_AUTOSSH")
        if not period_minutes:
            break

        period_minutes = int(period_minutes)
        logger.info(
            f"ℹ️ Запуск фоновой задачи - проверка autossh каждые {period_minutes} минут")

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
            critical_error_logger.error(
                f"Ошибка проверки и запуска ssh-тунеля:{str(e)}")
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка проверки autossh-туннеля",
                prefix="AUTOSSH",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)

        await asyncio.sleep(60 * period_minutes)
