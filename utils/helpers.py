"""
Common utility functions for the Meme Coin Analyzer Bot
"""

import pandas as pd
import numpy as np
from typing import Optional, Union, Any
from datetime import datetime, timedelta
from config.settings import (
    VOLUME_SURGE_THRESHOLD, VOLUME_INCREASE_THRESHOLD, VOLUME_NORMAL_THRESHOLD,
    RSI_OVERSOLD_THRESHOLD, RSI_OVERBOUGHT_THRESHOLD, RSI_APPROACHING_OVERBOUGHT, RSI_APPROACHING_OVERSOLD,
    HIGH_VOLATILITY, MODERATE_VOLATILITY, LOW_LIQUIDITY, HIGH_LIQUIDITY, EXTREMELY_LOW_LIQUIDITY,
    HIGH_VOLUME, LOW_VOLUME, EXTREME_CONCENTRATION, VERY_HIGH_CONCENTRATION, HIGH_CONCENTRATION,
    MEDIUM_CONCENTRATION, LOW_CONCENTRATION, HIGH_TRANSFER_FEE, MODERATE_TRANSFER_FEE,
    EXCELLENT_LP_LOCK, GOOD_LP_LOCK, PARTIAL_LP_LOCK
)

def datetime_to_timestamp(dt: datetime) -> int:
    """Convert datetime to timestamp"""
    return int(dt.timestamp())

def human_format(num: Union[int, float, None]) -> str:
    """Format large numbers with appropriate suffixes"""
    if num is None or pd.isna(num):
        return "N/A"
    
    try:
        num = float(num)
        for unit in ['', 'K', 'M', 'B']:
            if abs(num) < 1000:
                return f"{num:.2f}{unit}"
            num /= 1000
        return f"{num:.2f}T"
    except (ValueError, TypeError):
        return "N/A"

def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def safe_get_nested(data: dict, *keys, default: Any = None) -> Any:
    """Safely get nested dictionary values"""
    for key in keys:
        if isinstance(data, dict) and key in data and data[key] is not None:
            data = data[key]
        else:
            return default
    return data

def safe_html_escape(text: Any) -> str:
    """Safely escape HTML characters and handle None values"""
    if text is None or text == "N/A":
        return "N/A"
    return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')

def safe_get_escaped(data: dict, key: str, default: str = "N/A") -> str:
    """Get data and escape HTML characters"""
    value = data.get(key, default) if data.get(key) is not None else default
    return safe_html_escape(value)

def validate_solana_address(address: str) -> bool:
    """Validate Solana token address format"""
    if not address or len(address) < 32 or len(address) > 44:
        return False
    
    base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return all(c in base58_chars for c in address)

def calculate_dynamic_thresholds(ohlcv_data: pd.DataFrame, lookback_periods: int = 20) -> tuple[float, float]:
    """Calculate dynamic dip and pump thresholds"""
    if len(ohlcv_data) < lookback_periods:
        lookback_periods = len(ohlcv_data)
    
    recent_data = ohlcv_data.tail(lookback_periods)
    price_changes = recent_data['close'].pct_change().dropna()
    
    if len(price_changes) == 0:
        return -0.05, 0.05
    
    mean_change = price_changes.mean()
    std_dev_change = price_changes.std()
    
    dip_threshold = mean_change - (std_dev_change * 2.0)
    pump_threshold = mean_change + (std_dev_change * 2.0)
    
    return dip_threshold, pump_threshold

def analyze_volume_profile(ohlcv_data: pd.DataFrame) -> str:
    """Analyze volume profile and return description"""
    if len(ohlcv_data) < 10:
        return "Insufficient data"
    
    recent_volume = ohlcv_data['volume'].tail(5).mean()
    avg_volume = ohlcv_data['volume'].mean()
    
    volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
    
    if volume_surge > VOLUME_SURGE_THRESHOLD:
        return "🚀 High Volume Surge"
    elif volume_surge > VOLUME_INCREASE_THRESHOLD:
        return "📈 Increased Volume"
    elif volume_surge > VOLUME_NORMAL_THRESHOLD:
        return "🟡 Normal Volume"
    else:
        return "📉 Low Volume"

