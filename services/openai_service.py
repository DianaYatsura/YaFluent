from openai import AsyncOpenAI

from core.config import settings

client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def get_chat_response(messages: list):
    response = await client.chat.completions.create(
        model="gpt-4o-mini", messages=messages
    )
    return response.choices[0].message.content
