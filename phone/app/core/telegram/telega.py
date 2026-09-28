
import requests
from core.telegram.config import TOKEN
from log.log import get_logger

logger = get_logger(__name__)


def send_messege_to_boot(text, CHAT_ID="5151092623"):
    """ ОТправка сообщения через телеграм бот

    Args:
        text (_type_): _description_
        CHAT_ID (_type_): _description_
    """
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text}

        # Настройка прокси (SOCKS5 через localhost:1080) для этого должен быть запущен ssh-tunnel.sh
        # читвй app\libs\telegram\readme.md
        # ssh -D 9090 -N -f kai@89.125.188.172
        proxies = {
            "http": "socks5://127.0.0.1:9090",
            "https": "socks5://127.0.0.1:9090"
        }

        response = requests.post(url, json=payload, proxies=proxies)
        print(response.json())
    except Exception as e:  # noqa: BLE001
        logger.error('Проблема с отправкой лога в Телеграмм'+str(e))
