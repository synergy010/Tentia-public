import os
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import ta   
from telegram.helpers import escape_markdown
import json
import logging

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def datetime_to_timestamp(dt):
    return int(dt.timestamp())

def get_token_pair_address(token_address):
    url = f"https://api.dexscreener.com/tokens/v1/solana/{token_address}"
    response = requests.get(url)    
    if response.status_code == 200:
        data = response.json()
        if isinstance(data, list) and len(data) > 0:
            pair_data = data[0]
            if 'pairAddress' in pair_data:
                pair_address = pair_data['pairAddress']
                print(f"Pair address found: {pair_address}")
                return pair_address
            else:
                print(f"Pair address not found in response for token address: {token_address}")
        else:
            print(f"No trading pairs found for token address: {token_address}")
    else:
        print(f"Failed to fetch data for token address: {token_address}")
    return None

def human_format(num):
    if num is None or pd.isna(num):
        return "N/A"
    for unit in ['', 'K', 'M', 'B']:
        if abs(num) < 1000:
            return f"{num:.2f}{unit}"
        num /= 1000
    return f"{num:.2f}T"

def fetch_ohlcv_data(pair_address, from_date, to_date, limit=50):
    url = f'https://solana-gateway.moralis.io/token/mainnet/pairs/{pair_address}/ohlcv'
    params = {
        'limit': limit,
        'fromDate': from_date,
        'toDate': to_date,
        'timeframe': '1min',
        'currency': 'usd'
    }
    headers = {'accept': 'application/json', 'X-Api-Key': os.getenv('MORALIS_API_KEY', '')}
    response = requests.get(url, params=params, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if 'result' in data:
            return process_ohlcv_data(data)
    return None

def fetch_dex_screener_data(pair_address):
    url = f'https://api.dexscreener.com/latest/dex/pairs/solana/{pair_address}'
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    return None

# RugChecker Integration
class RugCheckerIntegration:
    def __init__(self, debug_mode=False):
        self.api_base_url = "https://api.rugcheck.xyz/v1/tokens"
        self.debug_mode = debug_mode
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def debug_log(self, message, data=None):
        if self.debug_mode:
            print(f"🐛 RUG DEBUG: {message}")
            if data is not None:
                print(f"📄 DATA: {str(data)[:500]}...")
    
    def get_risk_level_from_score(self, risk_score):
        if risk_score is None:
            return "❓", "Unknown", 50
        
        risk_score = int(float(risk_score))
        
        if risk_score <= 20:
            return "🟢", "Good", risk_score * 0.5
        elif risk_score <= 40:
            return "🟡", "Fair", 10 + (risk_score - 20) * 1.0
        elif risk_score <= 60:
            return "🟠", "Poor", 30 + (risk_score - 40) * 1.5
        elif risk_score <= 80:
            return "🔴", "High Risk", 60 + (risk_score - 60) * 1.5
        else:
            return "💀", "Very High Risk", min(90 + (risk_score - 80) * 0.5, 99.9)
        
    def calculate_refined_rug_probability(self, api_score, data: dict) -> tuple:
        _, _, base_probability = self.get_risk_level_from_score(api_score)
        
        critical_factors = []
        probability_adjustments = 0
        
        # CRITICAL INSTANT RUG INDICATORS
        if data.get('rugged', False):
            return 100.0, ["💀 TOKEN IS CONFIRMED RUGGED!"]
        
        # MAJOR SECURITY ISSUES
        token = data.get('token', {})
        
        if token.get('mintAuthority'):
            probability_adjustments += 20
            critical_factors.append("🔴 Mint Authority Active - Can create unlimited tokens")
        
        if token.get('freezeAuthority'):
            probability_adjustments += 15
            critical_factors.append("🔴 Freeze Authority Active - Can freeze user accounts")
        
        # HOLDER CONCENTRATION ANALYSIS
        top_holders = data.get('topHolders', [])
        if top_holders:
            top_1_pct = float(top_holders[0].get('pct', 0)) if len(top_holders) > 0 else 0
            if top_1_pct > 95:
                probability_adjustments += 25
                critical_factors.append(f"💀 Extreme concentration: Top holder owns {top_1_pct:.1f}%")
            elif top_1_pct > 85:
                probability_adjustments += 20
                critical_factors.append(f"🔴 Very high concentration: Top holder owns {top_1_pct:.1f}%")
            elif top_1_pct > 70:
                probability_adjustments += 10
                critical_factors.append(f"🟠 High concentration: Top holder owns {top_1_pct:.1f}%")
            elif top_1_pct > 50:
                probability_adjustments += 5
                critical_factors.append(f"🟡 Medium concentration: Top holder owns {top_1_pct:.1f}%")
            elif top_1_pct < 20:
                probability_adjustments -= 5
                critical_factors.append("🟢 Good token distribution")
        
        # LIQUIDITY ANALYSIS
        total_liquidity = data.get('totalStableLiquidity', 0)
        if total_liquidity < 1000:
            probability_adjustments += 15
            critical_factors.append(f"🔴 Extremely low liquidity: ${total_liquidity:.2f}")
        elif total_liquidity < 5000:
            probability_adjustments += 8
            critical_factors.append(f"🟠 Low liquidity: ${total_liquidity:.2f}")
        elif total_liquidity > 100000:
            probability_adjustments -= 5
            critical_factors.append("🟢 High liquidity pool")
        
        # LP PROVIDERS
        lp_providers = data.get('totalLPProviders', 0)
        if lp_providers == 0:
            probability_adjustments += 10
            critical_factors.append("🔴 No LP providers detected")
        elif lp_providers < 2:
            probability_adjustments += 5
            critical_factors.append(f"🟡 Very few LP providers: {lp_providers}")
        
        # Calculate final probability
        final_probability = base_probability + probability_adjustments
        final_probability = max(0.1, min(99.9, final_probability))
        
        return final_probability, critical_factors[:6]
    
    async def check_token_rug(self, token_address: str) -> dict:
        try:
            token_address = token_address.strip()
            self.debug_log(f"Starting rug check for token: {token_address}")
            
            api_url = f"{self.api_base_url}/{token_address}/report"
            response = requests.get(api_url, headers=self.headers, timeout=15)
            
            if response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Token not found in RugCheck database',
                    'rug_probability': None,
                    'risk_score': None,
                    'security_flags': None
                }
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'RugCheck API failed: {response.status_code}',
                    'rug_probability': None,
                    'risk_score': None,
                    'security_flags': None
                }
            
            api_data = response.json()
            return self.process_rug_data(api_data)
            
        except Exception as e:
            self.debug_log(f"Error in rug check: {str(e)}")
            return {
                'success': False,
                'error': f'Rug check failed: {str(e)}',
                'rug_probability': None,
                'risk_score': None,
                'security_flags': None
            }
    
    def process_rug_data(self, api_data: dict) -> dict:
        try:
            api_risk_score = api_data.get('score', 0)
            api_risk_score = max(0, min(100, int(float(api_risk_score))))
            
            rug_probability, risk_factors = self.calculate_refined_rug_probability(api_risk_score, api_data)
            
            risk_emoji, risk_level, _ = self.get_risk_level_from_score(api_risk_score)
            
            # Extract security flags
            token_info = api_data.get('token', {})
            token_meta = api_data.get('tokenMeta', {})
            
            security_flags = {
                'mint_authority': bool(token_info.get('mintAuthority')),
                'freeze_authority': bool(token_info.get('freezeAuthority')),
                'rugged': api_data.get('rugged', False),
                'mutable_metadata': token_meta.get('mutable', False),
                'transfer_fee_active': bool(api_data.get('transferFee', {}).get('pct', 0) > 0),
                'transfer_fee_pct': api_data.get('transferFee', {}).get('pct', 0),
            }
            
            # Extract holder info
            top_holders = api_data.get('topHolders', [])
            holder_info = {}
            if top_holders:
                holder_info = {
                    'total_holders': api_data.get('totalHolders', 0),
                    'top_holder_pct': float(top_holders[0].get('pct', 0)),
                    'top_5_pct': sum(float(h.get('pct', 0)) for h in top_holders[:min(5, len(top_holders))]),
                }
            
            # Extract liquidity info
            liquidity_info = {
                'total_stable_usd': api_data.get('totalStableLiquidity', 0),
                'total_lp_providers': api_data.get('totalLPProviders', 0),
            }
            
            return {
                'success': True,
                'risk_score': api_risk_score,
                'risk_level': risk_level,
                'risk_emoji': risk_emoji,
                'rug_probability': round(rug_probability, 1),
                'risk_factors': risk_factors,
                'security_flags': security_flags,
                'holder_info': holder_info,
                'liquidity_info': liquidity_info,
                'insider_networks': len(api_data.get('insiderNetworks', [])),
                'jupiter_verified': api_data.get('verification', {}).get('jup_verified', False),
                'raw_data': api_data  # Keep raw data for detailed analysis
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing rug data: {str(e)}',
                'rug_probability': None,
                'risk_score': None,
                'security_flags': None
            }

