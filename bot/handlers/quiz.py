from datetime import datetime, timezone

from aiogram import F, Router, html
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select, update

from core.db import AsyncSessionLocal
from models.models import User, UserWord
from services.spaced_repetition import sm2_calculate

router = Router()


class QuizStates(StatesGroup):
    waiting_for_answer = State()
    hint_level = State()


@router.message(Command("stop"))
async def cmd_stop_quiz(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return await message.answer("Ти зараз не проходиш квіз.")

    await state.clear()

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

    msg = "🛑 Квіз зупинено. Повертайся, коли будеш готовий!"
    await message.answer(msg, reply_markup=keyboard)


@router.message(Command("quiz", "review"))
@router.callback_query(F.data == "start_quiz_from_welcome")
async def start_quiz(event: Message | CallbackQuery):
    if isinstance(event, CallbackQuery):
        message = event.message
        await event.answer()
    else:
        message = event

    user_id = event.from_user.id

    async with AsyncSessionLocal() as session:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if not user:
            msg = "Спочатку зареєструйтесь, надіславши /start"
            return await message.answer(msg)

        stmt = (
            select(UserWord)
            .where(
                UserWord.user_id == user.id,
                UserWord.next_review <= datetime.now(timezone.utc),
            )
            .limit(15)
        )
        result = await session.execute(stmt)
        words = result.scalars().all()

        keyboard_buttons = [
            [
                InlineKeyboardButton(
                    text="🇬🇧 -> 🇺🇦 (Картки)",
                    callback_data="quiz_mode:flashcards",
                ),
                InlineKeyboardButton(
                    text="🇺🇦 -> 🇬🇧 (Написання)",
                    callback_data="quiz_mode:write",
                ),
            ]
        ]

        if not words:
            all_words_stmt = (
                select(UserWord).where(UserWord.user_id == user.id).limit(1)
            )
            all_words_result = await session.execute(all_words_stmt)
            if not all_words_result.scalar_one_or_none():
                msg = "У тебе ще немає збережених слів. Додай щось у словник!"
                return await message.answer(msg)

            keyboard_buttons.append(
                [
                    InlineKeyboardButton(
                        text="🔄 Просто потренуватися",
                        callback_data="quiz_mode:practice",
                    )
                ]
            )
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
            msg = (
                "🎉 Всі заплановані слова вивчені! "
                "Але ти можеш просто потренуватися "
                "на випадкових словах."
            )
            return await message.answer(msg, reply_markup=keyboard)

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)

        await message.answer("Обери режим квізу:", reply_markup=keyboard)


