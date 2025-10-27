import os
from openai import AsyncOpenAI
from dotenv import load_dotenv
from rsa.cli import verify

load_dotenv()

# === Константы ===
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_BASE_URL = "https://foundation-models.api.cloud.ru/v1"
GIGACHAT_MODEL = "GigaChat/GigaChat-2-Max-without-filter"


def get_async_gigachat_client() -> AsyncOpenAI | None:
    """
    Создает и возвращает асинхронный клиент OpenAI для работы с GigaChat API.
    """
    if not GIGACHAT_API_KEY:
        print("❌ Не найден GIGACHAT_API_KEY в окружении")
        return None

    try:
        client = AsyncOpenAI(
            api_key=GIGACHAT_API_KEY,
            base_url=GIGACHAT_BASE_URL
        )
        return client
    except Exception as e:
        print(f"⚠️ Ошибка создания клиента GigaChat: {e}")
        return None


async def generate_recommendation(text: str, incidents: list) -> str:
    """
    Отправляет текст и список нарушений в GigaChat и получает рекомендации.
    Использует асинхронный OpenAI-совместимый клиент.
    """
    client = get_async_gigachat_client()
    if not client:
        return "API GigaChat не настроен или клиент не создан."

    prompt = (
        "Ты эксперт по рекламе. Дай рекомендации, как исправить следующие нарушения:\n"
        f"{', '.join(i['rule_name'] for i in incidents)}\n\n"
        f"Текст публикации:\n{text}\n\n"
        "Сначала напиши кратко, в виде списка с пунктами."
        "В конце предложи исправленную версию."
    )

    try:
        response = await client.chat.completions.create(
            model=GIGACHAT_MODEL,
            messages=[
                {"role": "system", "content": "Ты эксперт по рекламе и комплаенсу."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            top_p=0.95,
            presence_penalty=0,
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Ошибка GigaChat: {e}"

async def find_ads(text: str) -> str:
    """
    Отправляет текст и список нарушений в GigaChat и получает рекомендации.
    Использует асинхронный OpenAI-совместимый клиент.
    """
    client = get_async_gigachat_client()
    if not client:
        return "API GigaChat не настроен или клиент не создан."

    prompt = (
        "Ты эксперт по рекламе в телеграмм. Определи является ли следующая публикация рекламой:\n"
        f"Текст публикации:\n{text}\n\n"
        "В ответ просто напиши: Реклама или Не реклама."
    )

    try:
        response = await client.chat.completions.create(
            model=GIGACHAT_MODEL,
            messages=[
                {"role": "system", "content": "Ты эксперт по рекламе в телеграмм."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7,
            top_p=0.95,
            presence_penalty=0,
        )

        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Ошибка GigaChat: {e}"