# Initialize RugChecker
rug_checker = RugCheckerIntegration(debug_mode=True)

def process_ohlcv_data(data):
    if 'result' not in data or not data['result']:
        return "This coin was launched recently, and OHLCV data is not available yet."
    
    df = pd.DataFrame(data['result'])

    if df.empty:
        return "This coin was just launched, and OHLCV data is not available yet."
    
    columns_needed = {'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}
    df = df.rename(columns=columns_needed)
    
    df = df[list(columns_needed.values())]
    
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)
   
    for col in ['open', 'high', 'low', 'close', 'volume']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        
    return add_technical_indicators(df)

def add_technical_indicators(df):
    if df.empty or len(df) < 20:
        return df
    
    df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
    df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
    df['macd'] = df['ema_12'] - df['ema_26']
    df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
    df['macd_histogram'] = df['macd'] - df['signal_line']
    
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['std_20'] = df['close'].rolling(window=20).std()
    df['bollinger_upper'] = df['sma_20'] + (df['std_20'] * 2)
    df['bollinger_lower'] = df['sma_20'] - (df['std_20'] * 2)
    
    delta = df['close'].diff(1)
    gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
    
    rs = gain / loss.replace(0, np.nan)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['close'].shift(1))
    df['tr3'] = abs(df['low'] - df['close'].shift(1))
    df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
    df['atr'] = df['true_range'].rolling(window=14).mean()
    
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_ma']
    
    return df

