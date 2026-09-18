# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/results.py
from ._base import Optional, Union, BaseModel, Field, datetime
from .dictionary.enums import ResultStatus
from .senders import PhoneSender
from fastapi.responses import JSONResponse


class Result(BaseModel):
    status: ResultStatus
    due_date: datetime
    sender:  Optional[PhoneSender] = None
    detail: Optional[str] = None  # Только для ошибок
    data: Union[str, None, dict] = None

    @property
    def is_error(self) -> bool:
        return self.status == ResultStatus.ERROR

    @property
    def is_ok(self) -> bool:
        return self.status == ResultStatus.OK

    def to_response(self, log_message: str = None) -> JSONResponse:
        """
        Преобразует результат выполнения в JSONResponse с корректным статус-кодом.
        """
        from log.log import logger  # Импорт внутри метода, чтобы избежать циклической зависимости, если logger импортирует models

        status_code = 200 if self.is_ok else 500

        # Если передано сообщение для лога при ошибке
        if log_message and self.is_error:
            logger.error("⚠️"+log_message)
            # Создаем копию результата для ответа, чтобы добавить/заменить деталь без изменения оригинала
            result_dict = self.model_dump(mode='json')
            result_dict["detail"] = log_message
            return JSONResponse(status_code=status_code, content=result_dict)

        # Стандартный возврат (mode='json' корректно сериализует datetime и enum)
        return JSONResponse(status_code=status_code, content=self.model_dump(mode='json'))
