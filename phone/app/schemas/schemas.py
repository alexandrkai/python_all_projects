from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing_extensions import Self

from .enums import OperatorPhone, ResultStatus, SimStatus, TaskStatus, TaskType

PHONE_PATTERN_RUSSIA = re.compile(
    r"^\+7(?:\(\d{3}\)|\d{3})[ -]?\d{3}[ -]?\d{2}[ -]?\d{2}$"
)


class ORMBaseModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class EmailSender(BaseModel):
    smtp_server: str
    smtp_port: int = Field(default=587)
    smtp_username: EmailStr
    smtp_password: str


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
        ..., max_length=300, description="Размер сообщения (не более 300 символов)"
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


class SIM(BaseModel):
    slot: int
    number: str
    status: SimStatus
    operator: OperatorPhone | None = None


class PhoneSender(BaseModel):
    name: str
    sims: list[SIM]
    mac: str | None = None
    ip: str | None = None
    url: str | None = None
    port: int | None = None


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
    execute_at: datetime | None = Field(None, description="Время выполнения для one_time")
    cron_expression: str | None = Field(None, description="Cron выражение для cron задач")
    interval_seconds: int | None = Field(None, description="Интервал в секундах для периодических задач")
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