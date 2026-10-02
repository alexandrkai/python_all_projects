# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/phone.py
import random

from config.config import (
    Config,
    get_full_error_message,
    send_message_to_telegram,
)
from core.log.log import get_logger
from schemas import SIM, ResultShellCommandSendSMS, ResultStatus, SimStatus, SMSRequest

from core.common import runShellCommand

logger = get_logger(__name__)


class SimNotFoundError(Exception):
    """Исключение при отсутствии подходящей SIM-карты."""


class SmsSendError(Exception):
    """Исключение при ошибке отправки SMS."""


def select_sim(data: SMSRequest) -> SIM:
    all_sims = getattr(Config.SENDER, "sims", []) or []
    active_sims = [sim for sim in all_sims if sim.status == SimStatus.ACTIVE]

    if not active_sims:
        err = SimNotFoundError("Нет активных SIM-карт в конфигурации")
        full_msg = get_full_error_message(e=err, error_message="Ошибка выбора сим-карты", prefix="SELECT_SIM")
        logger.critical(full_msg)
        send_message_to_telegram(full_msg)
        raise err

    # 1. Если слот явно передан клиентом — ищем его среди активных
    if data.sim_slot is not None:
        matched_sims = [sim for sim in active_sims if sim.slot == data.sim_slot]
        if not matched_sims:
            err = SimNotFoundError(f"Активная сим-карта в слоте {data.sim_slot} не найдена")
            full_msg = get_full_error_message(e=err, error_message="Слот недоступен", prefix="SELECT_SIM")
            logger.critical(full_msg)
            send_message_to_telegram(full_msg)
            raise err
        return matched_sims[0]

    # 2. Если доступна всего одна симка
    if len(active_sims) == 1:
        sim = active_sims[0]
        data.sim_slot = sim.slot
        return sim

    # 3. Балансировка по весам
    slot_weights = getattr(Config.SENDER, "slot_weights", None) or {0: 50, 1: 50}
    weights = [slot_weights.get(sim.slot, 50) for sim in active_sims]
    sim = random.choices(active_sims, weights=weights, k=1)[0]

    data.sim_slot = sim.slot
    return sim


class Phone:
    @staticmethod
    def send_sms(data: SMSRequest) -> ResultShellCommandSendSMS:
        """
        Отправляет SMS через termux-sms-send.
        """
        sim = select_sim(data)

        # Синтаксис: termux-sms-send -s  -n  
        command = [
            "termux-sms-send",
            "-s", str(sim.slot),
            "-n", str(data.number),
            str(data.message),
        ]

        result = runShellCommand(command)

        if result.status == ResultStatus.OK:
            sms_result = ResultShellCommandSendSMS.from_command_result(
                base=result,
                sim_sender=sim,
                sender=Config.SENDER.to_ShortPhoneSender(),
            )
            # Уведомление об успешной отправке
            send_message_to_telegram(
                f"✅ SMS отправлено: {Config.SENDER.name}|{sim.slot}|{sim.number} -> {data.number}\n"
            )
            return sms_result

        # Обработка ошибки выполнения команды
        err = SmsSendError(result.error or "Команда termux-sms-send вернула статус ERROR")
        full_msg = get_full_error_message(
            e=err,
            error_message=f"Слот {sim.slot} ({sim.number}) -> {data.number}",
            prefix="SMS_SEND",
        )
        logger.error(full_msg)
        send_message_to_telegram(full_msg)
        raise err