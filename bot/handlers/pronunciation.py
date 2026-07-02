import asyncio
import os

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.states import PracticeStates
from services.audio_converter import convert_ogg_to_wav
from services.azure_speech import azure_service

router = Router()


@router.message(F.voice, PracticeStates.waiting_for_voice)
async def process_voice_assessment(message: Message, state: FSMContext, bot):
    data = await state.get_data()
    target_word = data.get("practice_word")

    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    ogg_path = f"temp_{file_id}.ogg"
    wav_path = f"temp_{file_id}.wav"

    await bot.download_file(file.file_path, ogg_path)

    try:
        await asyncio.to_thread(convert_ogg_to_wav, ogg_path, wav_path)
    except Exception:
        await message.answer("Помилка обробки аудіо.")
        os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)
        return

    assessment = await asyncio.to_thread(
        azure_service.assess_pronunciation, wav_path, target_word
    )

    accuracy = assessment["NBest"][0]["PronunciationAssessment"]["AccuracyScore"]

    await message.answer(f"📊 Результати:\nТочність вимови: {accuracy}/100")

    os.remove(ogg_path)
    os.remove(wav_path)
    await state.clear()
