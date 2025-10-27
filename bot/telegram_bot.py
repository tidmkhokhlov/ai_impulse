import os
import asyncio
import base64
import tempfile
import httpx
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton


from bot.monitoring.monitor import monitor

from bot.utils.fetch import fetch
load_dotenv()


# ====== Настройки ======
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/api/v1/analyze/"
REPORT_ENDPOINT = f"{API_URL}report"

# ====== айдишник админа  ======
ADMIN_IDS = [1431784288]  # Ваш ID или список ID администраторов
MONITORED_CHANNELS = set()  # Хранилище отслеживаемых каналов ( Временно нужно перенести в бд )

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
            [KeyboardButton(text="📢 Мониторинг каналов"), KeyboardButton(text="❓ Помощь")]
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

def get_monitoring_keyboard():
    """Клавиатура управления мониторингом"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Добавить канал"), KeyboardButton(text="📋 Мои подписки")],
            [KeyboardButton(text="❌ Удалить канал"), KeyboardButton(text="⬅️ Главное меню")]
        ],
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


# ====== Хэндлеры мониторинга ======
@router.message(F.text == "📢 Мониторинг каналов")
async def monitoring_menu(message: types.Message):
    """Меню управления мониторингом"""
    menu_text = """
📢 **Мониторинг Telegram каналов**

Функции:
• 📢 Добавить канал - начать отслеживание новых постов
• 📋 Мои подписки - список отслеживаемых каналов  
• ❌ Удалить канал - остановить мониторинг

Бот будет автоматически проверять каждый новый пост в канале и присылать уведомления о нарушениях.
    """
    await message.answer(menu_text, reply_markup=get_monitoring_keyboard())


@router.message(F.text == "📢 Добавить канал")
async def add_channel_request(message: types.Message):
    """Запрос пересланного сообщения для добавления канала"""
    await message.answer(
        "➡️ **Чтобы добавить канал для мониторинга:**\n\n"
        "1. Перейдите в нужный канал\n"
        "2. Выберите любое сообщение\n" 
        "3. Нажмите \"Переслать\"\n"
        "4. Выберите этого бота\n\n"
        "📝 *Бот автоматически добавит канал в отслеживание*",
        reply_markup=get_back_to_main_keyboard(),
        parse_mode="Markdown"
    )


@router.message(F.forward_from_chat)
async def handle_forwarded_channel(message: types.Message):
    """Обработка пересланного сообщения из канала"""
    try:
        channel = message.forward_from_chat

        # Проверяем, что это канал
        if channel.type != "channel":
            await message.answer("❌ Это не канал. Перешлите сообщение именно из канала.")
            return

        channel_id = channel.id
        channel_title = channel.title
        channel_username = f"@{channel.username}" if channel.username else f"ID: {channel_id}"

        # Проверяем права бота в канале
        try:
            bot_member = await bot.get_chat_member(channel_id, (await bot.get_me()).id)
            if bot_member.status not in ['administrator', 'member']:
                await message.answer(
                    f"❌ **Бот не добавлен в канал '{channel_title}'!**\n\n"
                    f"Чтобы начать мониторинг:\n"
                    f"1. Добавьте бота в канал как администратора\n"
                    f"2. Дайте права на чтение сообщений\n"
                    f"3. Перешлите сообщение снова",
                    reply_markup=get_monitoring_keyboard()
                )
                return
        except Exception as e:
            await message.answer(
                f"❌ **Не удалось проверить права бота:**\n{str(e)}\n\n"
                f"Убедитесь, что бот добавлен в канал как администратор.",
                reply_markup=get_monitoring_keyboard()
            )
            return

        # Добавляем канал в глобальное отслеживание
        if channel_id not in MONITORED_CHANNELS:
            MONITORED_CHANNELS.add(channel_id)

        # Добавляем подписку пользователя
        subscription_id = channel_username
        if monitor.add_subscription(message.from_user.id, subscription_id):

            await message.answer(
                f"✅ **Канал добавлен для мониторинга!**\n\n"
                f"📢 **Название:** {channel_title}\n"
                f"🔗 **ID:** {subscription_id}\n\n"
                f"Теперь бот будет анализировать каждый новый пост в этом канале "
                f"и присылать вам отчеты с анализом нарушений.",
                reply_markup=get_monitoring_keyboard()
            )

            print(f"✅ Добавлен канал: {channel_title} (ID: {channel_id}) для пользователя {message.from_user.id}")

        else:
            await message.answer(
                f"ℹ️ Канал '{channel_title}' уже отслеживается",
                reply_markup=get_monitoring_keyboard()
            )

    except Exception as e:
        await message.answer(
            f"❌ **Ошибка при добавлении канала:**\n{str(e)}",
            reply_markup=get_monitoring_keyboard()
        )

@router.message(F.text == "📋 Мои подписки")
async def show_subscriptions(message: types.Message):
    """Показать подписки пользователя"""
    subscriptions = monitor.get_user_subscriptions(message.from_user.id)

    if not subscriptions:
        await message.answer("❌ Вы не отслеживаете ни одного канала.")
        return

    subscriptions_text = "📋 **Ваши подписки:**\n\n" + "\n".join([f"• {sub}" for sub in subscriptions])
    await message.answer(subscriptions_text)


@router.message(F.text == "❌ Удалить канал")
async def remove_channel_request(message: types.Message):
    """Запрос username канала для удаления"""
    subscriptions = monitor.get_user_subscriptions(message.from_user.id)

    if not subscriptions:
        await message.answer("❌ У вас нет активных подписок.")
        return

    subscriptions_text = "Введите @username канала для удаления:\n\n" + "\n".join([f"• {sub}" for sub in subscriptions])
    await message.answer(subscriptions_text, reply_markup=get_back_to_main_keyboard())


@router.message(F.text.startswith('@'))
async def handle_channel_username(message: types.Message):
    """Обработка username канала"""
    username = message.text.strip().lower()

    # Определяем контекст - добавление или удаление
    if username in [sub.lower() for sub in monitor.get_user_subscriptions(message.from_user.id)]:
        # Удаление
        monitor.remove_subscription(message.from_user.id, username)
        await message.answer(f"✅ Канал {username} удален из мониторинга.")
    else:
        # Добавление
        if monitor.add_subscription(message.from_user.id, username):
            await message.answer(f"✅ Канал {username} добавлен в мониторинг!")
        else:
            await message.answer(f"⚠️ Вы уже отслеживаете канал {username}.")

    await message.answer("Выберите действие:", reply_markup=get_monitoring_keyboard())


@router.message()
async def handle_text(message: types.Message):
    """Основной обработчик текста и ссылок"""
    text = message.text.strip()

    # Игнорируем команды меню
    if text in ["📊 Анализ текста", "🔗 Анализ ссылки", "❓ Помощь", "📢 Добавить канал", "📢 Мониторинг каналов"]:
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