def calculate_dynamic_thresholds(ohlcv_data, lookback_periods=20):
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

def analyze_volume_profile(ohlcv_data):
    if len(ohlcv_data) < 10:
        return "Insufficient data"
    
    recent_volume = ohlcv_data['volume'].tail(5).mean()
    avg_volume = ohlcv_data['volume'].mean()
    
    volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
    
    if volume_surge > 3:
        return "🚀 High Volume Surge"
    elif volume_surge > 2:
        return "📈 Increased Volume"
    elif volume_surge > 0.5:
        return "🟡 Normal Volume"
    else:
        return "📉 Low Volume"

def calculate_momentum_score(ohlcv_data):
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

def get_final_verdict(ohlcv_data, pair_info, rug_data=None):
    """Enhanced scoring system with rug check integration and fixed confidence score"""
    score = 0
    reasons = []
    
    latest_price = float(ohlcv_data['close'].iloc[-1])
    prev_price = float(ohlcv_data['close'].iloc[-2]) if len(ohlcv_data) > 1 else latest_price
    
    # CRITICAL RUG CHECK OVERRIDE
    if rug_data and rug_data.get('success'):
        rug_probability = rug_data.get('rug_probability', 0)
        security_flags = rug_data.get('security_flags', {})
        
        # Instant avoid conditions
        if security_flags and security_flags.get('rugged', False):
            return "AVOID - RUGGED", "💀 Token is confirmed rugged", -100
        
        if rug_probability >= 85:
            score -= 50
            reasons.append(f"💀 EXTREME rug risk: {rug_probability:.1f}% probability")
        elif rug_probability >= 65:
            score -= 30
            reasons.append(f"🔴 Very high rug risk: {rug_probability:.1f}% probability")
        elif rug_probability >= 45:
            score -= 15
            reasons.append(f"🟠 High rug risk: {rug_probability:.1f}% probability")
        elif rug_probability >= 25:
            score -= 5
            reasons.append(f"🟡 Moderate rug risk: {rug_probability:.1f}% probability")
        else:
            score += 5
            reasons.append(f"🟢 Low rug risk: {rug_probability:.1f}% probability")
        
        # Security flag penalties
        if security_flags:
            if security_flags.get('mint_authority', False):
                score -= 20
                reasons.append("🔴 Mint authority active - unlimited token creation risk")
            
            if security_flags.get('freeze_authority', False):
                score -= 15
                reasons.append("🔴 Freeze authority active - account freeze risk")
            
            if security_flags.get('transfer_fee_active', False):
                fee_pct = security_flags.get('transfer_fee_pct', 0)
                if fee_pct > 10:
                    score -= 10
                    reasons.append(f"🔴 High transfer fee: {fee_pct}%")
        
        # Holder concentration from rug checker
        holder_info = rug_data.get('holder_info', {})
        if holder_info:
            top_holder_pct = holder_info.get('top_holder_pct', 0)
            if top_holder_pct > 85:
                score -= 25
                reasons.append(f"💀 Extreme concentration: Top holder {top_holder_pct:.1f}%")
            elif top_holder_pct > 70:
                score -= 15
                reasons.append(f"🔴 High concentration: Top holder {top_holder_pct:.1f}%")
        
        # LP Provider check
        rug_liquidity = rug_data.get('liquidity_info', {})
        if rug_liquidity:
            lp_providers = rug_liquidity.get('total_lp_providers', 0)
            if lp_providers == 0:
                score -= 20
                reasons.append("🔴 No LP providers - high manipulation risk")
        
        # Insider networks
        insider_networks = rug_data.get('insider_networks', 0)
        if insider_networks > 0:
            score -= 10
            reasons.append(f"🕸️ {insider_networks} insider network(s) detected")
    
    # Price action analysis
    price_change = (latest_price - prev_price) / prev_price if prev_price > 0 else 0
    dip_threshold, pump_threshold = calculate_dynamic_thresholds(ohlcv_data)
    
    if price_change < dip_threshold:
        score += 2
        reasons.append(f"Significant dip detected ({price_change:.2%}), potential buy opportunity")
    elif price_change > pump_threshold:
        score += 3
        reasons.append(f"Strong pump detected ({price_change:.2%}), momentum play")
    
    # Volume analysis
    volume_analysis = analyze_volume_profile(ohlcv_data)
    if "High Volume Surge" in volume_analysis:
        score += 3
        reasons.append("Exceptional volume surge indicating strong interest")
    elif "Increased Volume" in volume_analysis:
        score += 2
        reasons.append("Volume increasing, showing growing interest")
    elif "Low Volume" in volume_analysis:
        score -= 2
        reasons.append("Low volume, lack of interest")
    
    # Technical indicators
    rsi_current = ohlcv_data['rsi'].iloc[-1] if 'rsi' in ohlcv_data.columns and not pd.isna(ohlcv_data['rsi'].iloc[-1]) else 50
    
    if rsi_current < 25:
        score += 3
        reasons.append("Extremely oversold conditions (RSI < 25)")
    elif rsi_current < 35:
        score += 2
        reasons.append("Oversold conditions, potential reversal")
    elif rsi_current > 75:
        score -= 2
        reasons.append("Overbought conditions, potential correction")
    elif rsi_current > 65:
        score -= 1
        reasons.append("Approaching overbought levels")
    
    # Liquidity and market structure - FIXED SAFE ACCESS
    liquidity = safe_float(safe_get_nested(pair_info, 'liquidity', 'usd'), 0.0)
    volume_24h = safe_float(safe_get_nested(pair_info, 'volume', 'h24'), 0.0)
    
    if liquidity < 5000:
        score -= 4
        reasons.append("Extremely low liquidity, high manipulation risk")
    elif liquidity < 20000:
        score -= 2
        reasons.append("Low liquidity, proceed with caution")
    elif liquidity > 100000:
        score += 2
        reasons.append("Good liquidity providing safer trading")
    
    if volume_24h < 1000:
        score -= 3
        reasons.append("Very low trading volume")
    elif volume_24h > 50000:
        score += 2
        reasons.append("High trading volume indicating active market")
    
    # Momentum analysis
    momentum_score, momentum_desc = calculate_momentum_score(ohlcv_data)
    if "Strong Bullish" in momentum_desc:
        score += 3
        reasons.append("Strong bullish momentum across timeframes")
    elif "Bullish" in momentum_desc:
        score += 1
        reasons.append("Positive momentum detected")
    elif "Strong Bearish" in momentum_desc:
        score -= 3
        reasons.append("Strong bearish momentum, avoid")
    
    # Convert raw score to confidence percentage (0-100)
    # Normalize score to confidence range
    raw_score = score
    confidence_score = max(0, min(100, 50 + (raw_score * 5)))  # Base 50, adjust by score
    
    # Final verdict based on score with rug check consideration
    if rug_data and rug_data.get('success'):
        rug_probability = rug_data.get('rug_probability', 0)
        if rug_probability >= 85:
            verdict = "AVOID - HIGH RUG RISK"
        elif rug_probability >= 65 or raw_score <= -20:
            verdict = "AVOID - RISKY"
        elif raw_score >= 8 and rug_probability < 25:
            verdict = "STRONG BUY"
        elif raw_score >= 5 and rug_probability < 45:
            verdict = "BUY"
        elif raw_score >= 2 and rug_probability < 65:
            verdict = "MODERATE BUY"
        elif raw_score >= -2:
            verdict = "WAIT"
        else:
            verdict = "AVOID"
    else:
        # Fallback to original logic if no rug data
        if raw_score >= 8:
            verdict = "STRONG BUY"
        elif raw_score >= 5:
            verdict = "BUY"
        elif raw_score >= 2:
            verdict = "MODERATE BUY"
        elif raw_score >= -2:
            verdict = "WAIT"
        else:
            verdict = "AVOID"
    
    reason_text = " | ".join(reasons) if reasons else "No significant signals detected"
    return verdict, reason_text, confidence_score

