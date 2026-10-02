import logging
import os
from logging.handlers import RotatingFileHandler

# Логер для критических ошибок!!!!

def setup_logger(path_log_folder:str):
    # Общий логгер
    # logger = logging.getLogger("app")
    # logger.setLevel(logging.INFO)
    # logger.propagate = False

    # fh = RotatingFileHandler("app.log", maxBytes=5*1024*1024, backupCount=3)
    # fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    # fh.setFormatter(fmt)
    # logger.addHandler(fh)

    # Логгер для событий с телефоном
    logger = logging.getLogger("critical_error_events")
# Защита от повторной инициализации того же имени логгера
    if getattr(logger, "_period_task_initialized", False):
        return logger
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh_phone = RotatingFileHandler(os.path.join(
        path_log_folder, "critical_error.log"), maxBytes=5*1024*1024, backupCount=5)
    fmt_phone = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s")
    fh_phone.setFormatter(fmt_phone)
    logger.addHandler(fh_phone)

    logger._period_task_initialized = True
    return logger




# Обычные действия
# logger.info("Пользователь авторизовался")

# События, связанные с телефоном
# phone_logger.info("Отправка SMS на номер +79990000000")
# phone_logger.warning("Не удалось получить статус телефона")
