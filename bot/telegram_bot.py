import os
import asyncio
import base64
import tempfile
import httpx
import re

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

from app.services.fetch import fetch

# ====== Настройки ======
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = os.getenv("http://127.0.0.1:8000/api/v1/analyze/")
REPORT_ENDPOINT = f"{API_URL}report"

if not BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN not provided.")

# ====== Бот ======
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ====== Вспомогательная функция MarkdownV2 ======
def escape_markdown(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2 для Telegram."""
    escape_chars = r'_*\[\]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)


# ====== Хэндлеры ======
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Отправь текст публикации или ссылку на пост — я проверю её и пришлю отчёт (.xlsx)."
    )


@router.message()
async def handle_text(message: types.Message):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Сообщение пустое — отправь текст публикации.")
        return

    # Если ссылка на пост, достаем текст
    if text.startswith("https://t.me/"):
        text = await fetch(text)
        if not text:
            await message.answer("⚠️ Не удалось получить текст из ссылки.")
            return

    try:
        # Асинхронный запрос к API
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(REPORT_ENDPOINT, json={"text": text})
            resp.raise_for_status()
            data = resp.json()

        incidents = data.get("incidents", [])
        total_risk = data.get("total_risk", 0)
        risk_level = data.get("risk_level", "low")
        xlsx_base64 = data.get("xlsx_base64")
        recommendations = escape_markdown(data.get("recommendations", ""))

        # Сообщение о нарушениях
        await message.answer(
            f"✅ Найдено {len(incidents)} нарушений.\n"
            f"Суммарный риск: {total_risk}\n"
            f"Уровень риска: {risk_level}"
        )

        # Отправка рекомендаций GigaChat
        if recommendations:
            await message.answer(f"💡 Рекомендации по исправлению нарушений:\n{recommendations}",
                                 parse_mode="MarkdownV2")

        # Отправка XLSX
        if xlsx_base64:
            xlsx_bytes = base64.b64decode(xlsx_base64)
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(xlsx_bytes)
                tmp_file_path = tmp_file.name

            await message.answer_document(FSInputFile(tmp_file_path, filename="report.xlsx"))

            # Удаляем временный файл
            os.remove(tmp_file_path)

    except Exception as e:
        await message.answer(f"❌ Ошибка при связи с API: {e}")


# ====== Точка входа ======
async def main():
    print("🤖 Бот запущен и готов принимать сообщения.")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
