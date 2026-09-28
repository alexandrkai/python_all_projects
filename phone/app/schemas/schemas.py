from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    conint,
    field_validator,
    model_validator,
)
from typing_extensions import Self

from .enums import ResultStatus, SimStatus, TaskStatus, TaskType

PHONE_PATTERN_RUSSIA = re.compile(r"^\+7(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}$")
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# class ORMBaseModel(BaseModel):
#     model_config = ConfigDict(from_attributes=True)


class PhoneBase(BaseModel):
    number: str

    @field_validator("number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        clean_phone = re.sub(r"[\s\(\)\-]", "", v)
        if clean_phone.startswith("8") and len(clean_phone) == 11:
            clean_phone = "+7" + clean_phone[1:]
        if not re.match(PHONE_PATTERN_RUSSIA, clean_phone):
            raise ValueError(
                "Номер телефона должен быть в формате +7XXXXXXXXXX"
            )
        return clean_phone


class EmailParameters(BaseModel):
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: EmailStr
    SMTP_PASSWORD: str

    @field_validator("SMTP_USERNAME")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not v:
            raise ValueError("SMTP_USERNAME не может быть пустым")
        clean_email = v.strip().lower()
        if not re.match(EMAIL_REGEX, clean_email):
            raise ValueError("Некорректный формат SMTP_USERNAME")
        if len(clean_email) > 100:
            raise ValueError("Email не должен превышать 100 символов")
        return clean_email

class EmailSender(BaseModel):
    name: str
    description: str | None = None
    settings: EmailParameters

class EmailCreate(BaseModel):
    to_email: EmailStr
    subject: str
    body: str | None = None
    html_body: str | None = None
    sender: EmailSender | None = None
    from_number_phone: str | None = None

    @model_validator(mode="after")
    def check_body_html_body(self) -> Self:
        has_body = bool(self.body and self.body.strip())
        has_html = bool(self.html_body and self.html_body.strip())
        if not has_body and not has_html:
            raise ValueError(
                "⚠️ У email один из параметров (body или html_body) должен быть заполнен!"
            )
        return self


class SMSRequest(BaseModel):
    to_phone_number: str
    from_phone_number: str | None = None
    message: str = Field(
        ..., max_length=500, description="Размер сообщения (не более 300 символов)"
    )
    
    sim_slot: int | None = Field(
        default=None, ge=0, le=1, description="Номер слота симки (от 0 до 1)"
    )

    @model_validator(mode="after")
    def check_phone_match(self) -> Self:
        for number in (self.to_phone_number, self.from_phone_number):
            if number and not PHONE_PATTERN_RUSSIA.match(number):
                raise ValueError(
                    f"⚠️ Неправильный номер телефона: '{number}'. Он должен соответствовать формату +7XXXXXXXXXX"
                )
        return self


class SIM(PhoneBase):
    slot: conint(ge=0, le=1)  # type: ignore
    status: SimStatus
    operator: str | None = None


class PhoneSender(BaseModel):
    name: str
    description: str | None = None
    mac: str | None = None
    ip: str | None = None
    url: str | None = None
    port: int | None = None
    sims: list[SIM]
    updated_at: datetime = Field(default_factory=lambda: datetime.now())  # noqa: DTZ005


class Result(BaseModel):
    status: ResultStatus
    due_date: datetime
    sender: PhoneSender | None = None
    detail: str | None = None
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


class Senders(BaseModel):
    email: list[EmailSender] | None = None
    phone: list[PhoneSender] | None = None


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
