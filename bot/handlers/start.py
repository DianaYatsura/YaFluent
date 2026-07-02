from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.future import select

from core.db import AsyncSessionLocal
from models.models import User

router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    help_text = (
        "📖 <b>Посібник YaFluent Bot</b>\n\n"
        "Цей бот — твій AI-репетитор англійської. Ось що я вмію:\n\n"
        "🔍 <b>Пошук слів</b>\n"
        "• Надішли мені будь-яке <b>англійське слово або фразу</b>.\n"
        "• Я надам переклад, транскрипцію IPA, рівень CEFR та приклад використання.\n"
        "• А також надішлю <b>голосове повідомлення</b> з правильною вимовою.\n\n"
        "💾 <b>Особистий словник</b>\n"
        "• Натисни <b>'➕ Додати до словника'</b>, щоб зберегти слово.\n"
        "• Переглядай свої слова, натиснувши <b>'📁 Збережені слова'</b>.\n\n"
        "🧠 <b>Квізи для повторення</b>\n"
        "• Використовуй <code>/quiz</code> або <code>/review</code> для практики.\n"
        "• <b>Картки:</b> згадуєш переклад слова та оцінюєш свої знання.\n"
        "• <b>Письмо:</b> перекладай слово з української на англійську\n"
        "(підказки за потреби).\n"
        "• Я використовую <b>алгоритм інтервальних повторень (SM-2)</b>,\n"
        "щоб допомогти тобі ефективно запам'ятовувати слова.\n\n"
        "🗣 <b>Практика вимови</b>\n"
        "• Натисни <b>'🗣 Потренувати вимову'</b> під будь-яким словом.\n"
        "• Надішли <b>голосове повідомлення</b> зі своєю вимовою.\n"
        "• Я проаналізую її та поставлю <b>оцінку точності</b> (0-100%).\n\n"
        "🕹 <b>Команди</b>\n"
        "• <code>/start</code> — перезапустити бота.\n"
        "• <code>/quiz</code> або <code>/review</code> — почати повторення слів.\n"
        "• <code>/stop</code> — зупинити поточний квіз.\n"
        "• <code>/help</code> — показати цей посібник."
    )
    await message.answer(help_text, parse_mode="HTML")


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
                "Type /help to see everything I can do for you.\n"
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
                "Remember that every ocean begins with small drops.\n"
                "Use /help if you need a reminder of my features.",
                reply_markup=keyboard,
            )
