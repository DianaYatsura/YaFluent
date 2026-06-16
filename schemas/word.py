from pydantic import BaseModel, Field


class WordTranslationSchema(BaseModel):
    word: str = Field(description="The original English word or phrase in lowercase")
    ipa: str = Field(
        description="International Phonetic Alphabet (IPA) transcription, e.g., /fɪʃ/"
    )
    definition: str = Field(description="Clear English definition of the word")
    meanings: list[str] = Field(
        description="2-3 most common Ukrainian translations (meanings)"
    )
    cefr_level: str = Field(description="CEFR level (A1, A2, B1, B2, C1, or C2)")
    example_en: str = Field(
        description="An interesting example sentence in English using this word"
    )
    example_ua: str = Field(description="Ukrainian translation of the example sentence")
