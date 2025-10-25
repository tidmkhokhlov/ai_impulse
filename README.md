# AI-impulse — Автоматический аудит публикаций (реклама + ПД)

Репозиторий — минимальный рабочий каркас для хакатона:
- FastAPI API для анализа публикаций
- Простой NLP-сервис (regex + heuristics)
- Rules Engine (yaml rules)
- Telegram bot (aiogram) — пример взаимодействия
- Генерация отчёта .xlsx
- Dockerfile + docker-compose
- Тесты pytest

Инструкции:
1. Скопируйте `.env` или задайте переменные окружения:
   - TG_BOT_TOKEN (для бота, опционально)
   - DATABASE_URL (postgres url, например postgresql://postgres:postgres@db/postgres)
2. Запуск локально (без docker):
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload --port 8000
   ```
3. Для запуска в docker: `docker-compose up --build`

