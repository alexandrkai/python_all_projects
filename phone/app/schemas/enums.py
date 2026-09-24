import enum


class ResultStatus(str, enum.Enum):
    OK = "ok"
    ERROR = "error"


class SimStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

    # Добавляем метод для конвертации чисел при создании модели
    @classmethod
    def _missing_(cls, value):
        if value == 1 or value == "1":
            return cls.ACTIVE
        if value == 0 or value == "0":
            return cls.INACTIVE
        return None


class OperatorPhone(str, enum.Enum):
    MTS = "mts"
    BEELINE = "beeline"
    TELE2 = "tele2"
    MEGAFON = "megafon"
    OTHERS = "others"


class TaskType(str, enum.Enum):
    ONE_TIME = "one_time"
    PERIODIC = "periodic"
    CRON = "cron"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