def get_detailed_rug_analysis(rug_data):
    """Generate detailed rug check analysis for output"""
    if not rug_data or not rug_data.get('success'):
        return {
            'status': 'FAILED',
            'summary': 'Rug check failed or unavailable',
            'detailed_analysis': 'Unable to perform rug analysis',
            'security_summary': 'Security status unknown',
            'holder_analysis': 'Holder analysis unavailable',
            'liquidity_analysis': 'Liquidity analysis unavailable',
            'additional_info': 'Additional data unavailable',
            'risk_factors': []
        }
    
    # Basic metrics
    rug_probability = rug_data.get('rug_probability', 0)
    risk_score = rug_data.get('risk_score', 0)
    risk_level = rug_data.get('risk_level', 'Unknown')
    risk_emoji = rug_data.get('risk_emoji', '❓')
    
    # Security flags analysis
    security_flags = rug_data.get('security_flags', {})
    security_issues = []
    
    if security_flags.get('rugged', False):
        security_issues.append("💀 TOKEN IS CONFIRMED RUGGED")
    if security_flags.get('mint_authority', False):
        security_issues.append("🔴 Mint Authority Active (Can create unlimited tokens)")
    if security_flags.get('freeze_authority', False):
        security_issues.append("🔴 Freeze Authority Active (Can freeze user accounts)")
    if security_flags.get('mutable_metadata', False):
        security_issues.append("🟡 Mutable Metadata (Token info can be changed)")
    if security_flags.get('transfer_fee_active', False):
        fee_pct = security_flags.get('transfer_fee_pct', 0)
        security_issues.append(f"🟡 Transfer Fee Active ({fee_pct}% fee)")
    
    if not security_issues:
        security_issues.append("🟢 No major security issues detected")
    
    # Holder analysis
    holder_info = rug_data.get('holder_info', {})
    holder_analysis = "Holder data unavailable"
    
    if holder_info:
        total_holders = holder_info.get('total_holders', 0)
        top_holder_pct = holder_info.get('top_holder_pct', 0)
        top_5_pct = holder_info.get('top_5_pct', 0)
        
        concentration_risk = ""
        if top_holder_pct > 85:
            concentration_risk = "💀 EXTREME concentration risk"
        elif top_holder_pct > 70:
            concentration_risk = "🔴 Very high concentration risk"
        elif top_holder_pct > 50:
            concentration_risk = "🟠 High concentration risk"
        elif top_holder_pct > 30:
            concentration_risk = "🟡 Moderate concentration risk"
        else:
            concentration_risk = "🟢 Good distribution"
        
        holder_analysis = f"""
📊 Total Holders: {total_holders:,}
👑 Top Holder: {top_holder_pct:.2f}%
🏆 Top 5 Holders: {top_5_pct:.2f}%
⚖️ Distribution: {concentration_risk}"""
    
    # Liquidity analysis
    liquidity_info = rug_data.get('liquidity_info', {})
    liquidity_analysis = "Liquidity data unavailable"
    
    if liquidity_info:
        stable_liquidity = liquidity_info.get('total_stable_usd', 0)
        lp_providers = liquidity_info.get('total_lp_providers', 0)
        
        liq_risk = ""
        if stable_liquidity < 1000:
            liq_risk = "💀 EXTREMELY low liquidity"
        elif stable_liquidity < 5000:
            liq_risk = "🔴 Very low liquidity"
        elif stable_liquidity < 20000:
            liq_risk = "🟠 Low liquidity"
        elif stable_liquidity < 100000:
            liq_risk = "🟡 Moderate liquidity"
        else:
            liq_risk = "🟢 Good liquidity"
        
        provider_risk = ""
        if lp_providers == 0:
            provider_risk = "💀 No LP providers"
        elif lp_providers < 2:
            provider_risk = "🔴 Very few providers"
        elif lp_providers < 5:
            provider_risk = "🟡 Few providers"
        else:
            provider_risk = "🟢 Multiple providers"
        
        liquidity_analysis = f"""
💰 Stable Liquidity: ${stable_liquidity:,.2f}
👥 LP Providers: {lp_providers}
💧 Liquidity Risk: {liq_risk}
🤝 Provider Risk: {provider_risk}"""
    
    # Additional risk factors
    insider_networks = rug_data.get('insider_networks', 0)
    jupiter_verified = rug_data.get('jupiter_verified', False)
    risk_factors = rug_data.get('risk_factors', [])
    
    additional_info = f"""
🕸️ Insider Networks: {insider_networks} detected
✅ Jupiter Verified: {'Yes' if jupiter_verified else 'No'}"""
    
    # Summary status
    if rug_probability >= 85:
        status = "💀 EXTREME RISK"
        summary = f"AVOID - {rug_probability:.1f}% rug probability"
    elif rug_probability >= 65:
        status = "🔴 VERY HIGH RISK"
        summary = f"HIGH RISK - {rug_probability:.1f}% rug probability"
    elif rug_probability >= 45:
        status = "🟠 HIGH RISK"
        summary = f"RISKY - {rug_probability:.1f}% rug probability"
    elif rug_probability >= 25:
        status = "🟡 MODERATE RISK"
        summary = f"MODERATE - {rug_probability:.1f}% rug probability"
    else:
        status = "🟢 LOWER RISK"
        summary = f"SAFER - {rug_probability:.1f}% rug probability"
    
    return {
        'status': status,
        'summary': summary,
        'rug_probability': rug_probability,
        'risk_score': risk_score,
        'risk_level': risk_level,
        'risk_emoji': risk_emoji,
        'security_issues': security_issues,
        'security_summary': " | ".join(security_issues),
        'holder_analysis': holder_analysis,
        'liquidity_analysis': liquidity_analysis,
        'additional_info': additional_info,
        'risk_factors': risk_factors[:8],  # Top 8 risk factors
        'detailed_analysis': f"{risk_emoji} {risk_level} ({rug_probability:.1f}% rug risk)"
    }

