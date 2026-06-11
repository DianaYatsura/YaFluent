from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher, types
from fastapi import FastAPI

from bot.handlers import start
from core.config import settings

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: set webhook
    await bot.set_webhook(settings.WEBHOOK_URL)
    yield
    # Shutdown: close bot session
    await bot.session.close()


app = FastAPI(lifespan=lifespan)

dp.include_router(start.router)


@app.post("/webhook")
async def webhook(update: dict):
    telegram_update = types.Update(**update)
    await dp.feed_update(bot, telegram_update)
    return {"ok": True}


@app.get("/")
async def root():
    return {"message": "YaFluent Bot is running"}
