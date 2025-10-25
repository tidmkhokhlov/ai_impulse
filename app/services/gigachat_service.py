import os
import httpx

# URL публичного API GigaChat
GIGACHAT_API_URL = os.getenv("GIGACHAT_API_URL", "https://api.gigachat.ai/v1/chat")
# Твой публичный API_KEY
GIGACHAT_API_KEY = os.getenv("GIGACHAT_API_KEY")


async def generate_recommendation(text: str, incidents: list) -> str:
    """
    Отправляет текст и список нарушений в GigaChat и получает рекомендации.
    Используется публичный API_KEY (Bearer Token).
    """
    if not GIGACHAT_API_KEY:
        return "API GigaChat не настроен (нет API_KEY)."

    prompt = (
        "Ты эксперт по рекламе. Дай рекомендации, как исправить следующие нарушения:\n"
        f"{', '.join(i['message'] for i in incidents)}\n\n"
        f"Текст публикации:\n{text}\n\n"
        "Напиши кратко и понятно."
    )

    headers = {
        "Authorization": f"Bearer {GIGACHAT_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {"prompt": prompt, "max_tokens": 200}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(GIGACHAT_API_URL, headers=headers, json=payload)
            resp.raise_for_status()
            result = resp.json()
            # Предполагаем, что текст рекомендации в result["choices"][0]["text"]
            return result.get("choices", [{}])[0].get("text", "Нет рекомендации.")
    except Exception as e:
        return f"Ошибка GigaChat: {e}"