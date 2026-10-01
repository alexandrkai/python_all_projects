from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    SecretStr,
    conint,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from .enums import ResultStatus, SimStatus, TaskStatus, TaskType

PHONE_PATTERN_RUSSIA = re.compile(
    r"^\+7(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Регулярка для Telegram Chat ID:
# 1. Либо целое число (положительное или отрицательное, возможно с -100): ^-?\d+$
# 2. Либо username канала/группы: ^@[a-zA-Z0-9_]{5,32}$
TELEGRAM_CHAT_ID_PATTERN = re.compile(r"^(?:-?\d+|@[a-zA-Z0-9_]{5,32})$")


class PhoneBase(BaseModel):
    number: str 

    @field_validator("number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean_phone = re.sub(r"[\s\(\)\-]", "", v)
        if clean_phone.startswith("8") and len(clean_phone) == 11:
            clean_phone = "+7" + clean_phone[1:]
        if not re.match(PHONE_PATTERN_RUSSIA, clean_phone):
            raise ValueError("Номер телефона должен быть в формате +7XXXXXXXXXX")
        return clean_phone


class EmailParameters(BaseModel):
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: EmailStr
    SMTP_PASSWORD: SecretStr

    @field_validator("SMTP_USERNAME")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v:
            raise ValueError("SMTP_USERNAME не может быть пустым")
        clean_email = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean_email):
            raise ValueError("Некорректный формат SMTP_USERNAME")
        if len(clean_email) > 100:
            raise ValueError("SMTP_USERNAME не должен превышать 100 символов")
        return clean_email


class EmailSender(BaseModel):
    name: str
    description: str | None = None
    settings: EmailParameters

class MessagePayload(BaseModel):
    title: str = Field(..., min_length=1, description="Заголовок сообщения (актуально для email/push)")
    body: str = Field(..., min_length=1, description="Основное тело сообщения")
    footer: str | None = Field(default=None, description="Подвал сообщения (ссылка на отписку, подпись)")

class EmailRequest(BaseModel):
    to_email: EmailStr
    message:MessagePayload
    
    @field_validator("to_email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v:
            raise ValueError("to_email не может быть пустым")
        clean_email = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean_email):
            raise ValueError("Некорректный формат to_email")
        if len(clean_email) > 100:
            raise ValueError("to_email не должен превышать 100 символов")
        return clean_email
    
class EmailCreate(EmailRequest):
    sender: EmailSender | None = None
    # from_number_phone: str | None = None

    # @model_validator(mode="after")
    # def check_body_html_body(self) -> Self:
    #     has_body = bool(self.body and self.body.strip())
    #     has_html = bool(self.html_body and self.html_body.strip())
    #     if not has_body and not has_html:
    #         raise ValueError(
    #             "⚠️ У email один из параметров (body или html_body) должен быть заполнен!"
    #         )
    #     return self
    
    


class SMSRequest(PhoneBase):
    # number: str #телефон получателя
    # from_phone_number: str | None = None #телефон заказчика
    message: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Размер сообщения (не более 500 символов)",
    )

    sim_slot: int | None = Field(
        default=None, ge=0, le=1, description="Номер слота симки (от 0 до 1)"
    )

    # @model_validator(mode="after")
    # def check_phone_match(self) -> Self:
    # for number in (self.number, self.from_phone_number):
    #     if number and not PHONE_PATTERN_RUSSIA.match(number):
    #         raise ValueError(
    #             f"⚠️ Неправильный номер телефона: '{number}'. Он должен соответствовать формату +7XXXXXXXXXX"
    #         )
    # if not self.message:
    #     raise ValueError(f"⚠️Отправка пустого сообщения невозможна!")
    # return self
    @field_validator("message")
    @classmethod
    def not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("⚠️ Отправка пустого сообщения невозможна!")
        return v


class SIM(PhoneBase):
    slot: conint(ge=0, le=1)  # type: ignore
    status: SimStatus
    operator: str | None = None


class ShortPhoneSender(BaseModel):
    name: str
    description: str | None = None
    ip: str | None = None
    url: str | None = None
    port: int | None = None
    phones: list[str] | None = None


