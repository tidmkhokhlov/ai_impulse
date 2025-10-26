# AI-impulse — Автоматический аудит публикаций (реклама + ПДн)

Состав:
- FastAPI API для анализа публикаций
- Простой NLP-сервис
- Rules Engine (yaml rules)
- Telegram bot (aiogram)
- Генерация отчёта .xlsx
- Dockerfile + docker-compose

Инструкции:
1. Скопируйте `.env` или задайте переменные окружения:
   - TG_BOT_TOKEN (для бота)
   - GIGACHAT_API_KEY (gigachat api)
2. Запуск локально (без docker):
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   python -m bot.telegram_bot (в другом терминале)
   ```
3. Для запуска в docker: `docker-compose up --build`

