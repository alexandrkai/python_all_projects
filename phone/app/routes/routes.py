# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/routes/routes.py
import os
import subprocess
import sys
from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from config.config import (
    Config,
    get_full_error_message,
    send_message_to_telegram,
)
from core.common import (
    batteryStatus,
    callLog,
    contactList,
    networkInfo,
    smsList,
    startSSH,
)
from core.email import myEmail
from core.phone import Phone
from app.core.log.log import get_logger
from schemas import (
    EmailRequest,
    ResultShellCommandSendSMS,
    SMSRequest,
    TelegramRequest,
)

logger = get_logger(__name__)


def create_router_others():
    """Создание роутера для остальных страниц"""

    class TypeSMS(str, Enum):
        all = "all"
        inbox = "inbox"
        sent = "sent"
        draft = "draft"
        outbox = "outbox"

    others = APIRouter()

    @others.get("/")
    def root():
        return RedirectResponse(url="/docs")

    @others.get("/whoami")
    def whoami():
        return Config.SENDER

    @others.post("/send-sms-message", tags=["Телефон"], response_model=ResultShellCommandSendSMS)
    def send_sms(data: SMSRequest):
        """Отправляет SMS через termux-sms-send."""
        try:
            return Phone.send_sms(data)
        except ValueError as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Ошибка валидации SMS: {data.model_dump_json()}",
                prefix="ROUTE_SMS",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Сбой отправки SMS: {data.model_dump_json()}",
                prefix="ROUTE_SMS",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.post("/send-email-message", tags=["Электронная почта"])
    def send_email(data: EmailRequest):
        """Отправляет Email через SMTP."""
        try:
            return myEmail.send(data)
        except ValueError as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Ошибка данных Email к {data.to_email}",
                prefix="ROUTE_EMAIL",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Сбой отправки Email к {data.to_email}",
                prefix="ROUTE_EMAIL",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.post("/send-telegram--message", tags=["Telegram"])
    def send_telegram_to_msgprobot(data: TelegramRequest):
        """Отправляет сообщение в Telegram через Bot API."""
        try:
            target_chat = data.chat_id or "5151092623"
            response = send_message_to_telegram(data.text, chat_id=target_chat)
            if response is None:
                raise RuntimeError("Не удалось доставить сообщение в Telegram")
            return response
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message="Ошибка отправки сообщения в Telegram",
                prefix="ROUTE_TELEGRAM",
            )
            logger.error(full_msg)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/battery-status", tags=["System"])
    def battery_status():
        """Статус батареи"""
        try:
            return batteryStatus()
        except Exception as e:
            logger.error(f"⚠️ Error in battery_status: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/call-log", tags=["System"])
    def call_log(
        limit: int = Query(default=10),
        offset: int = Query(default=0),
    ):
        """Список вызовов"""
        try:
            return callLog(limit, offset)
        except Exception as e:
            logger.error(f"⚠️ Error in call_log: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/contact-list", tags=["System"])
    def contact_list():
        """Список контактов"""
        try:
            return contactList()
        except Exception as e:
            logger.error(f"⚠️ Error in contact_list: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/sms-list", tags=["System"])
    def sms_list(
        showDate: bool = Query(default=True),
        limit: int = Query(default=10),
        showNumberPhone: bool = Query(default=True),
        offset: int = Query(default=0),
        typeSMS: TypeSMS = Query(default=TypeSMS.all),
    ):
        """Список СМС"""
        try:
            return smsList(showDate, limit, showNumberPhone, offset, typeSMS.value)
        except Exception as e:
            logger.error(f"⚠️ Error in sms_list: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/network-info", tags=["System"])
    def network_info_route():
        """Информация о сети"""
        try:
            return networkInfo()
        except Exception as e:
            logger.error(f"⚠️ Error in network_info: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/start-ssh", tags=["System"])
    def start_ssh():
        try:
            return startSSH()
        except Exception as e:
            logger.error(f"⚠️ Error in start_ssh: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat(),
                },
            )

    @others.get("/restart", tags=["Service"])
    def api_restart():
        """Перезапуск сервиса через внешний скрипт."""
        try:
            restart_script = os.path.join(
                Config.PATH_APPLICATION_FOLDER, "restart_service.py"
            )
            result_proc = subprocess.run(
                [sys.executable, restart_script],
                capture_output=True,
                text=True,
            )
            return {
                "status": "ok",
                "message": "Сервис перезапущен",
                "output": result_proc.stdout,
                "error": result_proc.stderr,
                "returncode": result_proc.returncode,
            }
        except Exception as e:
            logger.error(f"⚠️ Ошибка при перезагрузке: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/restart-termux-am", tags=["System"])
    def restart_termux_am():
        """Перезапускает Termux через Activity Manager"""
        try:
            restart_cmd = """
            pkill -f com.termux
            sleep 1
            am start -n com.termux/.HomeActivity
            """
            result = subprocess.run(
                ["nohup", "bash", "-c", restart_cmd],
                capture_output=True,
                text=True,
            )
            return {
                "status": "warning",
                "message": "Команда отправлена, но Termux может перезапуститься",
                "output": result.stdout,
                "error": result.stderr,
            }
        except Exception as e:
            logger.error(f"⚠️ Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/restart-service", tags=["Service"])
    def restart_termux_service():
        """Перезапускает сервис внутри Termux"""
        try:
            script_path = os.path.join(
                Config.PATH_APPLICATION_FOLDER, "restart_termux_service.sh"
            )
            process = subprocess.Popen(
                ["bash", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            )
            return {
                "status": "ok",
                "message": "Сервис Termux перезапускается...",
                "pid": process.pid,
            }
        except Exception as e:
            logger.error(f"⚠️ Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/schedule-restart", tags=["System"])
    def schedule_termux_restart():
        """Планирует перезапуск Termux через 5 секунд"""
        try:
            script_content = f"""#!/data/data/com.termux/files/usr/bin/bash
sleep 5
cd {Config.PATH_APPLICATION_FOLDER}
nohup python run.py > api.log 2>&1 &
"""
            script_path = "/data/data/com.termux/files/home/delayed_restart.sh"
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)

            os.chmod(script_path, 0o755)
            subprocess.Popen(["bash", script_path])

            return {
                "status": "ok",
                "message": "Termux сервис будет перезапущен через 5 секунд",
            }
        except Exception as e:
            logger.error(f"⚠️ Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/soft-restart-termux", tags=["System"])
    def soft_restart():
        """Мягкий перезапуск - отправляет intent на обновление Termux"""
        try:
            cmd = "am start -a android.intent.action.MAIN -n com.termux/.HomeActivity"
            result = subprocess.run(cmd.split(), capture_output=True, text=True)
            return {
                "status": "ok" if result.returncode == 0 else "error",
                "message": "Intent отправлен",
                "output": result.stdout,
                "error": result.stderr,
            }
        except Exception as e:
            logger.error(f"⚠️ Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    # @others.post("/ping-services", tags=["Services"])
    # def ping_services():
    #     from core.ping import ping_services

    #     return ping_services()

    return others

def create_router_for_management():
    """Создает роутер для управления конфигурацией."""
    from fastapi import APIRouter

    router = APIRouter(prefix="/config", tags=["Конфигурация"])

    @router.post("/reload-config")
    async def reload_config():
        """Принудительная перезагрузка конфигурации из файлов и Redis."""
        logger.info("Принудительная перезагрузка конфигурации через API")
        Config.reload()
        config_data = Config.getItems().copy()
        config_data.update({
            "config_file": Config._env_file,
            "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None,
        })
        return {
            "message": "Конфигурация перезагружена",
            "config": config_data,
        }

    @router.get("/current")
    async def get_current_config():
        """Получить текущие параметры конфигурации."""
        config_data = Config.getItems().copy()
        config_data.update({
            "config_file": Config._env_file,
            "last_load_time": Config._last_load_time.isoformat() if Config._last_load_time else None,
        })
        return config_data

    return router

