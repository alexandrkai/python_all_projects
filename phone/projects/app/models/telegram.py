# D:/myprogramms/Python/Phones/PROJECT/PHONE/app/models/telegram.py
from ._base import BaseModel

class TelegramRequest(BaseModel):
    # bot_token: str
    chat_id: str
    text: str