# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/core/email.py
import random
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config.config import (
    Config,
    get_full_error_message,
    send_message_to_telegram,
)
from log.log import get_logger
from schemas import EmailRequest, EmailSender, ResultStatus

logger = get_logger(__name__)


def getEmailSender() -> EmailSender | None:
    """
    Получение случайного email-отправителя из конфигурации.
    Возвращает объект EmailSender или None, если список пуст.
    При критических ошибках отправляет алерт в Telegram.
    """
    email_senders = Config.get("EMAIL_SENDERS")
    if not email_senders:
        err = RuntimeError("Список EMAIL_SENDERS пуст или не настроен в конфигурации")
        full_msg = get_full_error_message(
            e=err,
            error_message="Отсутствуют почтовые серверы в конфигурации",
            prefix="EMAIL_CONFIG",
        )
        logger.critical(full_msg)
        send_message_to_telegram(full_msg)
        return None

    chosen = random.choice(email_senders)

    if isinstance(chosen, EmailSender):
        return chosen

    try:
        return EmailSender.model_validate(chosen)
    except Exception as e:
        full_msg = get_full_error_message(
            e=e,
            error_message="Ошибка валидации EmailSender из senders.json / Redis",
            prefix="EMAIL_VALIDATION",
        )
        logger.critical(full_msg, exc_info=True)
        send_message_to_telegram(full_msg)
        return None

class myEmail:
    @classmethod
    def send(cls, email: EmailRequest, sender: EmailSender | None = None) -> dict:
        """
        Отправка email-уведомления на основе EmailRequest.
        Если sender не передан, выбирается случайный из конфигурации.
        """
        active_sender = sender or getEmailSender()
        if not active_sender or not getattr(active_sender, "settings", None):
            err = RuntimeError("SMTP credentials не настроены или отсутствуют")
            full_msg = get_full_error_message(
                e=err,
                error_message="Отсутствуют настройки почтового отправителя",
                prefix="EMAIL_INIT",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise err

        smtp_settings = active_sender.settings
        from_email = smtp_settings.SMTP_USERNAME

        # Формируем тело письма
        full_text_body = email.message.body
        if email.message.footer:
            full_text_body = f"{full_text_body}\n\n---\n{email.message.footer}"

        # Собираем MIME-сообщение
        msg = MIMEMultipart("alternative")
        msg["Subject"] = email.message.title
        msg["From"] = from_email
        msg["To"] = email.to_email
        msg.attach(MIMEText(full_text_body, "plain", "utf-8"))

        # Отправка через SMTP
        try:
            with smtplib.SMTP(smtp_settings.SMTP_SERVER, smtp_settings.SMTP_PORT) as server:
                server.starttls()
                server.login(
                    smtp_settings.SMTP_USERNAME,
                    smtp_settings.SMTP_PASSWORD.get_secret_value(),
                )
                server.send_message(msg)

            logger.info(f"✅ Email успешно отправлен на {email.to_email}")
            send_message_to_telegram(f"✅ EMAIL: {from_email} -> {email.to_email}")

            sender_name = getattr(Config.SENDER, "name", "SYSTEM")
            return {
                "status": ResultStatus.OK,
                "due_date": datetime.now(),
                "sender": sender_name,
                "data": {
                    "message": "Email успешно отправлен",
                    "to": email.to_email,
                    "title": email.message.title,
                    "sender_email": from_email,
                },
            }

        except smtplib.SMTPException as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Ошибка SMTP при отправке на {email.to_email}",
                prefix="EMAIL_SMTP",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise RuntimeError(f"Не удалось отправить письмо: {e}") from e

        except Exception as e:
            full_msg = get_full_error_message(
                e=e,
                error_message=f"Неожиданная ошибка при отправке на {email.to_email}",
                prefix="EMAIL_UNEXPECTED",
            )
            logger.error(full_msg)
            send_message_to_telegram(full_msg)
            raise RuntimeError(f"Внутренняя ошибка при отправке email: {e}") from e