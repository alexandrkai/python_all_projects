


import asyncio
import html
import os
from datetime import datetime

from aiogram import BaseMiddleware, Bot, Dispatcher, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import (
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    TelegramObject,
)
from aiohttp_socks import ProxyConnector
from sqlalchemy import BigInteger, Boolean, DateTime, String, func, select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# =========================================================
# КОНФИГ
# =========================================================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8524403686:AAEjbYgXaHP70PHTifQDxA9em4nJkPPHfcU")
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://kai:291297@192.168.1.222:5432/botdb",
)

# Адрес локального SOCKS5-прокси, поднятого через SSH-туннель.
# Если туннель не нужен, поставьте PROXY_URL = None.
# для Docker
# PROXY_URL = "socks5://host.docker.internal:1080"
# для WSL
# Узнайте IP Windows-хоста из WSL: cat /etc/resolv.conf | grep nameserver
# PROXY_URL = "socks5://10.255.255.254:1080"
PROXY_URL = "socks5://127.0.0.1:1080"

# ID администраторов через запятую. Узнать свой можно командой /me.
ADMIN_IDS: set[int] = {
    int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()
}


# =========================================================
# МОДЕЛИ
# =========================================================
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    chat_id: Mapped[int] = mapped_column(BigInteger)

    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(32), nullable=True)

    is_subscribed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# =========================================================
