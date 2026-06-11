from aiogram import Router, types
from aiogram.filters import CommandStart

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    await message.answer(
        f"Hello, {message.from_user.full_name}! "
        "Every ocean begins with small drops, so we shouldn't waste time."
    )
