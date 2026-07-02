import asyncio
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.redis import RedisStorage
from fastapi import FastAPI
from redis.asyncio import Redis

from bot.handlers import start
from bot.handlers.pronunciation import router as pronunciation_router
from bot.handlers.quiz import router as quiz_router
from bot.handlers.vocabulary import router as vocabulary_router
from core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
redis = Redis.from_url(settings.REDIS_URL)
storage = RedisStorage(redis)
dp = Dispatcher(storage=storage)


@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = None
    if settings.USE_POLLING:
        print("Starting bot in Polling mode...")
        await bot.delete_webhook(drop_pending_updates=True)
        polling_task = asyncio.create_task(dp.start_polling(bot))
    else:
        print(f"Setting webhook to {settings.WEBHOOK_URL}")
        await bot.set_webhook(settings.WEBHOOK_URL, drop_pending_updates=True)

    yield

    if polling_task:
        print("Stopping bot polling...")
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            print("Bot polling task cancelled.")

    print("Shutting down bot...")
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

dp.include_router(start.router)
dp.include_router(quiz_router)
dp.include_router(vocabulary_router)
dp.include_router(pronunciation_router)


@app.post("/webhook")
async def webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": "YaFluent Bot is running"}