# БД
# =========================================================
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# =========================================================
# MIDDLEWARE
# =========================================================
class DbSessionMiddleware(BaseMiddleware):
    """Кладёт AsyncSession в data, чтобы хендлеры могли её использовать."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    async def __call__(self, handler, event: TelegramObject, data: dict):
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)


# =========================================================
# ХЕЛПЕРЫ
# =========================================================
async def get_or_create_user(session: AsyncSession, message: Message) -> User:
    """Возвращает пользователя из БД или создаёт нового."""
    tg_id = message.from_user.id

    result = await session.execute(select(User).where(User.telegram_id == tg_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=tg_id,
            chat_id=message.chat.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
        )
        session.add(user)
        await session.flush()
    else:
        user.chat_id = message.chat.id
        user.username = message.from_user.username
        user.first_name = message.from_user.first_name
        user.last_name = message.from_user.last_name

    return user


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def main_menu(
    has_phone: bool = False,
    is_subscribed: bool = False,
) -> ReplyKeyboardMarkup:
    """Строит клавиатуру в зависимости от состояния пользователя."""
    rows: list[list[KeyboardButton]] = []

    if not has_phone:
        rows.append([
            KeyboardButton(text="📱 Поделиться контактом", request_contact=True)
        ])

    if has_phone:
        if is_subscribed:
            rows.append([KeyboardButton(text="❌ Отписаться")])
        else:
            rows.append([KeyboardButton(text="✅ Подписаться")])

    if not rows:
        rows.append([
            KeyboardButton(text="📱 Поделиться контактом", request_contact=True)
        ])

    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def build_menu(user: User) -> ReplyKeyboardMarkup:
    return main_menu(
        has_phone=bool(user.phone_number),
        is_subscribed=bool(user.is_subscribed),
    )


def format_profile(user: User) -> str:
    """HTML-представление профиля пользователя."""
    phone = html.escape(user.phone_number) if user.phone_number else "— не указан —"
    subscribed = "✅ да" if user.is_subscribed else "❌ нет"

    created = (
        user.created_at.strftime("%d.%m.%Y %H:%M")
        if user.created_at
        else "—"
    )

    name_parts = [
        html.escape(user.first_name or ""),
        html.escape(user.last_name or ""),
    ]
    full_name = " ".join(p for p in name_parts if p) or "—"
    username = f"@{html.escape(user.username)}" if user.username else "—"

    return (
        "👤 <b>Ваш профиль</b>\n\n"
        f"<b>Имя:</b> {full_name}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>Telegram ID:</b> <code>{user.telegram_id}</code>\n"
        f"<b>Chat ID:</b> <code>{user.chat_id}</code>\n"
        f"<b>Телефон:</b> {phone}\n"
        f"<b>Подписка:</b> {subscribed}\n"
        f"<b>В системе с:</b> {created}"
    )


def format_user_row(idx: int, user: User) -> str:
    """Строка пользователя для админского списка."""
    name = html.escape(user.first_name or "") or "—"
    username = f"@{html.escape(user.username)}" if user.username else "—"
    phone = html.escape(user.phone_number) if user.phone_number else "—"
    sub = "✅" if user.is_subscribed else "❌"

    return (
        f"{idx}. <b>{name}</b> ({username}) {sub}\n"
        f"   ID: <code>{user.telegram_id}</code>\n"
        f"   📱 {phone}"
    )


# =========================================================
# ХЕНДЛЕРЫ
# =========================================================
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message)
    await session.commit()

    await message.answer(
        "Привет! Выберите действие 👇\n\n"
        "Доступные команды:\n"
        "/me — ваш профиль\n"
        "/help — справка",
        reply_markup=build_menu(user),
    )


@dp.message(Command("help"))
async def cmd_help(message: Message) -> None:
    text = (
        "📖 <b>Справка</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — главное меню\n"
        "/me — показать ваш профиль\n"
        "/help — эта справка\n\n"
        "<b>Кнопки меню:</b>\n"
        "📱 Поделиться контактом — сохранить ваш номер телефона\n"
        "✅ Подписаться — оформить подписку (нужен номер)\n"
        "❌ Отписаться — отменить подписку\n"
    )

    if is_admin(message.from_user.id):
        text += "\n<b>Админ-команды:</b>\n/users — список всех пользователей\n"

    await message.answer(text, parse_mode="HTML")


@dp.message(Command("me"))
async def cmd_me(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message)
    await session.commit()

    await message.answer(
        format_profile(user),
        parse_mode="HTML",
        reply_markup=build_menu(user),
    )


@dp.message(Command("users"))
async def cmd_users(message: Message, session: AsyncSession) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return

    result = await session.execute(select(User).order_by(User.id))
    users = result.scalars().all()

    if not users:
        await message.answer("В базе пока нет пользователей.")
        return

    total = len(users)
    subscribed = sum(1 for u in users if u.is_subscribed)
    with_phone = sum(1 for u in users if u.phone_number)

    header = (
        f"👥 <b>Пользователи</b> ({total})\n"
        f"Подписаны: {subscribed}\n"
        f"С телефоном: {with_phone}\n\n"
    )

    lines: list[str] = []
    current = header

    for idx, user in enumerate(users, start=1):
        row = format_user_row(idx, user) + "\n\n"
        if len(current) + len(row) > 3500:
            lines.append(current)
            current = ""
        current += row

    if current:
        lines.append(current)

    for chunk in lines:
        await message.answer(chunk, parse_mode="HTML")


@dp.message(F.contact)
async def contact_handler(message: Message, session: AsyncSession) -> None:
    contact = message.contact

    if contact.user_id and contact.user_id != message.from_user.id:
        user = await get_or_create_user(session, message)
        await session.commit()
        await message.answer(
            "Пожалуйста, поделитесь именно своим контактом.",
            reply_markup=build_menu(user),
        )
        return

    user = await get_or_create_user(session, message)
    user.phone_number = contact.phone_number
    await session.commit()

    await message.answer(
        f"Номер {html.escape(contact.phone_number)} сохранён ✅\n"
        "Теперь вы можете подписаться.",
        reply_markup=build_menu(user),
    )


@dp.message(F.text == "✅ Подписаться")
async def subscribe_handler(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message)

    if not user.phone_number:
        await session.commit()
        await message.answer(
            "Чтобы подписаться, сначала поделитесь номером телефона 📱",
            reply_markup=build_menu(user),
        )
        return

    if user.is_subscribed:
        await session.commit()
        await message.answer("Вы уже подписаны ✅", reply_markup=build_menu(user))
        return

    user.is_subscribed = True
    await session.commit()

    await message.answer("Вы подписались ✅", reply_markup=build_menu(user))


@dp.message(F.text == "❌ Отписаться")
async def unsubscribe_handler(message: Message, session: AsyncSession) -> None:
    user = await get_or_create_user(session, message)

    if not user.is_subscribed:
        await session.commit()
        await message.answer("Вы и так не подписаны.", reply_markup=build_menu(user))
        return

    user.is_subscribed = False
    await session.commit()

    await message.answer("Вы отписались ❌", reply_markup=build_menu(user))


# =========================================================
# СОЗДАНИЕ БОТА С SOCKS5-ПРОКСИ
# =========================================================

def create_bot() -> Bot:
    """Создаёт Bot с SOCKS5-прокси, если PROXY_URL задан."""
    if not PROXY_URL:
        print("ℹ️  PROXY_URL не задан — подключаемся напрямую.")
        return Bot(token=BOT_TOKEN)

    print(f"🔌 Используем прокси: {PROXY_URL}")
    session = AiohttpSession(proxy=PROXY_URL)
    return Bot(token=BOT_TOKEN, session=session)

# =========================================================
# ЗАПУСК
# =========================================================
async def main() -> None:
    print("🚀 Запуск бота...")
    await init_db()
    print("✅ БД инициализирована.")

    bot = create_bot()

    # Проверка соединения — сразу видим, работает ли прокси
    try:
        me = await bot.get_me()
        print(f"✅ Подключено к Telegram: @{me.username} (id={me.id})")
    except Exception as e:
        print(f"❌ Не удалось подключиться к Telegram: {e}")
        print("   Проверьте, что SSH-туннель запущен и PROXY_URL корректен.")
        await bot.session.close()
        return

    dp.update.middleware(DbSessionMiddleware(SessionLocal))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        print("👋 Бот остановлен.")


if __name__ == "__main__":
    asyncio.run(main())