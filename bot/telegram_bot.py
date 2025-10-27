import os
import asyncio
import base64
import tempfile
import httpx
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton

from bot.utils.fetch import fetch
load_dotenv()


# ====== Настройки ======
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/api/v1/analyze/"
REPORT_ENDPOINT = f"{API_URL}report"

if not BOT_TOKEN:
    raise ValueError("TG_BOT_TOKEN not provided.")

# ====== Бот ======
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)


# ====== Клавиатуры ======
def get_main_keyboard():
    """Основная клавиатура с командами"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Анализ текста"), KeyboardButton(text="🔗 Анализ ссылки")],
            [KeyboardButton(text="❓ Помощь")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )


def get_back_to_main_keyboard():
    """Кнопка возврата в главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="⬅️ Главное меню")]],
        resize_keyboard=True
    )


# ====== Хэндлеры ======
@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    welcome_text = """
🎉 Добро пожаловать в AI Impulse Analyzer!

🤖 Я помогу анализировать контент на нарушения:
• Рекламные нарушения
• Сбор персональных данных  
• Финансовые махинации
• Мошеннические схемы

👇 Выберите действие или отправьте текст для анализа!
    """

    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def cmd_help(message: types.Message):
    """Помощь по использованию бота"""
    help_text = """
📖 Как использовать:

1. 📊 Анализ текста - проверьте текст публикации
2. 🔗 Анализ ссылки - проверьте пост по ссылке
3. Или просто отправьте текст/ссылку

Бот проверит контент и выдаст отчет с нарушениями.
    """
    await message.answer(help_text, reply_markup=get_back_to_main_keyboard())


@router.message(F.text == "⬅️ Главное меню")
async def back_to_main(message: types.Message):
    """Возврат в главное меню"""
    await cmd_start(message)


@router.message(F.text == "📊 Анализ текста")
async def request_text_analysis(message: types.Message):
    """Запрос текста для анализа"""
    await message.answer(
        "📝 Отправьте текст публикации для проверки на нарушения:",
        reply_markup=get_back_to_main_keyboard()
    )


@router.message(F.text == "🔗 Анализ ссылки")
async def request_link_analysis(message: types.Message):
    """Запрос ссылки для анализа"""
    await message.answer(
        "🔗 Отправьте ссылку на Telegram пост для анализа:",
        reply_markup=get_back_to_main_keyboard()
    )


@router.message()
async def handle_text(message: types.Message):
    """Основной обработчик текста и ссылок"""
    text = message.text.strip()

    # Игнорируем команды меню
    if text in ["📊 Анализ текста", "🔗 Анализ ссылки", "❓ Помощь"]:
        return

    if not text:
        await message.answer(
            "⚠️ Сообщение пустое. Отправьте текст или ссылку.",
            reply_markup=get_main_keyboard()
        )
        return

    # Показываем статус анализа
    status_msg = await message.answer("🔍 Анализирую контент...")

    # Определяем тип контента
    if text.startswith("https://t.me/"):
        content_type = "ссылка"
        analysis_text = await fetch(text)
        if not analysis_text:
            await status_msg.edit_text("⚠️ Не удалось получить текст из ссылки.")
            return
    else:
        content_type = "текст"
        analysis_text = text

    try:
        # Асинхронный запрос к API
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(REPORT_ENDPOINT, json={"text": analysis_text})
            resp.raise_for_status()
            data = resp.json()

        incidents = data.get("incidents", [])
        total_risk = data.get("total_risk", 0)
        risk_level = data.get("risk_level", "low")
        xlsx_base64 = data.get("xlsx_base64")
        recommendations = data.get("recommendations", "")

        # Форматируем сообщение с результатами
        results_text = f"""
✅ Результаты анализа:

📊 Тип: {content_type}
🚨 Нарушений: {len(incidents)}
⚡ Риск: {total_risk} ({risk_level})
        """

        await status_msg.edit_text(results_text)

        # Отправка рекомендаций
        if recommendations:
            await message.answer(f"💡 Рекомендации:\n{recommendations}")

        # Отправка XLSX отчета
        if xlsx_base64:
            xlsx_bytes = base64.b64decode(xlsx_base64)
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
                tmp_file.write(xlsx_bytes)
                tmp_file_path = tmp_file.name

            await message.answer_document(
                FSInputFile(tmp_file_path, filename="security_report.xlsx"),
                caption="📎 Детальный отчет"
            )
            os.remove(tmp_file_path)

    except httpx.TimeoutException:
        await status_msg.edit_text("⏰ Превышено время ожидания.")
    except httpx.RequestError as e:
        await status_msg.edit_text(f"🔌 Ошибка соединения: {e}")
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {e}")

    # Показываем главное меню после анализа
    await message.answer("Выберите действие:", reply_markup=get_main_keyboard())


# ====== Точка входа ======
async def main():
    """Запуск бота"""
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
