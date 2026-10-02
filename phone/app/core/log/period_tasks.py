import logging
import os
from logging.handlers import RotatingFileHandler


def get_period_task_logger(PATH_LOG_FOLDER, name):
    logger = logging.getLogger(name)

    # Защита от повторной инициализации того же имени логгера
    if getattr(logger, "_period_task_initialized", False):
        return logger

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    fh_phone = RotatingFileHandler(
        os.path.join(PATH_LOG_FOLDER, "period_tasks.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    fmt_phone = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s"
    )
    fh_phone.setFormatter(fmt_phone)
    logger.addHandler(fh_phone)

    logger._period_task_initialized = True
    return logger