import asyncio
from datetime import datetime, timezone

from aiogram import Bot
from celery import Celery
from celery.schedules import crontab
from sqlalchemy import func, select

from core.config import settings
from core.db import AsyncSessionLocal
from models.models import User, UserWord

celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.conf.timezone = "Europe/Kyiv"

celery_app.conf.beat_schedule = {
    "send-daily-reminder-at-1pm": {
        "task": "tasks.worker.send_daily_reminder",
        "schedule": crontab(hour=13, minute=0),
    },
}


async def _send_daily_reminder():
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as session:
        stmt = (
            select(User.telegram_id)
            .join(UserWord, User.id == UserWord.user_id)
            .where(UserWord.next_review <= now)
            .group_by(User.telegram_id)
        )
        result = await session.execute(stmt)
        user_ids = result.scalars().all()

        for tg_id in user_ids:
            try:
                count_stmt = (
                    select(func.count(UserWord.id))
                    .join(User, User.id == UserWord.user_id)
                    .where(User.telegram_id == tg_id, UserWord.next_review <= now)
                )
                count_result = await session.execute(count_stmt)
                count = count_result.scalar()

                msg = (
                    f"🔔 <b>Час для повторення!</b>\n\n"
                    f"У тебе є {count} слів, які чекають на повторення. "
                    f"Приділи 5 хвилин, щоб не забути вивчене! 🧠\n\n"
                    f"Натисни /quiz, щоб почати."
                )
                await bot.send_message(tg_id, msg, parse_mode="HTML")
            except Exception as e:
                print(f"Failed to send reminder to {tg_id}: {e}")

    await bot.session.close()


@celery_app.task
def send_daily_reminder():
    asyncio.run(_send_daily_reminder())