def format_rug_analysis_for_assessment(rug_data):
    """Format rug analysis data to integrate with existing assessment system"""
    if not rug_data or not rug_data.get('success'):
        return {
            'rug_status': 'Unknown',
            'rug_probability': 'N/A',
            'rug_risk_level': 'Unknown',
            'rug_security_summary': 'Rug check unavailable',
            'rug_holder_summary': 'N/A',
            'rug_liquidity_summary': 'N/A',
            'rug_key_risks': ['Rug analysis unavailable'],
            'rug_detailed_analysis': 'Security analysis unavailable'
        }
   
    # Extract rug probability and format
    rug_probability = rug_data.get('rug_probability', 0)
    rug_probability_display = f"{rug_probability}%" if rug_probability != 'N/A' else 'N/A'
    
    # Get risk level and emoji
    risk_level = rug_data.get('risk_level', 'Unknown')
    risk_emoji = rug_data.get('risk_emoji', '❓')
    
    # Status determination
    if rug_probability >= 85:
        status = f"{risk_emoji} EXTREME RUG RISK"
    elif rug_probability >= 65:
        status = f"{risk_emoji} VERY HIGH RISK"
    elif rug_probability >= 45:
        status = f"{risk_emoji} HIGH RISK"
    elif rug_probability >= 25:
        status = f"{risk_emoji} MODERATE RISK"
    else:
        status = f"{risk_emoji} LOWER RISK"
    
    # Security summary
    security_flags = rug_data.get('security_flags', {})
    security_issues = []
    
    if security_flags.get('rugged', False):
        security_issues.append('TOKEN IS RUGGED')
    if security_flags.get('mint_authority', False):
        security_issues.append('Mint Authority Active')
    if security_flags.get('freeze_authority', False):
        security_issues.append('Freeze Authority Active')
    if security_flags.get('transfer_fee_active', False):
        fee_pct = security_flags.get('transfer_fee_pct', 0)
        security_issues.append(f'Transfer Fee: {fee_pct}%')
    
    security_summary = ' | '.join(security_issues) if security_issues else 'No major security issues'
    
    # Holder summary
    holder_info = rug_data.get('holder_info', {})
    if holder_info:
        total_holders = holder_info.get('total_holders', 0)
        top_holder_pct = holder_info.get('top_holder_pct', 0)
        holder_summary = f"{total_holders:,} holders | Top holder: {top_holder_pct:.1f}%"
    else:
        holder_summary = 'Holder data unavailable'
    
    # Liquidity summary
    liquidity_info = rug_data.get('liquidity_info', {})
    if liquidity_info:
        stable_liquidity = liquidity_info.get('total_stable_usd', 0)
        lp_providers = liquidity_info.get('total_lp_providers', 0)
        liquidity_summary = f"${stable_liquidity:,.0f} liquidity | {lp_providers} LP providers"
    else:
        liquidity_summary = 'Liquidity data unavailable'
    
    # Key risk factors (top 3)
    risk_factors = rug_data.get('risk_factors', [])
    key_risks = risk_factors[:3] if risk_factors else ['No major risks detected']
    
    # Detailed analysis text
    insider_networks = rug_data.get('insider_networks', 0)
    jupiter_verified = rug_data.get('jupiter_verified', False)
    
    detailed_analysis = f"{status} ({rug_probability_display})"
    if insider_networks > 0:
        detailed_analysis += f" | {insider_networks} insider networks"
    if jupiter_verified:
        detailed_analysis += " | Jupiter verified"
    
    return {
        'rug_status': status,
        'rug_probability': rug_probability_display,
        'rug_risk_level': risk_level,
        'rug_security_summary': security_summary,
        'rug_holder_summary': holder_summary,
        'rug_liquidity_summary': liquidity_summary,
        'rug_key_risks': key_risks,
        'rug_detailed_analysis': detailed_analysis
    }
