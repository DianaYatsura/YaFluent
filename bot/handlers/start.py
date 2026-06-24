from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.future import select

from core.db import AsyncSessionLocal
from models.models import User

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    tg_id = message.from_user.id
    username = message.from_user.username

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.telegram_id == tg_id))
        user = result.scalar_one_or_none()

        if not user:
            new_user = User(telegram_id=tg_id, username=username, english_level="A1")
            session.add(new_user)
            await session.commit()

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🚀 Почати квіз",
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
                f"Hello, {message.from_user.username}! 👋\n"
                "Welcome to YaFluent! I'm your AI English tutor.\n"
                "So let's get started!",
                reply_markup=keyboard,
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
            await message.answer(
                f"Welcome back, {message.from_user.username}!\n"
                "Remember that every ocean begins with small drops.",
                reply_markup=keyboard,
            )
