# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/phone.py
import re
from ._base import Optional, Field, BaseModel, model_validator, Self
from log.log import logger


class SMSRequest(BaseModel):
    to_phone_number: str      # Номер телефона (например, +79991234567)
    from_phone_number: str = Field(default=None)
    # Текст сообщения
    message: str = Field(
        max_length=300, description="Размер сообщения(не более 300 символов)")
    simSlot: Optional[int] = Field(
        default=None, ge=0, le=1, description="Номер слота симки(от 0б до 1)")
    

    @model_validator(mode='after')
    def check_phone_match(self) -> Self:
        PHONE_PATTERN_RUSSIA = re.compile(
            r"^\+7\(?\d{3}\)?[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}$")
        if not PHONE_PATTERN_RUSSIA.match(self.to_phone_number) or  (self.from_phone_number and not PHONE_PATTERN_RUSSIA.match(self.from_phone_number)):
            error_message = "⚠️Неправильный номер телефона. Он должен соответствовать формату +71234567890"
            logger.error(error_message)
            raise ValueError(error_message)
        return self