def calculate_momentum_score(ohlcv_data: pd.DataFrame) -> tuple[float, str]:
    """Calculate momentum score and description"""
    if len(ohlcv_data) < 20:
        return 0, "Insufficient data"
    
    current_price = float(ohlcv_data['close'].iloc[-1])
    
    if len(ohlcv_data) >= 60:
        price_1h_ago = float(ohlcv_data['close'].iloc[-60])
        price_1h = (current_price / price_1h_ago) - 1 if price_1h_ago > 0 else 0
    else:
        price_1h = 0
    
    start_price = float(ohlcv_data['close'].iloc[0])
    price_change = (current_price / start_price) - 1 if start_price > 0 else 0
    
    rsi_current = ohlcv_data['rsi'].iloc[-1] if 'rsi' in ohlcv_data.columns else 50
    if pd.isna(rsi_current):
        rsi_current = 50
    rsi_momentum = (rsi_current - 50) / 50
    
    macd_current = ohlcv_data['macd'].iloc[-1] if 'macd' in ohlcv_data.columns else 0
    macd_signal = ohlcv_data['signal_line'].iloc[-1] if 'signal_line' in ohlcv_data.columns else 0
    
    if pd.isna(macd_current):
        macd_current = 0
    if pd.isna(macd_signal):
        macd_signal = 0
        
    macd_momentum = 1 if macd_current > macd_signal else -1
    
    momentum_score = (price_change * 0.4) + (rsi_momentum * 0.3) + (macd_momentum * 0.3)
    
    if momentum_score > 0.1:
        momentum_desc = "🚀 Strong Bullish"
    elif momentum_score > 0.05:
        momentum_desc = "📈 Bullish"
    elif momentum_score > -0.05:
        momentum_desc = "🟡 Neutral"
    elif momentum_score > -0.1:
        momentum_desc = "📉 Bearish"
    else:
        momentum_desc = "🔻 Strong Bearish"
    
    return momentum_score, momentum_desc

def get_risk_level_from_score(risk_score: Union[int, float, None]) -> tuple[str, str, float]:
    """Convert API risk score to emoji and description"""
    if risk_score is None:
        return "❓", "Unknown", 50
    
    try:
        risk_score = int(float(risk_score))
        
        # RugCheck uses 0-100 scale, Lower scores = better (safer)
        if risk_score <= 20:
            return "🟢", "Good", risk_score * 0.5  # 0-10% rug probability
        elif risk_score <= 40:
            return "🟡", "Fair", 10 + (risk_score - 20) * 1.0  # 10-30% rug probability
        elif risk_score <= 60:
            return "🟠", "Poor", 30 + (risk_score - 40) * 1.5  # 30-60% rug probability
        elif risk_score <= 80:
            return "🔴", "High Risk", 60 + (risk_score - 60) * 1.5  # 60-90% rug probability
        else:
            return "💀", "Very High Risk", min(90 + (risk_score - 80) * 0.5, 99.9)  # 90-99.9%
    except (ValueError, TypeError):
        return "❓", "Unknown", 50

def get_rug_probability_emoji(probability: float) -> str:
    """Get emoji for rug probability"""
    if probability >= EXTREME_RISK_THRESHOLD:
        return "💀"
    elif probability >= VERY_HIGH_RISK_THRESHOLD:
        return "🔴"
    elif probability >= HIGH_RISK_THRESHOLD:
        return "🟠"
    elif probability >= MODERATE_RISK_THRESHOLD:
        return "🟡"
    else:
        return "🟢"

def assess_liquidity_health(liquidity_usd: float, lp_providers: int) -> str:
    """Assess overall liquidity health"""
    if liquidity_usd > HIGH_LIQUIDITY and lp_providers > 10:
        return "🟢 Excellent"
    elif liquidity_usd > 50000 and lp_providers > 5:
        return "🟢 Good"
    elif liquidity_usd > MODERATE_LIQUIDITY and lp_providers > 2:
        return "🟡 Fair"
    elif liquidity_usd > LOW_LIQUIDITY:
        return "🟠 Low"
    else:
        return "🔴 Very Poor"

