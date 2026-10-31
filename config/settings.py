"""
Centralized configuration for the Meme Coin Analyzer Bot
All configuration and constants are managed here
"""

import os
from typing import Dict, Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Bot Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN", "")
PAYMENT_AMOUNT = os.getenv("PAYMENT_AMOUNT", "0.2 SOL")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET", "")
GROUP_LINK = os.getenv("GROUP_LINK", "")
GROUP_NAME = os.getenv("GROUP_NAME", "Tentia Coin Alerts")

# Rate Limiting Configuration
RATE_LIMIT_SECONDS = int(os.getenv("RATE_LIMIT_SECONDS", "20"))
RATE_LIMIT_RUGCHECK_SECONDS = int(os.getenv("RATE_LIMIT_RUGCHECK_SECONDS", "20"))

# Solana Configuration
SOLANA_RPC_URL = os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
EXPECTED_MINIMUM_SOL = float(os.getenv("EXPECTED_MINIMUM_SOL", "0.19"))

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

# API Configuration
DEXSCREENER_BASE_URL = os.getenv("DEXSCREENER_BASE_URL", "https://api.dexscreener.com")
MORALIS_BASE_URL = os.getenv("MORALIS_BASE_URL", "https://solana-gateway.moralis.io")
RUGCHECK_BASE_URL = os.getenv("RUGCHECK_BASE_URL", "https://api.rugcheck.xyz/v1/tokens")

# Moralis API Key
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY", "")

# Analysis Configuration
ANALYSIS_TIMEOUT = 30.0  # seconds
OHLCV_LIMIT = 100
LOOKBACK_PERIODS = 20
VOLUME_SURGE_THRESHOLD = 3.0
VOLUME_INCREASE_THRESHOLD = 2.0
VOLUME_NORMAL_THRESHOLD = 0.5

# Risk Assessment Thresholds
EXTREME_RISK_THRESHOLD = 85
VERY_HIGH_RISK_THRESHOLD = 65
HIGH_RISK_THRESHOLD = 45
MODERATE_RISK_THRESHOLD = 25
LOW_RISK_THRESHOLD = 15

# Technical Analysis Parameters
RSI_OVERSOLD_THRESHOLD = 25
RSI_OVERBOUGHT_THRESHOLD = 75
RSI_APPROACHING_OVERBOUGHT = 65
RSI_APPROACHING_OVERSOLD = 35

# Liquidity Thresholds
EXTREMELY_LOW_LIQUIDITY = 1000
LOW_LIQUIDITY = 5000
MODERATE_LIQUIDITY = 20000
HIGH_LIQUIDITY = 100000

# Volume Thresholds
LOW_VOLUME = 1000
HIGH_VOLUME = 50000

# Volatility Thresholds
HIGH_VOLATILITY = 15
MODERATE_VOLATILITY = 8

# Holder Concentration Thresholds
EXTREME_CONCENTRATION = 95
VERY_HIGH_CONCENTRATION = 85
HIGH_CONCENTRATION = 70
MEDIUM_CONCENTRATION = 50
LOW_CONCENTRATION = 20

# Transfer Fee Thresholds
HIGH_TRANSFER_FEE = 10
MODERATE_TRANSFER_FEE = 5

# LP Lock Thresholds
EXCELLENT_LP_LOCK = 99
GOOD_LP_LOCK = 90
PARTIAL_LP_LOCK = 50

# Telegram Message Limits
MAX_MESSAGE_LENGTH = 4096
MAX_MESSAGE_LENGTH_SAFE = 4000

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Debug Configuration
DEBUG_MODE = True
RUGCHECK_DEBUG_MODE = True

# User Agent for API requests
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

# API Headers
DEFAULT_HEADERS = {
    'User-Agent': USER_AGENT,
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

# Timeout Configuration
REQUEST_TIMEOUT = 30
API_TIMEOUT = 15

# Cache Configuration
CACHE_ENABLED = True
CACHE_TTL = 300  # 5 minutes

# Worker Pool Configuration
MAX_WORKERS = 3  # Configured for standard instances
WORKER_POOL_SIZE = 3
MAX_CONCURRENT_USERS = 15
WORKER_TIMEOUT = 45

def get_config() -> Dict[str, Any]:
    """Get all configuration as a dictionary"""
    return {
        'bot_token': BOT_TOKEN,
        'payment_amount': PAYMENT_AMOUNT,
        'payment_wallet': PAYMENT_WALLET,
        'group_link': GROUP_LINK,
        'group_name': GROUP_NAME,
        'rate_limit_seconds': RATE_LIMIT_SECONDS,
        'rate_limit_rugcheck_seconds': RATE_LIMIT_RUGCHECK_SECONDS,
        'solana_rpc_url': SOLANA_RPC_URL,
        'expected_minimum_sol': EXPECTED_MINIMUM_SOL,
        'supabase_url': SUPABASE_URL,
        'supabase_key': SUPABASE_KEY,
        'dexscreeener_base_url': DEXSCREENER_BASE_URL,
        'moralis_base_url': MORALIS_BASE_URL,
        'rugcheck_base_url': RUGCHECK_BASE_URL,
        'moralis_api_key': MORALIS_API_KEY,
        'analysis_timeout': ANALYSIS_TIMEOUT,
        'ohlcv_limit': OHLCV_LIMIT,
        'lookback_periods': LOOKBACK_PERIODS,
        'debug_mode': DEBUG_MODE,
        'rugcheck_debug_mode': RUGCHECK_DEBUG_MODE,
        'max_workers': MAX_WORKERS,
        'worker_pool_size': WORKER_POOL_SIZE,
        'max_concurrent_users': MAX_CONCURRENT_USERS,
        'worker_timeout': WORKER_TIMEOUT,
        'cache_enabled': CACHE_ENABLED,
        'cache_ttl': CACHE_TTL
    }
