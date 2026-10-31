# Solana Meme Coin Analyzer Bot

An asynchronous Telegram bot built with Python for real-time Solana meme coin analysis, technical momentum scoring, on-chain liquidity risk checks, and subscription management.

---

## Features

- **Technical Momentum Analysis**: Calculates EMAs (12/26), MACD, RSI, Bollinger Bands, ATR, volume profiles, and support/resistance levels from OHLCV candle data.
- **Meme Coin Pattern Detection**: Analyzes volume surges, price momentum, and pump-and-dump behavior with dynamic threshold adaptation.
- **On-Chain Rug Pull Detection**: Integrates with RugCheck API to audit mint/freeze authority, top 10 holder concentration, LP burn/lock status, and insider activity.
- **Concurrent Worker Pool**: Priority task queue with bounded worker threads and per-user concurrency limits to handle simultaneous user requests.
- **Multi-Tier Rate Limiting**: Cooldown enforcement per user and command to protect external APIs.
- **Subscription Management**: Automated subscription verification with on-chain Solana transaction checks (via Solana RPC) backed by Supabase.
- **Low-Memory Optimization**: Chunked data processing and explicit memory management designed for constrained cloud environments (e.g., AWS EC2 t2.micro).

---

## Architecture Overview

```
Conversion/
├── concurrent_processing/   # Concurrency and rate limiting
│   ├── rate_limiter.py      # Dual-tier rate limiting and sliding windows
│   └── worker_pool.py       # Asynchronous priority task worker pool
├── config/                  # Centralized configuration
│   ├── logging_config.py    # Formatted stdout logger
│   └── settings.py          # Environment configuration and thresholds
├── database/                # Persistence layer
│   └── subscription_db.py   # Supabase client wrapper for subscriptions
├── models/                  # Dataclass schemas
│   └── token_data.py        # Token, Price, Market, Rug, and Analysis models
├── services/                # Business logic services
│   ├── analysis_engine.py   # Technical indicators and pattern analysis
│   ├── analysis_service.py  # Orchestration facade
│   ├── data_fetcher.py      # DexScreener & Moralis API client
│   └── rug_checker.py       # Rug pull analysis wrapper
├── tests/                   # Test suite
│   ├── test_confidence_score.py
│   ├── test_meme_coin_analysis.py
│   ├── test_new_architecture.py
│   └── test_realistic_meme_coin.py
├── utils/                   # Shared helpers and system utilities
│   ├── helpers.py           # Address validation, unit formatting
│   └── system_monitor.py    # CPU/RAM/Disk monitor
├── main_refactored.py       # Modern modular bot entrypoint
├── main.py                  # Standalone bot entrypoint
├── solana_checker.py        # Solana on-chain transaction verification
├── requirements.txt         # Production dependencies
└── .env.example             # Environment variable template
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Optional: Moralis API Key, Solana RPC Endpoint (e.g. Helius / QuickNode), Supabase Project

### 2. Clone and Install Dependencies

```bash
git clone <repository-url>
cd <repository-directory>

# Create and activate a virtual environment
python -m venv venv
# Linux / macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Telegram bot API token from BotFather | Required |
| `PAYMENT_WALLET` | Solana public address to receive subscription payments | Optional |
| `PAYMENT_AMOUNT` | Display amount for membership (e.g. `0.2 SOL`) | `0.2 SOL` |
| `EXPECTED_MINIMUM_SOL` | Minimum SOL transfer amount accepted by verifier | `0.19` |
| `GROUP_LINK` | Telegram private alert group invite link | Optional |
| `SOLANA_RPC_URL` | Solana JSON-RPC endpoint URL | `https://api.mainnet-beta.solana.com` |
| `SUPABASE_URL` | Supabase project URL | Optional |
| `SUPABASE_KEY` | Supabase anon or service key | Optional |
| `MORALIS_API_KEY` | Moralis Web3 API key for OHLCV data | Optional |
| `RATE_LIMIT_SECONDS` | Cooldown period between analysis calls | `20` |

### 4. Running the Bot

Run the refactored modular bot:

```bash
python main_refactored.py
```

Or run the legacy entrypoint:

```bash
python main.py
```

### 5. Running Tests

```bash
pytest tests/
```

---

## Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Displays welcome overview and feature list |
| `/analyze <address>` | Comprehensive token analysis (momentum, indicators, rug risk) |
| `/rugcheck <address>` | Full security and risk report via RugCheck |
| `/quick <address>` | Rapid security summary |
| `/subscribe` | Subscription payment details and instructions |
| `/verify <tx_hash>` | Verifies on-chain payment and activates subscription |
| `/status` | Checks subscription expiry and active rate limits |
| `/group` | Link to private alert group (subscribers only) |
| `/help` | Complete commands guide |

