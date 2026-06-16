from io import BytesIO

from openai import AsyncOpenAI

from core.config import settings
from schemas.word import WordTranslationSchema


class OpenAIService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def translate_and_define_word(
        self, word: str
    ) -> WordTranslationSchema | None:
        system_prompt = (
            "You are an expert English-Ukrainian dictionary builder. "
            "Analyze the provided English word or phrase and extract its details "
            "strictly according to the schema. "
            "Provide 2-3 most common meanings/translations in Ukrainian."
        )
        try:
            response = await self.client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze the word: '{word}'"},
                ],
                response_format=WordTranslationSchema,
                temperature=0.3,
            )

            return response.choices[0].message.parsed
        except Exception as e:
            print(f"Error calling OpenAI API: {e}")
            return None

    async def generate_speech(self, text: str, voice: str = "alloy") -> BytesIO:
        try:
            response = await self.client.audio.speech.create(
                model="tts-1", voice=voice, input=text
            )

            audio_buffer = BytesIO(response.content)
            audio_buffer.name = "pronunciation.mp3"
            return audio_buffer

        except Exception as e:
            print(f"Error generating speech: {e}")
            return None


openai_service = OpenAIService()
