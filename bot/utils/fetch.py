import re
import os
from telethon import TelegramClient
from dotenv import load_dotenv

load_dotenv()

# Получаем ключи из переменных окружения
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")


async def fetch(channel_url: str):
    """
    Получает текст Telegram-поста по ссылке формата https://t.me/<channel>/<post_id>
    Возвращает текст публикации или сам текст, если это не ссылка.
    """

    # Проверяем, является ли входная строка ссылкой на Telegram
    pattern = r"https?://t\.me/([\w_]+)/(\d+)"
    match = re.match(pattern, channel_url)
    if not match:
        return channel_url  # если это не ссылка — вернуть сам текст

    channel, post_id = match.groups()

    # Проверяем, заданы ли ключи
    if not API_ID or not API_HASH:
        return "⚠️ Ошибка: TG_API_ID или TG_API_HASH не заданы в окружении."

    try:
        # Открываем сессию клиента
        async with TelegramClient("session_ai_impulse", API_ID, API_HASH) as client:
            message = await client.get_messages(channel, ids=int(post_id))

            if not message:
                return "⚠️ Не удалось получить сообщение (возможно, канал приватный или пост удалён)."

            text = message.text or ""
            if message.media and getattr(message, "caption", None):
                text += f"\n\n{message.caption}"

            return text.strip()

    except Exception as e:
        return f"⚠️ Ошибка при получении поста: {e}"
