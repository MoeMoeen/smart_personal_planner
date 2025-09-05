# app/main.py

import os
from fastapi import FastAPI
from app.routers import goals, cycles, occurrences, planning, telegram, users
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    mode = os.environ.get("TELEGRAM_MODE", "webhook").lower()

    await telegram.application.initialize()
    await telegram.application.start()

    if mode == "webhook":
        webhook_url = os.environ.get("TELEGRAM_WEBHOOK_URL")
        if webhook_url:
            await telegram.application.bot.set_webhook(webhook_url)
            logging.info(f"🔗 Webhook set to {webhook_url}")
    else:
        logging.info("💡 Skipping webhook — running in polling mode (manual start required).")

    yield

    await telegram.application.stop()
    await telegram.application.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"message": "Welcome to Smart Personal Planner!"}

app.include_router(goals.router)
app.include_router(cycles.router)
app.include_router(occurrences.router)
app.include_router(planning.router)
app.include_router(users.router)
app.include_router(telegram.router)

