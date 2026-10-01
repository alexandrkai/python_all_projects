import json
import os

# parent directory
from pathlib import Path

from config import TOKEN
from telegram import KeyboardButton, ReplyKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Получаем путь к текущему файлу и берём родительскую директорию
current_path = Path(__file__).resolve()
root_dir = current_path.parent.parent.parent
data_dir = os.path.join(str(root_dir), "data")
chat_ids_json_file = os.path.join(
    str(root_dir), "data", "msgprobot_chat_ids.json")

# Команда /start


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой бот. Наш chat_id {}".format(update.message.chat.id))
    # Создаем кнопку с запросом контакта
    contact_button = KeyboardButton(
        text="📱 Отправить номер телефона", request_contact=True)
    # Создаем клавиатуру с этой кнопкой
    reply_markup = ReplyKeyboardMarkup(
        [[contact_button]], resize_keyboard=True)

    # Отправляем сообщение с клавиатурой
    await update.message.reply_text(
        "Нажмите на кнопку ниже, чтобы поделиться своим номером телефона:",
        reply_markup=reply_markup
    )

# Обработчик полученного контакта


async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Получаем объект контакта из сообщения
    contact = update.message.contact

    # Извлекаем номер телефона, имя и фамилию
    phone_number = contact.phone_number
    first_name = contact.first_name
    last_name = contact.last_name
    chat_id = update.message.chat_id
    # Формируем ответное сообщение
    response_text = (
        f"Спасибо, {first_name}!\n"
        f"Ваш номер: {phone_number}\n"
        f"Наш номер: {chat_id}\n"
    )
    if last_name:
        response_text += f"Фамилия: {last_name}"
    change = False
    # Отправляем подтверждение пользователю
    await update.message.reply_text(response_text)
    with open(chat_ids_json_file, "r") as file:
        data = json.load(file)
        if phone_number not in data:
            data[phone_number] = chat_id
            change = True
    if change == True:
        with open(chat_ids_json_file, "w") as file:
            json.dump(data, file)


def main():
    # Создаем приложение
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    # Обрабатываем все сообщения, которые содержат контакт
    app.add_handler(MessageHandler(filters.CONTACT, contact_handler))

    # Запускаем бота
    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
