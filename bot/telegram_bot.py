import os
import asyncio
import base64
import tempfile
import httpx

from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import CommandStart
from aiogram.types import FSInputFile
from bot.utils.escape_markdown import escape_markdown

from app.services.fetch import fetch
from app.services.gigachat_service import generate_recommendation

# ====== Настройки ======
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/api/v1/analyze/")
REPORT_ENDPOINT = f"{API_URL}report"

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

    if text.startswith("https://t.me/"):
        text = await fetch(text)
        if not text:
            await message.answer("⚠️ Не удалось получить текст из ссылки.")
            return

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(REPORT_ENDPOINT, json={"text": text})
            if resp.status_code != 200:
                await message.answer(f"⚠️ Ошибка при анализе: {resp.status_code} {resp.text}")
                return
            data = resp.json()

        incidents = data.get("incidents", [])
        total_risk = data.get("total_risk", 0)
        risk_level = data.get("risk_level", "low")
        xlsx_base64 = data.get("xlsx_base64")

        # 1. Сообщение о нарушениях с категориями
        category_map = {
            "general": "🟢",
            "privacy": "🔴",
            "finance": "🟡",
            "marketing": "🔵",
            "hidden": "🟠"
        }

        if incidents:
            category_messages = []
            for cat, emoji in category_map.items():
                cat_incidents = [i['message'] for i in incidents if i.get('category') == cat]
                if cat_incidents:
                    category_messages.append(f"{emoji} *{cat.capitalize()}*:\n- " + "\n- ".join(cat_incidents))

            await message.answer(
                f"✅ Найдено {len(incidents)} возможных нарушений.\n"
                f"Суммарный риск: {total_risk}\n"
                f"Уровень риска: {risk_level}\n\n" + "\n\n".join(category_messages),
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"✅ Нарушений не найдено. Суммарный риск: {total_risk}, уровень: {risk_level}")

        # 2. Генерация рекомендаций через GigaChat
        if incidents:
            try:
                recs_ai = await generate_recommendation(text, incidents)
                safe_recs = escape_markdown(recs_ai)
                await message.answer(f"💡 Рекомендации по исправлению нарушений:\n{safe_recs}", parse_mode="MarkdownV2")
            except Exception as e:
                await message.answer(f"⚠️ Не удалось получить рекомендации от GigaChat: {e}")

        # 3. Отправка XLSX
        if xlsx_base64:
            xlsx_bytes = base64.b64decode(xlsx_base64)
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(xlsx_bytes)
                tmp_file_path = tmp_file.name

            await message.answer_document(FSInputFile(tmp_file_path, filename="report.xlsx"))
            os.remove(tmp_file_path)

    except Exception as e:
        await message.answer(f"❌ Ошибка связи с API: {e}")

# ====== Точка входа ======
async def main():
    print("🤖 Бот запущен и готов принимать сообщения.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
