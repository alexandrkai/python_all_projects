# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/email.py
from ._base import BaseModel,Field,EmailStr,Optional,model_validator
from log.log import logger

class EmailSender(BaseModel):
    SMTP_SERVER:str #"smtp.yandex.ru",
    SMTP_PORT:int=Field(default= 587)
    SMTP_USERNAME:EmailStr #"kaibytele2@yandex.ru",
    SMTP_PASSWORD:str #"qsctxqnmhjxlwkgq"

class EmailCreate(BaseModel):
    toEmail:EmailStr
    subject:str
    body:Optional[str]=None
    htmlBody:Optional[str]=None
    sender:Optional[EmailSender]=None
    from_number_phone:Optional[str]=None
    
    @model_validator(mode="after")
    def check_body_htmlBode(self):
        if not self.body and not self.htmlBody:
            error_message= "⚠️У email один из параметров(body или htmlBody) должен быть заполнен!"
            logger.error(error_message)
            raise ValueError(error_message)
        return self
    

# class EmailRequest(BaseModel):
#     to_email: EmailStr
#     subject: str
#     message: str
#     # Для простоты передаем логин/пароль в запросе, 
#     # но в продакшене лучше использовать переменные окружения!
#     sender_email: EmailStr 
#     sender_password: str
#     smtp_server: str = "smtp.gmail.com" 
#     smtp_port: int = 465