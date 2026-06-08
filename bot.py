import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from loguru import logger

from config import settings
from services import BinanceService, OKXService
from utils.calculations import format_rate

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

Path("logs").mkdir(exist_ok=True)

logger.remove()
logger.add(
    sys.stderr,
    level=settings.LOG_LEVEL,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | {message}",
)
logger.add(
    settings.LOG_FILE,
    level=settings.LOG_LEVEL,
    rotation="10 MB",
    retention="7 days",
    compression="zip",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
)

# ---------------------------------------------------------------------------
# Bot & dispatcher
# ---------------------------------------------------------------------------

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

binance_service = BinanceService()
okx_service = OKXService()

# ---------------------------------------------------------------------------
# Keyboard
# ---------------------------------------------------------------------------

REFRESH_CALLBACK = "refresh_rates"


def get_refresh_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Refresh Rates", callback_data=REFRESH_CALLBACK)]
        ]
    )


# ---------------------------------------------------------------------------
# Rate fetching & formatting
# ---------------------------------------------------------------------------

async def fetch_and_format_rates() -> str:
    """Fetch rates from all exchanges and return a formatted message string."""

    binance_task = asyncio.create_task(binance_service.get_rates())
    okx_task = asyncio.create_task(okx_service.get_rates())

    binance_rates, okx_rates = await asyncio.gather(binance_task, okx_task)

    lines: list[str] = ["📊 <b>P2P USDT Rates</b>\n"]

    # --- Binance pairs ---
    if binance_rates is None:
        lines.append("❌ Failed to retrieve Binance P2P rates.\n")
        logger.error("Binance rates unavailable — skipping Binance section.")
    else:
        for fiat in settings.BINANCE_FIATS:
            data = binance_rates.get(fiat, {})
            buy = format_rate(data.get("buy"))
            sell = format_rate(data.get("sell"))
            lines.append(f"<b>USDT/{fiat}</b>")
            lines.append(f"Buy: {buy} | Sell: {sell}\n")

    # --- OKX pairs ---
    if okx_rates is None:
        lines.append("❌ Failed to retrieve OKX P2P rates.\n")
        logger.error("OKX rates unavailable — skipping OKX section.")
    else:
        for fiat in settings.OKX_FIATS:
            data = okx_rates.get(fiat, {})
            buy = format_rate(data.get("buy"))
            sell = format_rate(data.get("sell"))
            lines.append(f"<b>USDT/{fiat}</b>")
            lines.append(f"Buy: {buy} | Sell: {sell}\n")

    # --- Timestamp ---
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"🕒 Updated: {now_utc}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

@dp.message(CommandStart())
async def handle_start(message: Message) -> None:
    """Handle /start command."""
    logger.info(f"User {message.from_user.id} started the bot.")
    await message.answer(
        "👋 Welcome to the <b>P2P USDT Rate Bot</b>!\n\n"
        "Press the button below to fetch the latest P2P rates from Binance and OKX.",
        reply_markup=get_refresh_keyboard(),
        parse_mode="HTML",
    )


@dp.callback_query(F.data == REFRESH_CALLBACK)
async def handle_refresh(callback: CallbackQuery) -> None:
    """Handle the Refresh Rates button press."""
    user_id = callback.from_user.id
    logger.info(f"User {user_id} requested rate refresh.")

    await callback.answer("⏳ Fetching latest rates…")

    # Show a loading message while fetching
    await callback.message.edit_text(
        "⏳ <i>Fetching latest P2P rates, please wait…</i>",
        parse_mode="HTML",
    )

    try:
        text = await fetch_and_format_rates()
        logger.info(f"Rates successfully fetched for user {user_id}.")
    except Exception as e:
        logger.error(f"Unexpected error fetching rates for user {user_id}: {e}")
        text = "❌ An unexpected error occurred while fetching rates. Please try again later."

    await callback.message.edit_text(
        text,
        reply_markup=get_refresh_keyboard(),
        parse_mode="HTML",
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    logger.info("Starting P2P Rate Bot…")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
