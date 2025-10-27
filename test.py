
import os
from openai import OpenAI


api_key = "YThkZmY0YjAtY2JhYy00MDBlLWE3YzctNDJkN2NjZGFhYmQz.a633accab6244d6afcab6bbf5ac5ff8a"
url = "https://foundation-models.api.cloud.ru/v1"




client = OpenAI(
    api_key=api_key,
    base_url=url
)

response = client.chat.completions.create(
    model="GigaChat/GigaChat-2-Max-without-filter",
    max_tokens=100,
    temperature=0.5,
    presence_penalty=0,
    top_p=0.95,
    messages=[
        {
            "role": "user",
            "content":"Как написать хороший код?"
        }
    ]
)

print(response.choices[0].message.content)
