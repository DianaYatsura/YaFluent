from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
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
            await message.answer(
                f"Hello, {message.from_user.username}! 👋\n"
                "Welcome to YaFluent! I'm your AI English tutor"
                "So lets get started!"
            )
        else:
            await message.answer(
                f"Welcome back, {message.from_user.username}!"
                "Remember that every ocean begins with small drops"
            )
