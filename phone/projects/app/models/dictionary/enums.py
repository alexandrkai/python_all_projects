# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/dictionary/enums.py
from enum import Enum

class ResultStatus(str, Enum):
    OK = "ok"
    ERROR = "error"

class SimStatus(str, Enum):
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
    
class OperatorPhone(str,Enum):
    MTS="mts"
    BEELINE="beeline"
    TELE2="tele2"
    MEGAFON="megafon"