def safe_get_nested(data, *keys, default=None):
    """Safely get nested dictionary values"""
    for key in keys:
        if isinstance(data, dict) and key in data and data[key] is not None:
            data = data[key]
        else:
            return default
    return data

def safe_float(value, default=0.0):
    """Safely convert to float"""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


async def generate_analysis(token_address):
    """Enhanced analysis with integrated rug checking"""
    print("🔍 Starting comprehensive token analysis...")
    
    # Get pair address
    pair_address = get_token_pair_address(token_address)
    if not pair_address:
        return "Could not retrieve pair address."
    
    print("📊 Fetching market data...")
    # Fetch market data
    dex_data = fetch_dex_screener_data(pair_address)
    if not dex_data or 'pairs' not in dex_data or not dex_data['pairs']:
        return "Failed to retrieve pair data from DexScreener."
    
    pair_info = dex_data['pairs'][0]
    
    print("📈 Fetching OHLCV data...")
    # Fetch OHLCV data
    current_time = datetime.utcnow()
    from_date = datetime_to_timestamp(current_time - timedelta(hours=6))
    to_date = datetime_to_timestamp(current_time)
    ohlcv_data = fetch_ohlcv_data(pair_address, from_date, to_date, limit=100)

    if isinstance(ohlcv_data, str):
        return ohlcv_data

    if ohlcv_data is None or ohlcv_data.empty:
        return "This coin was just launched and has no trading data yet."
    
    print("🛡️ Running rug check analysis...")
    # Run rug check
    rug_data = await rug_checker.check_token_rug(token_address)
    
    # FORMAT RUG DATA FOR ASSESSMENT INTEGRATION
    formatted_rug = format_rug_analysis_for_assessment(rug_data)
    
    # Basic metrics
    name = pair_info['baseToken']['name']
    symbol = pair_info['baseToken']['symbol']
    token_address = pair_info['baseToken']['address']
    url = pair_info.get('url')
    
    # Price data
    latest_price = float(ohlcv_data['close'].iloc[-1])
    prev_price = float(ohlcv_data['close'].iloc[-2]) if len(ohlcv_data) > 1 else latest_price
    price = float(pair_info['priceUsd'])
    
    # Market data
    liquidity_data = pair_info.get('liquidity', {})
    if isinstance(liquidity_data, dict) and 'usd' in liquidity_data:
       liquidity = float(liquidity_data['usd'])
    else:
         liquidity = 0.0
    market_cap = safe_get_nested(pair_info, 'fdv')
    if market_cap and market_cap != 'N/A':
        market_cap = safe_float(market_cap)
    volume_24h = safe_float(safe_get_nested(pair_info, 'volume', 'h24'), 0.0)
    
    # Transaction data with safe access
    buy_tx = safe_get_nested(pair_info, 'txns', 'h24', 'buys', default=0)
    sell_tx = safe_get_nested(pair_info, 'txns', 'h24', 'sells', default=0)
    total_tx = buy_tx + sell_tx
    buy_sell_ratio = buy_tx / sell_tx if sell_tx > 0 else float('inf')

    # Technical analysis
    support_level = float(ohlcv_data['low'].min()) if not ohlcv_data.empty else None
    resistance_level = float(ohlcv_data['high'].max()) if not ohlcv_data.empty else None
    
    # Risk assessment
    volatility = ohlcv_data['close'].pct_change().std() * 100
    
    current_rsi = ohlcv_data['rsi'].iloc[-1] if 'rsi' in ohlcv_data.columns and not pd.isna(ohlcv_data['rsi'].iloc[-1]) else 50
    
    # Volume analysis
    volume_profile = analyze_volume_profile(ohlcv_data)
    
    # Momentum analysis
    momentum_score, momentum_desc = calculate_momentum_score(ohlcv_data)
    
    # Position sizing recommendation
    if volatility > 15:
        position_size = "SMALL (High Risk)"
    elif volatility > 8:
        position_size = "MEDIUM (Moderate Risk)"
    else:
        position_size = "LARGE (Lower Risk)"
    
    # Entry and exit levels
    if support_level and resistance_level and latest_price:
        price_position = (latest_price - support_level) / (resistance_level - support_level)
        
        if price_position < 0.3:
            entry_strategy = "Near Support - Good Entry"
        elif price_position > 0.7:
            entry_strategy = "Near Resistance - Wait for Breakout"
        else:
            entry_strategy = "Mid-Range - Wait for Clear Signal"
    else:
        entry_strategy = "📊 Insufficient Price History"
    
    # Get final verdict with rug data
    verdict, reasons, confidence_score = get_final_verdict(ohlcv_data, pair_info, rug_data)
    
    # Enhanced risk level assessment with rug data
    base_risk_factors = []
    if liquidity < 10000 or volume_24h < 5000 or volatility > 20:
        base_risk_factors.append("market")
    
    if rug_data and rug_data.get('success'):
        rug_probability = rug_data.get('rug_probability', 0)
        security_flags = rug_data.get('security_flags', {})
        
        if rug_probability >= 65 or (security_flags and any([
            security_flags.get('rugged', False),
            security_flags.get('mint_authority', False),
            security_flags.get('freeze_authority', False)
        ])):
            risk_level = "EXTREME RISK"
        elif rug_probability >= 45 or len(base_risk_factors) > 0:
            risk_level = "HIGH RISK"
        elif rug_probability >= 25:
            risk_level = "MEDIUM RISK"
        else:
            risk_level = "LOWER RISK"
    else:
        if len(base_risk_factors) > 0:
            risk_level = "HIGH RISK"
        else:
            risk_level = "LOWER RISK"

    print("✅ Analysis complete!")
    
    # Build comprehensive result WITH INTEGRATED RUG DATA
    result = {
        # Basic Info
        "token_name": safe_get_nested(pair_info, 'baseToken', 'name', default='Unknown'),
        "token_symbol": safe_get_nested(pair_info, 'baseToken', 'symbol', default='Unknown'),
        "token_address": safe_get_nested(pair_info, 'baseToken', 'address', default=token_address),
        "price": f"${safe_float(safe_get_nested(pair_info, 'priceUsd'), 0.0):.8f}",
        "price_change_24h": f"{((latest_price - prev_price) / prev_price * 100):.2f}%" if prev_price > 0 else "N/A",
        
        # Market Data - SAFE ACCESS
        "liquidity": human_format(liquidity) if liquidity > 0 else "N/A",
        "market_cap": human_format(market_cap) if market_cap and market_cap > 0 else "N/A",
        "volume_24h": human_format(volume_24h) if volume_24h > 0 else "N/A",
        "volatility": f"{volatility:.2f}%" if volatility and not pd.isna(volatility) else "N/A",
        
        # Trading Activity
        "buys_24h": buy_tx,
        "sells_24h": sell_tx,
        "total_trades_24h": total_tx,
        "buy_sell_ratio": f"{buy_sell_ratio:.2f}" if buy_sell_ratio != float('inf') else "∞",
        
        # Technical Analysis
        "support_level": f"${support_level:.8f}" if support_level else "N/A",
        "resistance_level": f"${resistance_level:.8f}" if resistance_level else "N/A",
        "rsi": f"{current_rsi:.1f}" if not pd.isna(current_rsi) else "N/A",
        "momentum": momentum_desc,
        "volume_profile": volume_profile,
        
        # Trading Recommendations
        "final_verdict": verdict,
        "confidence_score": f"{confidence_score:.0f}%" if confidence_score else "N/A",
        "risk_level": risk_level,
        "position_size": position_size,
        "entry_strategy": entry_strategy,
        "reasoning": reasons,
        
        # INTEGRATED RUG ANALYSIS DATA
        "rug_status": formatted_rug.get('rug_status', 'Unknown'),
        "rug_probability": formatted_rug.get('rug_probability', 'N/A'),
        "rug_risk_level": formatted_rug.get('rug_risk_level', 'Unknown'),
        
        # Links
        "dex_link": safe_get_nested(pair_info, 'url', default='N/A'),
    }
    
    return result


