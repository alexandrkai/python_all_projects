# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/routes/routes.py
import requests
import subprocess
import sys
import os
from datetime import datetime
from typing import Union, List, Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, Body
from fastapi.responses import JSONResponse, RedirectResponse

# Импорты моделей и конфига
from models import *
from models._base import *
from models.dictionary.enums import ResultStatus, SimStatus
from config.config import Config
from routes.period_task import *
from core.telegram.telega import send_messege_to_boot

# Импорты функций ядра
from core.common import (
    batteryStatus, callLog,
    contactList, smsList, startSSH, networkInfo
)
from core.email import myEmail
# Импортируем вспомогательные функции получения отправителей
from core.phone import Phone, get_logger
from core.email import getEmailSender
# from log.log import get_logger

logger = get_logger(__name__)


def create_router_others():
    """Создание роутера для остальных страниц"""
    from enum import Enum

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

    @others.post("/send-sms", tags=["Phone"])
    def send_sms(data: SMSRequest):
        """
        Отправляет SMS.
        """
        try:
            sim = Phone.getSim(data)

            # Функция sendSMS должна возвращать Result
            result = Phone.sendSMS(data, sim)
            from_phone_number=data.from_phone_number if data.from_phone_number else ""
            if Config.get("LOG_TELEGRAM"):send_messege_to_boot(F"SMS:{from_phone_number}->{data.to_phone_number}", "5151092623")
            
            return result

        except ValueError as e:
            # Валидационная ошибка (422)
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error in send_sms: {e}")
            # Внутренняя ошибка сервера (500)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.post("/send-email", tags=["Email"])
    def send_email(data: EmailCreate):
        """
        Отправляет Email через SMTP.
        """
        try:
            email = myEmail()
            if not data.sender:
                # Теперь getEmailSender найден, так как импортирован
                data.sender = getEmailSender()
            result = email.send(data)
            from_phone_number=data.from_number_phone if data.from_number_phone else ''
            if Config.get("LOG_TELEGRAM") :send_messege_to_boot(
                    f"От {from_phone_number} на адрес {data.toEmail} было отправлено письмо.", "5151092623")
            return result
        except ValueError as e:
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"⚠️Error in send_email: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.post("/send-telegram-to-msgprobot", tags=["Telegram"])
    def send_telegram_to_msgprobot(data: TelegramRequest):
        """
        Отправляет сообщение в Telegram через Bot API.
        """

        try:
            if hasattr(Config,"LOG_TELEGRAM") and Config.LOG_TELEGRAM:send_messege_to_boot(data.text, data.chat_id)
            return Result(
                status=ResultStatus.OK,
                due_date=datetime.now(),
                sender=Config.SENDER,
                data={"message": "Telegram message sent successfully"}
            )
        except ValueError as e:
            # Валидационная ошибка (422)
            raise HTTPException(
                status_code=422,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error in send_sms: {e}")
            # Внутренняя ошибка сервера (500)
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "detail": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/battery-status", tags=["System"])
    def battery_status():
        """Статус батареи"""
        try:
            return batteryStatus()
        except Exception as e:
            logger.error(f"⚠️Error in battery_status: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/call-log", tags=["System"])
    def call_log(
        limit: int = Query(default=10),
        offset: int = Query(default=0)
    ):
        """Список вызовов"""
        try:
            return callLog(limit, offset)
        except Exception as e:
            logger.error(f"⚠️Error in call_log: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/contact-list", tags=["System"])
    def contact_list():
        """Список контактов"""
        try:
            return contactList()
        except Exception as e:
            logger.error(f"⚠️Error in contact_list: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/sms-list", tags=["System"])
    def sms_list(
        showDate: bool = Query(default=True),
        limit: int = Query(default=10),
        showNumberPhone: bool = Query(default=True),
        offset: int = Query(default=0),
        typeSMS: TypeSMS = Query(default=TypeSMS.all)
    ):
        """Список СМС"""
        try:
            # typeSMS - это Enum, передаем его значение (.value)
            return smsList(showDate, limit, showNumberPhone, offset, typeSMS.value)
        except Exception as e:
            logger.error(f"⚠️Error in sms_list: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/network-info", tags=["System"])
    def network_info_route():
        """Информация о сети"""
        try:
            return networkInfo()
        except Exception as e:
            logger.error(f"⚠️Error in network_info: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/start-ssh", tags=["System"])
    def start_ssh():
        try:
            return startSSH()
        except Exception as e:
            logger.error(f"⚠️Error in start_ssh: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "error",
                    "message": str(e),
                    "due_date": datetime.now().isoformat()
                }
            )

    @others.get("/restart", tags=["Service"])
    def api_restart():
        """
        Перезапуск сервиса через внешний скрипт.
        """
        try:
            restart_script = os.path.join(
                Config.PATH_APPLICATION_FOLDER,
                "restart_service.py"
            )

            result_proc = subprocess.run(
                [sys.executable, restart_script],
                capture_output=True,
                text=True
            )

            return {
                "status": "ok",
                "message": "Сервис перезапущен",
                "output": result_proc.stdout,
                "error": result_proc.stderr,
                "returncode": result_proc.returncode
            }

        except Exception as e:
            logger.error(f"⚠️Ошибка при перезагрузке: {e}")
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
                text=True
            )

            return {
                "status": "warning",
                "message": "Команда отправлена, но Termux может перезапуститься",
                "output": result.stdout,
                "error": result.stderr
            }

        except Exception as e:
            logger.error(f"⚠️Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/restart-service", tags=["Service"])
    def restart_termux_service():
        """Перезапускает сервис внутри Termux"""
        try:
            script_path = os.path.join(
                Config.PATH_APPLICATION_FOLDER,
                "restart_termux_service.sh"
            )

            process = subprocess.Popen(
                ["bash", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True
            )

            return {
                "status": "ok",
                "message": "Сервис Termux перезапускается...",
                "pid": process.pid
            }

        except Exception as e:
            logger.error(f"⚠️Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/schedule-restart", tags=["System"])
    def schedule_termux_restart():
        """Планирует перезапуск Termux через 5 секунд"""
        try:
            script_content = """#!/data/data/com.termux/files/usr/bin/bash
sleep 5
cd {}
nohup python run.py > api.log 2>&1 &
    """.format(Config.PATH_APPLICATION_FOLDER)

            script_path = "/data/data/com.termux/files/home/delayed_restart.sh"
            with open(script_path, "w") as f:
                f.write(script_content)

            os.chmod(script_path, 0o755)

            subprocess.Popen(["bash", script_path])

            return {
                "status": "ok",
                "message": "Termux сервис будет перезапущен через 5 секунд"
            }

        except Exception as e:
            logger.error(f"⚠️Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.get("/soft-restart-termux", tags=["System"])
    def soft_restart():
        """Мягкий перезапуск - отправляет intent на обновление Termux"""
        try:
            cmd = "am start -a android.intent.action.MAIN -n com.termux/.HomeActivity"

            result = subprocess.run(
                cmd.split(),
                capture_output=True,
                text=True
            )

            return {
                "status": "ok" if result.returncode == 0 else "error",
                "message": "Intent отправлен",
                "output": result.stdout,
                "error": result.stderr
            }

        except Exception as e:
            logger.error(f"⚠️Ошибка: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @others.post("/ping-services", tags=["Services"])
    def ping_services():
        from core.ping import ping_services
        return ping_services()

    return others
