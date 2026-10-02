# Логгер только для конфигов
import logging,os
from logging.handlers import RotatingFileHandler


# сделаем свой config_logger
def get_period_task_logger(PATH_LOG_FOLDER,name):
    # Логгер для событий в конфигурации
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh_phone = RotatingFileHandler(os.path.join(
        PATH_LOG_FOLDER, "period_tasks.log"), maxBytes=5*1024*1024, backupCount=5)
    fmt_phone = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s")
    fh_phone.setFormatter(fmt_phone)
    logger.addHandler(fh_phone)

    # return logger, phone_logger
    return logger

