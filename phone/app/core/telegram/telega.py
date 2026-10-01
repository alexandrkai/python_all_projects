
import requests
from core.telegram.config import DEFAULT_CHAT_ID, TOKEN
from log.log import get_logger

logger = get_logger(__name__)

# для отправки сообщения кому-то надо знать ваш общий с чат-ботом msgpro.ru chat_id.
# ЭТИ МЕТОДЫ НАПРЯМУЮ ИСПОЛЬЗОВАТЬ НЕЛЬЗЯ!!! ОНИ БУДУТ ПЕРЕОПРЕДЕЛЕНЫ В config.py


def __send_message_to_telegram(message, chat_id, port_ssh_tunnel) -> dict:
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": message}

        # Настройка прокси (SOCKS5 через localhost:1080) для этого должен быть запущен ssh-tunnel.sh
        # читвй app\libs\telegram\readme.md
        # ssh -D 9090 -N -f kai@89.125.188.172
        # proxies = {
        #     "http": f"socks5://127.0.0.1:{port_ssh_tunnel}",
        #     "https": f"socks5://127.0.0.1:{port_ssh_tunnel}"
        # }
        proxies = {
            "http": f"socks5h://127.0.0.1:{port_ssh_tunnel}",
            "https": f"socks5h://127.0.0.1:{port_ssh_tunnel}"
        }

        response = requests.post(url, json=payload, proxies=proxies)
        return response.json()
    except Exception as e:  # noqa: BLE001
        logger.error('❌Проблема с отправкой лога в Телеграмм'+str(e))
        return None
