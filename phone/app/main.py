# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/main.py
import uvicorn
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.log.log import get_logger

# Импорты функций создания роутеров
from app.routes.app import create_app
from app.routes.routes import create_router_for_management, create_router_others

logger = get_logger(__file__)

# Получаем экземпляр приложения (с уже настроенным lifespan)
app = create_app()

# Глобальный обработчик ошибок валидации


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    logger.debug(f"Какая-то ошибка по адресу {request.url}")
    for error in exc.errors():
        locs = [str(loc) for loc in error['loc'] if loc != 'body']
        field = " -> ".join(locs)

        # Получаем сообщение об ошибке
        if error['type'] == 'value_error':
            # Для кастомных ValueError берем сообщение из контекста
            ctx_error = error.get('ctx', {}).get('error')
            message = str(ctx_error) if ctx_error else error['msg']
        else:
            # Для стандартных ошибок валидации
            message = error['msg']

        errors.append({
            "field": field,
            "message": message,
            "type": error['type']
        })

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "status": "error",
            "message": "Ошибка валидации данных",
            "errors": errors
        }
    )

# Подключаем основной роутер (из routes.py)
app.include_router(create_router_others())
app.include_router(create_router_for_management())

if __name__ == "__main__":
    from config.config import Config
    # Проверяем конфигурацию при запуске
    logger.info(f"Запуск сервера на порту {Config.PORT_APPLICATION}")
    logger.info(
        f"Период обновления сети: {Config.PERIOD_MINUTES_UPDATE_NETWORKINFO} минут")
    logger.info(
        f"Период обновления конфигурации: {Config.PERIOD_MINUTES_UPDATE_CONFIGURATION} минут")

    # Запускаем сервер
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(Config.PORT_APPLICATION),
        # reload=True # Можно раскомментировать для разработки
    )
