from aiogram import F, Router, html
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select

from bot.states import PracticeStates
from core.db import AsyncSessionLocal
from models.models import DictionaryWord, User, UserWord
from services.openai_service import openai_service

router = Router()


@router.message(StateFilter(None), F.text & ~F.text.startswith("/"))
async def handle_word_search(message: Message):
    if len(message.text) > 50:
        return await message.answer(
            "Будь ласка, надсилай тільки слова або короткі фрази."
        )

    waiting_msg = await message.answer("🔄 Звертаюсь до YaFluent AI...")

    parsed_word = await openai_service.translate_and_define_word(message.text.strip())

    if not parsed_word:
        return await waiting_msg.edit_text(
            "❌ Не вдалося проаналізувати слово. Спробуй ще раз."
        )

    async with AsyncSessionLocal() as session:
        stmt = select(DictionaryWord).where(
            DictionaryWord.word == parsed_word.word.lower()
        )
        result = await session.execute(stmt)
        meanings_str = ", ".join(parsed_word.meanings)
        if not result.scalar_one_or_none():
            db_word = DictionaryWord(
                word=parsed_word.word.lower(),
                translation=meanings_str,
                definition=parsed_word.definition,
                example_sentence=parsed_word.example_en,
            )
            session.add(db_word)
            await session.commit()

    msg = (
        f"📚 <b>Word:</b> {html.quote(parsed_word.word.upper())} "
        f"[{html.quote(parsed_word.ipa)}]\n"
        f"🏅 <b>Level:</b> {html.quote(parsed_word.cefr_level)}\n"
        f"🇺🇦 <b>Переклад:</b> {html.quote(meanings_str)}\n\n"
        f"📖 <b>Definition:</b> {html.quote(parsed_word.definition)}\n\n"
        f"💡 <b>Example:</b>\n"
        f"• {html.quote(parsed_word.example_en)}\n"
        f"• <i>({html.quote(parsed_word.example_ua)})</i>"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Додати до словника",
                    callback_data=f"add_word:{parsed_word.word[:30]}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗣 Потренувати вимову",
                    callback_data=f"practice_pronunciation:{parsed_word.word[:30]}",
                )
            ],
        ]
    )

    await waiting_msg.edit_text("🔊 Генерую правильну вимову...")

    audio_buffer = await openai_service.generate_speech(parsed_word.word, voice="nova")

    await waiting_msg.delete()

    await message.answer(msg, reply_markup=keyboard, parse_mode="HTML")

    if audio_buffer:
        audio_file = BufferedInputFile(audio_buffer.getvalue(), filename="speech.mp3")
        await message.answer_voice(
            voice=audio_file,
            caption=f"🗣 Вимова для слова '{parsed_word.word}'",
        )


@router.callback_query(F.data.startswith("add_word:"))
async def handle_add_word(callback: CallbackQuery):
    word_to_add = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            msg = "❌ Користувача не знайдено."
            return await callback.answer(msg, show_alert=True)

        check_stmt = select(UserWord).where(
            UserWord.user_id == user.id, UserWord.word == word_to_add.lower()
        )
        check_result = await session.execute(check_stmt)
        if check_result.scalar_one_or_none():
            msg = f"✅ Слово '{word_to_add}' вже є у твоєму словнику!"
            return await callback.answer(msg)

        dict_stmt = select(DictionaryWord).where(
            DictionaryWord.word == word_to_add.lower()
        )
        dict_result = await session.execute(dict_stmt)
        dict_word = dict_result.scalar_one_or_none()

        if not dict_word:
            return await callback.answer("❌ Помилка: дані слова не знайдено.")

        new_user_word = UserWord(
            user_id=user.id, word=dict_word.word, translation=dict_word.translation
        )
        session.add(new_user_word)
        await session.commit()

    msg_ok = f"✅ Слово '{dict_word.word}' додано до словника!"
    await callback.answer(msg_ok)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📚 Повторити слова",
                    callback_data="start_quiz_from_welcome",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📁 Збережені слова",
                    callback_data="show_saved_words",
                )
            ],
        ]
    )

    await callback.message.edit_reply_markup(reply_markup=keyboard)


@router.callback_query(F.data.startswith("practice_pronunciation:"))
async def handle_practice_pronunciation(callback: CallbackQuery, state: FSMContext):
    word = callback.data.split(":", 1)[1]
    await state.set_state(PracticeStates.waiting_for_voice)
    await state.update_data(practice_word=word)

    await callback.message.answer(
        f"Надішли голосове повідомлення, де ти вимовляєш слово: <b>{word}</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "show_saved_words")
async def handle_show_saved_words(callback: CallbackQuery):
    user_id = callback.from_user.id

    async with AsyncSessionLocal() as session:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            msg = "Користувача не знайдено."
            return await callback.answer(msg, show_alert=True)

        words_stmt = (
            select(UserWord).where(UserWord.user_id == user.id).order_by(UserWord.word)
        )
        words_result = await session.execute(words_stmt)
        user_words = words_result.scalars().all()

        if not user_words:
            msg = "Твій словник поки порожній. Додай нові слова!"
            await callback.answer(msg)
            return

        response_text = "<b>📁 Твої збережені слова:</b>\n\n"
        keyboard_buttons = []
        for uw in user_words:
            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text=f"📖 {uw.word}", callback_data=f"view_word:{uw.word[:30]}"
                    )
                ]
            )

        keyboard_buttons.extend(
            [
                [
                    InlineKeyboardButton(
                        text="📚 Повторити слова",
                        callback_data="start_quiz_from_welcome",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔄 Оновити список",
                        callback_data="show_saved_words",
                    )
                ],
            ]
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await callback.message.answer(
            response_text, reply_markup=keyboard, parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("view_word:"))
async def handle_view_word(callback: CallbackQuery):
    word_text = callback.data.split(":", 1)[1]

    async with AsyncSessionLocal() as session:
        stmt = select(DictionaryWord).where(DictionaryWord.word == word_text.lower())
        result = await session.execute(stmt)
        db_word = result.scalar_one_or_none()

    if not db_word:
        return await callback.answer("❌ Слово не знайдено в базі.", show_alert=True)

    msg = (
        f"📚 <b>Word:</b> {html.quote(db_word.word.upper())}\n"
        f"🇺🇦 <b>Переклад:</b> {html.quote(db_word.translation)}\n\n"
        f"📖 <b>Definition:</b> {html.quote(db_word.definition or 'N/A')}\n\n"
        f"💡 <b>Example:</b>\n"
        f"• {html.quote(db_word.example_sentence or 'N/A')}\n"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗣 Потренувати вимову",
                    callback_data=f"practice_pronunciation:{db_word.word[:30]}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📁 Назад до списку",
                    callback_data="show_saved_words",
                )
            ],
        ]
    )

    await callback.message.answer(msg, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()
