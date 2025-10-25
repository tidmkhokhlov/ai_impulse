import os
import asyncio
import requests
import base64
import tempfile

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile

# ====== Настройки ======
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/analyze/")
REPORT_ENDPOINT = f"{API_URL}report"  # endpoint для .xlsx

if not BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN not provided. Set it in environment variables.")

# ====== Создание бота ======
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ====== Хендлеры ======

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Отправь ссылку на пост или текст публикации — я проверю её и пришлю отчёт (.xlsx)."
    )

@router.message()
async def handle_text(message: types.Message):
    text = message.text.strip()
    if not text:
        await message.answer("⚠️ Сообщение пустое — отправь текст публикации.")
        return

    try:
        # Запрос на API для анализа и получения XLSX
        resp = requests.post(REPORT_ENDPOINT, json={"text": text})
        if resp.status_code == 200:
            data = resp.json()
            incidents = data.get("incidents", [])
            xlsx_base64 = data.get("xlsx_base64")

            if xlsx_base64:
                # Декодируем base64
                xlsx_bytes = base64.b64decode(xlsx_base64)

                # Сохраняем во временный файл
                with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                    tmp_file.write(xlsx_bytes)
                    tmp_file_path = tmp_file.name

                # Отправляем файл
                await message.answer(f"✅ Найдено {len(incidents)} возможных нарушений. Отчёт ниже:")
                await message.answer_document(FSInputFile(tmp_file_path, filename="report.xlsx"))

            else:
                await message.answer(f"✅ Найдено {len(incidents)} нарушений, но отчёт недоступен.")
        else:
            await message.answer(f"⚠️ Ошибка при анализе: {resp.status_code}")

    except Exception as e:
        await message.answer(f"❌ Ошибка связи с API: {e}")

# ====== Точка входа ======
async def main():
    print("🤖 Бот запущен и готов принимать сообщения.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
