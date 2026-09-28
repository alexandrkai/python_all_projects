# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/phone.py
import random
import re

from config.config import Config
from log.log import get_logger
from schemas import SIM, SimStatus, SMSRequest

from core.common import runShellCommand

logger = get_logger(__name__)


class Phone:
    # Регулярное выражение (дублируем из модели для надежности или используем импорт)
    PHONE_PATTERN_RUSSIA = re.compile(
        r"^\+7\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}$")

    @staticmethod
    def getSim(data: SMSRequest) -> SIM:
        if not data.simSlot is None:
            active_sims = [sim for sim in Config.SENDER.sims if sim.status ==
                           SimStatus.ACTIVE and sim.slot == data.simSlot]
        else:
            active_sims = [
                sim for sim in Config.SENDER.sims if sim.status == SimStatus.ACTIVE]
        if not active_sims:
            error_msg = "⚠️Нет активных SIM-карт в конфигурации"
            logger.critical(error_msg)
            raise Exception(error_msg)
        sim = random.choice(active_sims)
        logger.debug(
            f"Для отправки была выбрана симка {sim.model_dump_json()}")
        return sim

    @staticmethod
    def sendSMS(data: SMSRequest, sim: SIM | None = None) -> dict:
        """
        Отправляет SMS через termux-sms-send.
        Возвращает объект dict.
        """
        from schemas.enums import ResultStatus
        # Проверка валидности номера (доп. проверка на уровне выполнения)
        if not Phone.PHONE_PATTERN_RUSSIA.match(data.to_phone_number):
            error_message = f"⚠️Неправильный номер телефона {data.to_phone_number}. Он должен соответствовать формату +71234567890"
            logger.error(error_message)
            raise ValueError(error_message)

        # Проверка, что отправитель найден
        if not sim:
            # Если слот был указан, но симка не найдена
            if data.simSlot is not None:
                error_message = f"⚠️Сим-карта в слоте {data.simSlot} не найдена или неактивна"
                logger.error(error_message)
                raise Exception(error_message)
            else:
                error_message = f"⚠️Не удалось выбрать случайную сим-карту (нет активных)"
                logger.error(error_message)
                raise Exception(error_message)

        # Получаем номер слота
        simSlot = sim.slot

        # Формируем команду
        # termux-sms-send -s slotnumber number message
        command = ["termux-sms-send"]
        command.extend(["-s", str(simSlot)])
        command.extend(["-n", data.to_phone_number, data.message])

        # Выполняем команду через runShellCommand, который вернет Result
        result = runShellCommand(command)
        if result.status == ResultStatus.OK:
            result = result.model_dump()
            result["sender"] = {
                "sender": Config.SENDER.name, "sim": sim.number}
            return result
        raise Exception(result.detail)