class PhoneSender(BaseModel):
    name: str
    description: str | None = None
    mac: str | None = None
    ip: str | None = None
    url: str | None = None
    port: int | None = None
    sims: list[SIM] | None = None
    # Значения по умолчанию 50/50, если в JSON поле не указано:
    slot_weights: dict[int, int] | None = Field(
        default_factory=lambda: {0: 50, 1: 50},
        description="Веса слотов для балансировки отправки SMS",
    )
    updated_at: datetime = Field(default_factory=datetime.now)  # noqa: DTZ005

    def to_ShortPhoneSender(self) -> ShortPhoneSender:
        return ShortPhoneSender(
            name=self.name,
            description=self.description,
            ip=self.ip,
            url=self.url,
            port=self.port,
            phones=[sim.number for sim in self.sims] if self.sims else [],
        )

class TelegramChatId(BaseModel):
    phone: str
    chat_id: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        clean_phone = re.sub(r"[\s\(\)\-]", "", v)
        if clean_phone.startswith("8") and len(clean_phone) == 11:
            clean_phone = "+7" + clean_phone[1:]
        if not re.match(PHONE_PATTERN_RUSSIA, clean_phone):
            raise ValueError("Номер телефона должен быть в формате +7XXXXXXXXXX")
        return clean_phone

    @field_validator("chat_id")
    @classmethod
    def validate_chat_id(cls, v: str) -> str:
        clean_chat_id = str(v).strip()
        if not clean_chat_id:
            raise ValueError("chat_id не может быть пустым")

        if not TELEGRAM_CHAT_ID_PATTERN.match(clean_chat_id):
            raise ValueError(
                "Некорректный chat_id. Допустимо: целое число (например, '5151092623', '-1001234567890') "
                "или публичный канал (например, '@my_channel')"
            )

        return clean_chat_id
    

class ResultShellCommand(BaseModel):
    status: ResultStatus
    due_date: datetime
    # sender: PhoneSender | None = None
    error: str | None = None
    output: str | None = None
    data: str | dict[str, Any] | None = None

    @property
    def is_error(self) -> bool:
        return self.status == ResultStatus.ERROR

    @property
    def is_ok(self) -> bool:
        return self.status == ResultStatus.OK

    def to_response(self, log_message: str | None = None) -> JSONResponse:
        status_code = 200 if self.is_ok else 500
        result_dict = self.model_dump(mode="json")
        if log_message and self.is_error:
            result_dict["detail"] = log_message
        return JSONResponse(status_code=status_code, content=result_dict)


class ResultShellCommandSendSMS(ResultShellCommand):
    sim_sender: SIM
    sender: ShortPhoneSender | None = None

    @classmethod
    def from_command_result(
        cls,
        base: ResultShellCommand,
        sim_sender: SIM,
        sender: ShortPhoneSender | None = None,
    ) -> "ResultShellCommandSendSMS":
        return cls(
            **base.model_dump(),
            sim_sender=sim_sender,
            sender=sender,
        )

    def to_json(self) -> str:
        # d = cls.model_dump(mode="json")
        # return json.dumps(d)
        return self.model_dump_json()

    def to_dict(self) -> dict:
        # d = cls.model_dump(mode="json")
        # return json.dumps(d)
        return self.model_dump()


class Senders(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    emails: list[EmailSender] | None = Field(default=None)
    phones: list[PhoneSender] | None = Field(default=None)
    telegram_chat_ids:list[TelegramChatId] | None = Field(default=None)

class TaskRequest(BaseModel):
    task_name: str = Field(..., description="Название задачи")
    task_type: TaskType = Field(default=TaskType.ONE_TIME)
    execute_at: datetime | None = Field(
        None, description="Время выполнения для one_time")
    cron_expression: str | None = Field(
        None, description="Cron выражение для cron задач")
    interval_seconds: int | None = Field(
        None, description="Интервал в секундах для периодических задач")
    function_name: str = Field(..., description="Имя функции для выполнения")
    function_args: dict[str, Any] = Field(default_factory=dict)
    function_kwargs: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class TaskResponse(BaseModel):
    task_id: str
    task_name: str
    task_type: TaskType
    status: TaskStatus
    execute_at: datetime | None = None
    created_at: datetime
    result: dict[str, Any] | None = None
    error: str | None = None


class TelegramRequest(BaseModel):
    chat_id: int | str
    text: str
