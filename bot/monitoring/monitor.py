import asyncio
import logging
from typing import Dict, List, Set
from datetime import datetime
import httpx
from telethon import TelegramClient, events
from telethon.tl.types import Message
import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки
API_ID = os.getenv("TG_API_ID")
API_HASH = os.getenv("TG_API_HASH")
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
API_URL = "http://127.0.0.1:8000/api/v1/analyze/"
REPORT_ENDPOINT = f"{API_URL}report"

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChannelMonitor:
    def __init__(self):
        self.client = None
        self.subscribed_channels: Dict[int, Set[str]] = {}  # user_id: set(channel_usernames)
        self.setup_database()

    def setup_database(self):
        """Инициализация базы данных для хранения подписок"""
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS channel_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                channel_username TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, channel_username)
            )
        ''')
        conn.commit()
        conn.close()

    async def init_client(self):
        """Инициализация Telethon клиента"""
        if not API_ID or not API_HASH:
            raise ValueError("TG_API_ID or TG_API_HASH not set")

        self.client = TelegramClient("monitor_session", API_ID, API_HASH)
        await self.client.start()
        logger.info("Monitor client started")

    async def analyze_content(self, text: str) -> dict:
        """Анализ контента через API"""
        if not text or len(text.strip()) < 10:  # Минимальная длина текста
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(REPORT_ENDPOINT, json={"text": text})
                resp.raise_for_status()
                data = resp.json()

                # Фильтруем только значимые результаты
                incidents = data.get("incidents", [])
                total_risk = data.get("total_risk", 0)

                if incidents and total_risk > 20:  # Порог значимости
                    return data
                return None

        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return None

    async def send_alert(self, user_id: int, channel: str, message_text: str, analysis_result: dict):
        """Отправка уведомления пользователю"""
        try:
            from aiogram import Bot
            bot = Bot(token=BOT_TOKEN)

            incidents_count = len(analysis_result.get("incidents", []))
            total_risk = analysis_result.get("total_risk", 0)
            risk_level = analysis_result.get("risk_level", "low")

            alert_text = f"""
🚨 **Обнаружены нарушения в канале!**

📢 Канал: {channel}
📊 Нарушений: {incidents_count}
⚡ Уровень риска: {total_risk} ({risk_level})

📝 Сообщение:
{message_text[:500]}{'...' if len(message_text) > 500 else ''}

💡 Рекомендации:
{analysis_result.get('recommendations', 'Проверить контент вручную')}
            """

            await bot.send_message(user_id, alert_text)
            await bot.close()

        except Exception as e:
            logger.error(f"Alert send error: {e}")

    def add_subscription(self, user_id: int, channel_username: str):
        """Добавление канала в мониторинг"""
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO channel_subscriptions (user_id, channel_username) VALUES (?, ?)",
                (user_id, channel_username.lower())
            )
            conn.commit()

            if user_id not in self.subscribed_channels:
                self.subscribed_channels[user_id] = set()
            self.subscribed_channels[user_id].add(channel_username.lower())

            logger.info(f"User {user_id} subscribed to {channel_username}")
            return True

        except sqlite3.IntegrityError:
            return False  # Уже подписан
        finally:
            conn.close()

    def remove_subscription(self, user_id: int, channel_username: str):
        """Удаление канала из мониторинга"""
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM channel_subscriptions WHERE user_id = ? AND channel_username = ?",
            (user_id, channel_username.lower())
        )
        conn.commit()
        conn.close()

        if user_id in self.subscribed_channels:
            self.subscribed_channels[user_id].discard(channel_username.lower())

        logger.info(f"User {user_id} unsubscribed from {channel_username}")

    def get_user_subscriptions(self, user_id: int) -> List[str]:
        """Получение списка подписок пользователя"""
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()

        cursor.execute(
            "SELECT channel_username FROM channel_subscriptions WHERE user_id = ?",
            (user_id,)
        )
        subscriptions = [row[0] for row in cursor.fetchall()]
        conn.close()

        return subscriptions

    def load_all_subscriptions(self):
        """Загрузка всех подписок из базы данных"""
        conn = sqlite3.connect('monitoring.db')
        cursor = conn.cursor()

        cursor.execute("SELECT DISTINCT user_id, channel_username FROM channel_subscriptions")
        for user_id, channel_username in cursor.fetchall():
            if user_id not in self.subscribed_channels:
                self.subscribed_channels[user_id] = set()
            self.subscribed_channels[user_id].add(channel_username)

        conn.close()
        logger.info(f"Loaded {len(self.subscribed_channels)} users with subscriptions")

    async def setup_handlers(self):
        """Настройка обработчиков новых сообщений"""

        @self.client.on(events.NewMessage)
        async def handler(event: Message):
            try:
                if not event.message.text and not event.message.caption:
                    return

                # Получаем текст сообщения
                text = event.message.text or ""
                if event.message.caption:
                    text += f"\n\n{event.message.caption}"

                # Получаем информацию о канале/чате
                chat = await event.get_chat()
                channel_username = getattr(chat, 'username', None)
                if not channel_username:
                    return

                channel_username = channel_username.lower()

                # Проверяем подписчиков этого канала
                for user_id, channels in self.subscribed_channels.items():
                    if channel_username in channels:
                        # Анализируем контент
                        analysis_result = await self.analyze_content(text)
                        if analysis_result:
                            await self.send_alert(user_id, channel_username, text, analysis_result)

            except Exception as e:
                logger.error(f"Handler error: {e}")

    async def start_monitoring(self):
        """Запуск мониторинга"""
        await self.init_client()
        self.load_all_subscriptions()
        await self.setup_handlers()

        logger.info("Channel monitoring started")
        await self.client.run_until_disconnected()


# Глобальный экземпляр монитора
monitor = ChannelMonitor()