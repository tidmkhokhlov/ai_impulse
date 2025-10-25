import os
import httpx
import uuid

# === Константы ===
GIGACHAT_AUTH_TOKEN = os.getenv("GIGACHAT_API_KEY")
GIGACHAT_SCOPE = "GIGACHAT_API_PERS"
GIGACHAT_OAUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
GIGACHAT_CHAT_URL = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"


async def get_gigachat_token() -> str | None:
    if not GIGACHAT_AUTH_TOKEN:
        print("❌ Не найден GIGACHAT_AUTH_TOKEN в окружении")
        return None

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
        "RqUID": str(uuid.uuid4()),
        "Authorization": f"Basic {GIGACHAT_AUTH_TOKEN}",
    }

    data = "scope=GIGACHAT_API_PERS"  # важно: строка, не dict

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            resp = await client.post(GIGACHAT_OAUTH_URL, headers=headers, content=data)
            resp.raise_for_status()
            token = resp.json().get("access_token")
            return token
    except httpx.HTTPStatusError as e:
        print(f"⚠️ Ошибка получения токена GigaChat: {e.response.text}")
        return None



async def generate_recommendation(text: str, incidents: list) -> str:
    """
    Отправляет текст и список нарушений в GigaChat и получает рекомендации.
    Использует Basic-токен для получения access_token.
    """
    access_token = await get_gigachat_token()
    if not access_token:
        return "API GigaChat не настроен или токен не получен."

    prompt = (
        "Ты эксперт по рекламе. Дай рекомендации, как исправить следующие нарушения:\n"
        f"{', '.join(i['message'] for i in incidents)}\n\n"
        f"Текст публикации:\n{text}\n\n"
        "Напиши кратко, в виде списка с пунктами."
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": "Ты эксперт по рекламе и комплаенсу."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient(verify=False, timeout=20.0) as client:
            resp = await client.post(GIGACHAT_CHAT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Ошибка GigaChat: {e}"