@router.callback_query(F.data.startswith("quiz_mode:"))
async def select_quiz_mode(callback: CallbackQuery, state: FSMContext):
    mode = callback.data.split(":")[1]
    await state.update_data(quiz_mode=mode)
    await callback.answer()

    user_id = callback.from_user.id
    async with AsyncSessionLocal() as session:
        user_stmt = select(User).where(User.telegram_id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()

        if mode == "practice":
            from sqlalchemy.sql import func

            stmt = (
                select(UserWord)
                .where(UserWord.user_id == user.id)
                .order_by(func.random())
                .limit(1)
            )
        else:
            stmt = (
                select(UserWord)
                .where(
                    UserWord.user_id == user.id,
                    UserWord.next_review <= datetime.now(timezone.utc),
                )
                .limit(1)
            )

        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            return await callback.message.edit_text(
                "🎉 У тебе поки немає слів для вивчення."
            )

        if mode == "flashcards" or mode == "practice":
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="👁 Показати переклад",
                            callback_data=f"quiz_show:{word.id}",
                        )
                    ]
                ]
            )
            await callback.message.edit_text(
                f"Слово: <b>{word.word}</b>", reply_markup=keyboard, parse_mode="HTML"
            )
        else:
            await state.set_state(QuizStates.waiting_for_answer)
            await state.update_data(current_word_id=word.id, hint_level=0)

            hint = " _ " * len(word.word)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💡 Підказка",
                            callback_data=f"quiz_hint:{word.id}",
                        )
                    ]
                ]
            )

        msg = (
            f"Напиши англійське слово для:\n"
            f"🇺🇦 <b>{word.translation}</b>\n\n"
            f"Підказка: <code>{hint}</code> "
            f"({len(word.word)} літер)"
        )
        await callback.message.edit_text(
            msg,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


@router.message(QuizStates.waiting_for_answer)
async def handle_quiz_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    word_id = data.get("current_word_id")

    async with AsyncSessionLocal() as session:
        stmt = select(UserWord).where(UserWord.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            await state.clear()
            return await message.answer("Помилка: слово не знайдено.")

        user_answer = message.text.strip().lower()
        correct_word = word.word.lower()

        if user_answer == correct_word:
            quality = 5
            response = (
                f"✅ <b>Правильно!</b>\n\n<b>{word.word}</b> — {word.translation}"
            )
        else:
            quality = 1
            response = (
                f"❌ <b>Неправильно.</b>\n\n"
                f"Правильна відповідь: <b>{word.word}</b>\n"
                f"Твоя відповідь: "
                f"<strike>{html.quote(message.text)}</strike>"
            )

        current_interval = (word.next_review - word.last_reviewed).days
        if current_interval < 1:
            current_interval = 1

        new_rep_level, new_ef, new_interval_days, next_review_date = sm2_calculate(
            quality=quality,
            repetition_level=word.repetition_level,
            easiness_factor=word.easiness_factor,
            interval=current_interval,
        )

        await session.execute(
            update(UserWord)
            .where(UserWord.id == word_id)
            .values(
                repetition_level=new_rep_level,
                easiness_factor=new_ef,
                next_review=next_review_date,
                last_reviewed=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        await message.answer(response, parse_mode="HTML")
        next_stmt = (
            select(UserWord)
            .where(
                UserWord.user_id == word.user_id,
                UserWord.next_review <= datetime.now(timezone.utc),
            )
            .limit(1)
        )

        data = await state.get_data()
        if data.get("quiz_mode") == "practice":
            from sqlalchemy.sql import func

            next_stmt = (
                select(UserWord)
                .where(UserWord.id != word_id, UserWord.user_id == word.user_id)
                .order_by(func.random())
                .limit(1)
            )

        next_result = await session.execute(next_stmt)
        next_word = next_result.scalar_one_or_none()

        if next_word:
            await state.update_data(current_word_id=next_word.id, hint_level=0)
            hint = " _ " * len(next_word.word)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💡 Підказка",
                            callback_data=f"quiz_hint:{next_word.id}",
                        )
                    ]
                ]
            )
            msg = (
                f"Наступне слово:\n🇺🇦 <b>{next_word.translation}</b>\n\n"
                f"Підказка: <code>{hint}</code> ({len(next_word.word)} літер)"
            )
            await message.answer(
                msg,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await state.clear()
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
            await message.answer(
                "🎉 Всі слова на сьогодні перевірено!",
                reply_markup=keyboard,
            )


@router.callback_query(F.data.startswith("quiz_hint:"))
async def handle_quiz_hint(callback: CallbackQuery, state: FSMContext):
    word_id = int(callback.data.split(":")[1])
    data = await state.get_data()
    hint_level = data.get("hint_level", 0) + 1
    await state.update_data(hint_level=hint_level)

    async with AsyncSessionLocal() as session:
        stmt = select(UserWord).where(UserWord.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            return await callback.answer("Слово не знайдено.")

        w = word.word
        length = len(w)

        if hint_level == 1:
            hint = w[0] + " _ " * (length - 1)
        elif hint_level == 2:
            if length > 1:
                hint = w[0] + " _ " * (length - 2) + w[-1]
            else:
                hint = w
        elif hint_level == 3:
            if length > 2:
                mid = length // 2
                hint_list = list(" _ " * length)
                hint_list[0] = w[0]
                hint_list[mid] = w[mid]
                hint_list[-1] = w[-1]
                hint = "".join(hint_list)
            else:
                hint = w
        else:
            hint = w

        if hint_level >= 4:
            quality = 1
            current_interval = (word.next_review - word.last_reviewed).days
            if current_interval < 1:
                current_interval = 1

            new_rep_level, new_ef, new_interval_days, next_review_date = sm2_calculate(
                quality=quality,
                repetition_level=word.repetition_level,
                easiness_factor=word.easiness_factor,
                interval=current_interval,
            )

            await session.execute(
                update(UserWord)
                .where(UserWord.id == word_id)
                .values(
                    repetition_level=new_rep_level,
                    easiness_factor=new_ef,
                    next_review=next_review_date,
                    last_reviewed=datetime.now(timezone.utc),
                )
            )
            await session.commit()

            msg = (
                f"❌ <b>Ти використав усі підказки.</b>\n\n"
                f"Слово було: <b>{word.word}</b> — {word.translation}"
            )
            await callback.message.edit_text(msg, parse_mode="HTML")
            next_stmt = (
                select(UserWord)
                .where(
                    UserWord.user_id == word.user_id,
                    UserWord.next_review <= datetime.now(timezone.utc),
                )
                .limit(1)
            )

            data = await state.get_data()
            if data.get("quiz_mode") == "practice":
                from sqlalchemy.sql import func

                next_stmt = (
                    select(UserWord)
                    .where(UserWord.id != word_id, UserWord.user_id == word.user_id)
                    .order_by(func.random())
                    .limit(1)
                )

            next_result = await session.execute(next_stmt)
            next_word = next_result.scalar_one_or_none()

            if next_word:
                await state.update_data(current_word_id=next_word.id, hint_level=0)
                hint = " _ " * len(next_word.word)
                keyboard = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="💡 Підказка",
                                callback_data=f"quiz_hint:{next_word.id}",
                            )
                        ]
                    ]
                )
                msg = (
                    f"Наступне слово:\n"
                    f"🇺🇦 <b>{next_word.translation}</b>\n\n"
                    f"Підказка: <code>{hint}</code> "
                    f"({len(next_word.word)} літер)"
                )
                await callback.message.answer(
                    msg,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            else:
                await state.clear()
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
                msg = "🎉 Всі слова на сьогодні перевірено!"
                await callback.message.answer(
                    msg,
                    reply_markup=keyboard,
                )

            await callback.answer()
            return

        keyboard_list = []
        if hint_level < 4:
            keyboard_list.append(
                [
                    InlineKeyboardButton(
                        text="💡 Наступна підказка",
                        callback_data=f"quiz_hint:{word.id}",
                    )
                ]
            )

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_list)

        msg = (
            f"Напиши англійське слово для:\n"
            f"🇺🇦 <b>{word.translation}</b>\n\n"
            f"Підказка: <code>{hint}</code> ({length} літер)"
        )
        await callback.message.edit_text(
            msg,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        await callback.answer()


@router.callback_query(F.data.startswith("quiz_show:"))
async def show_translation(callback: CallbackQuery):
    word_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        stmt = select(UserWord).where(UserWord.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            return await callback.answer("Слово не знайдено.")

        btns = [
            InlineKeyboardButton(
                text="❌ Не знаю", callback_data=f"quiz_rate:1:{word.id}"
            ),
            InlineKeyboardButton(
                text="🤔 Важко", callback_data=f"quiz_rate:3:{word.id}"
            ),
            InlineKeyboardButton(
                text="✅ Знаю", callback_data=f"quiz_rate:5:{word.id}"
            ),
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[btns])

        msg = f"Слово: <b>{word.word}</b>\nПереклад: <b>{word.translation}</b>"
        await callback.message.edit_text(msg, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("quiz_rate:"))
async def rate_word(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    quality = int(parts[1])
    word_id = int(parts[2])

    async with AsyncSessionLocal() as session:
        stmt = select(UserWord).where(UserWord.id == word_id)
        result = await session.execute(stmt)
        word = result.scalar_one_or_none()

        if not word:
            return await callback.answer("Слово не знайдено.")

        current_interval = (word.next_review - word.last_reviewed).days
        if current_interval < 1:
            current_interval = 1

        new_rep_level, new_ef, new_interval_days, next_review_date = sm2_calculate(
            quality=quality,
            repetition_level=word.repetition_level,
            easiness_factor=word.easiness_factor,
            interval=current_interval,
        )

        await session.execute(
            update(UserWord)
            .where(UserWord.id == word_id)
            .values(
                repetition_level=new_rep_level,
                easiness_factor=new_ef,
                next_review=next_review_date,
                last_reviewed=datetime.now(timezone.utc),
            )
        )
        await session.commit()

        user_id = word.user_id
        next_stmt = (
            select(UserWord)
            .where(
                UserWord.user_id == user_id,
                UserWord.next_review <= datetime.now(timezone.utc),
            )
            .limit(1)
        )

        state_data = await state.get_data()
        if state_data.get("quiz_mode") == "practice":
            from sqlalchemy.sql import func

            next_stmt = (
                select(UserWord)
                .where(UserWord.id != word_id, UserWord.user_id == word.user_id)
                .order_by(func.random())
                .limit(1)
            )

        next_result = await session.execute(next_stmt)
        next_word = next_result.scalar_one_or_none()

        if next_word:
            state_data = await state.get_data()
            quiz_mode = state_data.get("quiz_mode", "flashcards")

            if quiz_mode == "flashcards":
                btns = [
                    InlineKeyboardButton(
                        text="👁 Показати переклад",
                        callback_data=f"quiz_show:{next_word.id}",
                    )
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=[btns])
                msg = f"Слово: <b>{next_word.word}</b>"
                await callback.message.edit_text(
                    msg,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
            else:
                btns = [
                    InlineKeyboardButton(
                        text="👁 Показати переклад",
                        callback_data=f"quiz_show:{next_word.id}",
                    )
                ]
                keyboard = InlineKeyboardMarkup(inline_keyboard=[btns])
                msg = f"Слово: <b>{next_word.word}</b>"
                await callback.message.edit_text(
                    msg,
                    reply_markup=keyboard,
                    parse_mode="HTML",
                )
        else:
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
            msg = "🎉 Всі слова на сьогодні перевірено!"
            await callback.message.edit_text(
                msg,
                reply_markup=keyboard,
            )

    await callback.answer()