def format_analysis_output(analysis_result):
    """Enhanced format with detailed rug analysis"""
    if isinstance(analysis_result, str):
        return analysis_result
    
    detailed_rug = analysis_result.get('detailed_rug', {})
    
    output = f"""
📊 TOKEN ANALYSIS
🪙 {analysis_result['token_name']} ({analysis_result['token_symbol']})
{analysis_result['token_address']}

💰 Price Data
Current: {analysis_result['price']}
24h Change: {analysis_result['price_change_24h']}
Market Cap: {analysis_result['market_cap']}
Liquidity: {analysis_result['liquidity']}

📈 Trading Activity
Volume 24h: {analysis_result['volume_24h']}
Buys: {analysis_result['buys_24h']} | Sells: {analysis_result['sells_24h']}
Buy/Sell Ratio: {analysis_result['buy_sell_ratio']}
Total Trades: {analysis_result['total_trades_24h']}

🎯 Technical Indicators
RSI: {analysis_result['rsi']}
Momentum: {analysis_result['momentum']}
Volume Profile: {analysis_result['volume_profile']}
Volatility: {analysis_result['volatility']}

📊 Key Levels
Support: {analysis_result['support_level']}
Resistance: {analysis_result['resistance_level']}

📋 Assessment
Confidence: {analysis_result['confidence_score']}
Risk Level: {analysis_result['rug_risk_level']}
Position Size: {analysis_result['position_size']}
Rug Risk: {analysis_result['rug_probability']}
Rug Status: {analysis_result['rug_status']}

⚡️ FINAL VERDICT
 {analysis_result['final_verdict']} 

🎯 Entry Strategy
{analysis_result['entry_strategy']}

💭 Analysis Summary
{analysis_result['reasoning']}

📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC
⏱️ Next analysis available in 20 seconds
🔗 View Chart ({analysis_result.get('dex_link', 'N/A')})
"""
    
    output += "\n⚠️ DISCLAIMER: This is not financial advice. Always DYOR before investing."
    
    return output

import asyncio

async def main():
    token_address = input("Enter the token address (Solana): ")
    print(f"\n🚀 Analyzing token: {token_address}")
    print("This may take a moment as we fetch data from multiple sources...\n")
    
    analysis = await generate_analysis(token_address)
    
    # Format and display the result
    formatted_output = format_analysis_output(analysis)
    print(formatted_output)
    
    # Also create escaped version for Telegram if needed
    if isinstance(analysis, dict):
        try:
            escaped_message = escape_markdown(formatted_output, version=2)
            print("\n" + "="*50)
            print("TELEGRAM-READY OUTPUT (MarkdownV2 Escaped):")
            print("="*50)
            print(escaped_message)
        except Exception as e:
            print(f"\n⚠️ Could not create Telegram-escaped version: {e}")

if __name__ == "__main__":
    asyncio.run(main())
