# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/email.py
import random
import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from log.log import get_logger
from schemas import EmailCreate, EmailSender, Result, ResultStatus

from core.telegram.telega import send_messege_to_boot

logger = get_logger(__name__)

def getEmailSender() -> Optional[EmailSender]:
    """
    Получение случайного отправителя из файла senders.json.
    Возвращает объект EmailSender или None в случае ошибки.
    """
    from config.config import Config
    email_senders=Config.get('EMAIL_SENDERS')
    if email_senders:
        email_sender=random.choice(email_senders)
        SMTP_SERVER=email_sender['SMTP_SERVER']
        SMTP_PORT=email_sender['SMTP_PORT']
        SMTP_USERNAME=email_sender['SMTP_USERNAME']
        SMTP_PASSWORD=email_sender['SMTP_PASSWORD']
        if SMTP_SERVER and SMTP_PORT and SMTP_USERNAME and SMTP_PASSWORD:
            return EmailSender(
                SMTP_SERVER=SMTP_SERVER,
                SMTP_PORT=SMTP_PORT,
                SMTP_USERNAME=SMTP_USERNAME,
                SMTP_PASSWORD=SMTP_PASSWORD
            )
    # try:
    #     path_to_senders = os.path.join(
    #         Config.PATH_APPLICATION_FOLDER, "data", "senders.json")

    #     if not os.path.exists(path_to_senders):
    #         error_msg = f"⚠️Файл отправителей не найден: {path_to_senders}"
    #         logger.error(error_msg)
    #         raise Exception(error_msg)

    #     with open(path_to_senders, "r", encoding="utf-8") as file:
    #         context = file.read()
    #         data = json.loads(context)

    #         if "email" not in data or not data["email"]:
    #             error_msg = "⚠️В файле senders.json отсутствует ключ 'email' или список пуст"
    #             logger.error(error_msg)
    #             raise Exception(error_msg)

    #         emaiSenderDict = random.choice(data["email"])

    #         return EmailSender(
    #             SMTP_SERVER=emaiSenderDict.get("SMTP_SERVER"),
    #             SMTP_PORT=emaiSenderDict.get("SMTP_PORT"),
    #             SMTP_USERNAME=emaiSenderDict.get("SMTP_USERNAME"),
    #             SMTP_PASSWORD=emaiSenderDict.get("SMTP_PASSWORD")
    #         )

    # except Exception as e:
    #     mess = f"⚠️Ошибка при чтении отправителей: {str(e)}"
    #     logger.error(mess)
    #     raise


class myEmail:
    EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def send(self, email: EmailCreate) -> dict:
        """
        Отправка email уведомления.
        Возвращает объект Result.
        """
        from_phone_number=email.from_number_phone if email.from_number_phone else ""
        # Проверка формата email
        if not self.EMAIL_PATTERN.match(email.toEmail):
            error_msg = f"⚠️Неправильный формат email адреса {email.toEmail}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Проверка учетных данных (если sender не передан, getEmailSender вернет None, но роутер это должен обработать или мы здесь)
        # В данном случае проверяем поля внутри объекта email.sender
        if not email.sender or not email.sender.SMTP_USERNAME or not email.sender.SMTP_PASSWORD:
            error_msg = "⚠️SMTP credentials не настроены или отсутствуют"
            logger.error(error_msg)
            raise Exception(error_msg)

        fromEmail = email.sender.SMTP_USERNAME

        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.subject
        msg["From"] = fromEmail
        msg["To"] = email.toEmail

        # Текстовая версия
        if email.body:
            part1 = MIMEText(email.body, "plain")
            msg.attach(part1)

        # HTML версия, если есть
        if email.htmlBody:
            part2 = MIMEText(email.htmlBody, "html")
            msg.attach(part2)

        try:
            # Отправка
            with smtplib.SMTP(email.sender.SMTP_SERVER, email.sender.SMTP_PORT) as server:
                server.starttls()
                server.login(email.sender.SMTP_USERNAME,
                             email.sender.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info(f"Email успешно отправлен на {email.toEmail}")
            from config.config import Config
            # Формируем успешный результат
            return {
                "status": ResultStatus.OK,
                "due_date": datetime.now(),
                "sender": Config.SENDER.name,
                "data": {
                    "message": "Email отправлен",
                    "to": email.toEmail,
                    "sender_email": fromEmail
                }
            }

        except smtplib.SMTPException as e:
            # Специфичная ошибка SMTP
            logger.error(f"⚠️Ошибка SMTP при отправке на {email.toEmail}: {e}")
            raise Exception(f"Не удалось отправить письмо: {str(e)}")

        except Exception as e:
            # Любая другая ошибка
            logger.error(f"⚠️Неожиданная ошибка при отправке email: {e}")
            raise Exception(
                f"Внутренняя ошибка сервера при отправке email: {str(e)}")
