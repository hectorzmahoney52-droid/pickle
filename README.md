# 🤖 Telegram P2P Exchange Rate Bot

A Telegram bot that fetches live USDT P2P rates from **Binance** and **OKX** and displays averaged buy/sell prices for multiple fiat currencies.

## Supported Currency Pairs

| Exchange | Pair       |
|----------|------------|
| Binance  | USDT/KGS   |
| Binance  | USDT/KZT   |
| Binance  | USDT/GEL   |
| Binance  | USDT/AED   |
| Binance  | USDT/CNY   |
| OKX      | USDT/UZS   |

## Project Structure

```
tg_p2p_bot/
├── bot.py                  # Main bot entry point
├── config.py               # Settings via pydantic-settings + .env
├── requirements.txt
├── .env.example
├── services/
│   ├── __init__.py
│   ├── binance_service.py  # Binance P2P API client
│   └── okx_service.py      # OKX P2P API client
└── utils/
    ├── __init__.py
    └── calculations.py     # Averaging & formatting helpers
```

## Setup

### 1. Clone / copy the project

```bash
cd tg_p2p_bot
```

### 2. Create a virtual environment

```bash
python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and set your Telegram bot token:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
BINANCE_API_URL=https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search
OKX_API_URL=https://www.okx.com/v3/c2c/tradingOrders/books
```

> **Get a bot token**: Message [@BotFather](https://t.me/BotFather) on Telegram → `/newbot` → copy the token.

### 5. Run the bot

```bash
python bot.py
```

## Usage

1. Open your bot in Telegram and send `/start`.
2. Press **🔄 Refresh Rates** to fetch the latest P2P data.

Example output:

```
📊 P2P USDT Rates

USDT/KGS
Buy: 88.60 | Sell: 88.29

USDT/KZT
Buy: 522.14 | Sell: 519.87

USDT/GEL
Buy: 2.74 | Sell: 2.71

USDT/AED
Buy: 3.68 | Sell: 3.66

USDT/CNY
Buy: 7.24 | Sell: 7.21

USDT/UZS
Buy: 12,680.50 | Sell: 12,630.80

🕒 Updated: 2025-01-15 14:32 UTC
```

## How It Works

- On button press, the bot fires **async** requests to Binance and OKX simultaneously using `aiohttp`.
- For each currency pair and direction (BUY / SELL), it fetches the **latest 5 P2P advertisements**.
- The **average price** of those 5 ads is calculated and rounded to 2 decimal places.
- If one exchange is unreachable, the bot still shows data from the other and logs the error.

## Configuration Options

All settings live in `.env`:

| Variable          | Default                                                        | Description                        |
|-------------------|----------------------------------------------------------------|------------------------------------|
| `TELEGRAM_BOT_TOKEN` | *(required)*                                               | Your bot's API token               |
| `BINANCE_API_URL` | `https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search` | Binance P2P endpoint               |
| `OKX_API_URL`     | `https://www.okx.com/v3/c2c/tradingOrders/books`              | OKX P2P endpoint                   |

Additional constants in `config.py`:

| Setting          | Value | Description                          |
|------------------|-------|--------------------------------------|
| `REQUEST_TIMEOUT`| 10s   | HTTP request timeout                 |
| `MAX_RETRIES`    | 3     | Retries on failed requests           |
| `ADS_COUNT`      | 5     | Number of ads to average             |

## Logs

Logs are saved to `logs/bot.log` with automatic rotation (10 MB / 7-day retention).

- `INFO` — successful rate fetches
- `ERROR` — failed API requests or unexpected errors