def get_distribution_score(top_1_pct: float, top_10_pct: float) -> str:
    """Calculate distribution health score"""
    if top_1_pct > EXTREME_CONCENTRATION:
        return "💀 Extremely Poor"
    elif top_1_pct > VERY_HIGH_CONCENTRATION:
        return "🔴 Very Poor"
    elif top_1_pct > HIGH_CONCENTRATION:
        return "🟠 Poor"
    elif top_1_pct > MEDIUM_CONCENTRATION:
        return "🟡 Fair"
    elif top_1_pct > LOW_CONCENTRATION:
        return "🟡 Moderate"
    elif top_10_pct > 90:
        return "🟡 Fair (concentrated in top 10)"
    else:
        return "🟢 Good"

def get_concentration_risk(top_1_pct: float) -> str:
    """Get concentration risk level"""
    if top_1_pct > EXTREME_CONCENTRATION:
        return "💀 EXTREME RISK"
    elif top_1_pct > VERY_HIGH_CONCENTRATION:
        return "🔴 Very High Risk"
    elif top_1_pct > HIGH_CONCENTRATION:
        return "🟠 High Risk"
    elif top_1_pct > MEDIUM_CONCENTRATION:
        return "🟡 Medium Risk"
    elif top_1_pct > LOW_CONCENTRATION:
        return "🟡 Low-Medium Risk"
    else:
        return "🟢 Low Risk"

def format_number(num: Union[int, float, None]) -> str:
    """Format large numbers with appropriate suffixes"""
    if num is None:
        return "N/A"
    
    try:
        num = float(num)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.2f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.2f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.2f}K"
        else:
            return f"{num:.2f}"
    except (ValueError, TypeError):
        return str(num)

def format_percentage(num: Union[int, float, None]) -> str:
    """Format percentage values"""
    if num is None:
        return "N/A"
    try:
        return f"{float(num):.1f}%"
    except (ValueError, TypeError):
        return str(num)

def format_price(price: Union[int, float, None]) -> str:
    """Format price with appropriate decimal places"""
    if price is None:
        return "N/A"
    try:
        price = float(price)
        if price == 0:
            return "$0.00"
        elif price < 0.000001:
            return f"${price:.10f}"
        elif price < 0.001:
            return f"${price:.8f}"
        elif price < 1:
            return f"${price:.6f}"
        else:
            return f"${price:.4f}"
    except (ValueError, TypeError):
        return str(price)

def get_comprehensive_risk_assessment(api_score: Union[int, float], rug_probability: float) -> dict[str, str]:
    """Provide comprehensive risk assessment"""
    if rug_probability >= EXTREME_RISK_THRESHOLD:
        return {
            'level': '💀 EXTREME DANGER',
            'recommendation': '❌ AVOID AT ALL COSTS',
            'description': 'Critical red flags detected. Very high probability of rug pull.',
            'action': 'Do not invest. Exit immediately if holding.'
        }
    elif rug_probability >= VERY_HIGH_RISK_THRESHOLD:
        return {
            'level': '🔴 VERY HIGH RISK',
            'recommendation': '⚠️ EXTREME CAUTION',
            'description': 'Significant risks detected. High chance of losing funds.',
            'action': 'Only for very experienced traders with small amounts.'
        }
    elif rug_probability >= HIGH_RISK_THRESHOLD:
        return {
            'level': '🟠 HIGH RISK',
            'recommendation': '⚠️ HIGH CAUTION',
            'description': 'Several concerning factors. Above average risk.',
            'action': 'Thorough research required. Consider risks carefully.'
        }
    elif rug_probability >= MODERATE_RISK_THRESHOLD:
        return {
            'level': '🟡 MODERATE RISK',
            'recommendation': '🔍 RESEARCH REQUIRED',
            'description': 'Some risk factors present. Standard DeFi risks.',
            'action': 'Do your research. Understand the risks.'
        }
    elif rug_probability >= LOW_RISK_THRESHOLD:
        return {
            'level': '🟢 LOW-MODERATE RISK',
            'recommendation': '✅ ACCEPTABLE WITH CAUTION',
            'description': 'Below average risk but still requires caution.',
            'action': 'Standard due diligence recommended.'
        }
    else:
        return {
            'level': '🟢 LOW RISK',
            'recommendation': '✅ RELATIVELY SAFE',
            'description': 'Low risk indicators. Appears legitimate.',
            'action': 'Standard crypto risks apply. Still do your research.'
        }
