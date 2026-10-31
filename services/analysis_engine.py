"""
Technical analysis engine for token analysis
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, Any, Tuple
from config.settings import (
    LOOKBACK_PERIODS, HIGH_VOLATILITY, MODERATE_VOLATILITY,
    LOW_LIQUIDITY, HIGH_LIQUIDITY, EXTREMELY_LOW_LIQUIDITY,
    HIGH_VOLUME, LOW_VOLUME, RSI_OVERSOLD_THRESHOLD, RSI_OVERBOUGHT_THRESHOLD,
    RSI_APPROACHING_OVERBOUGHT, RSI_APPROACHING_OVERSOLD
)
from utils.helpers import (
    calculate_dynamic_thresholds, analyze_volume_profile, calculate_momentum_score,
    safe_float, safe_get_nested
)
from config.logging_config import get_logger

logger = get_logger(__name__)

class TechnicalAnalysisEngine:
    """Engine for technical analysis calculations"""
    
    def __init__(self):
        self.lookback_periods = LOOKBACK_PERIODS
    
    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to OHLCV data"""
        try:
            if df.empty or len(df) < 20:
                logger.warning("Insufficient data for technical indicators")
                return df
            
            # Exponential Moving Averages
            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
            
            # MACD
            df['macd'] = df['ema_12'] - df['ema_26']
            df['signal_line'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_histogram'] = df['macd'] - df['signal_line']
            
            # Simple Moving Average and Bollinger Bands
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['std_20'] = df['close'].rolling(window=20).std()
            df['bollinger_upper'] = df['sma_20'] + (df['std_20'] * 2)
            df['bollinger_lower'] = df['sma_20'] - (df['std_20'] * 2)
            
            # RSI
            delta = df['close'].diff(1)
            gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
            
            rs = gain / loss.replace(0, np.nan)
            df['rsi'] = 100 - (100 / (1 + rs))
            
            # Average True Range (ATR)
            df['tr1'] = df['high'] - df['low']
            df['tr2'] = abs(df['high'] - df['close'].shift(1))
            df['tr3'] = abs(df['low'] - df['close'].shift(1))
            df['true_range'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
            df['atr'] = df['true_range'].rolling(window=14).mean()
            
            # Volume indicators
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
            
            logger.info("Technical indicators added successfully")
            return df
            
        except Exception as e:
            logger.error(f"Error adding technical indicators: {e}")
            return df
    
    def add_technical_indicators_memory_efficient(self, df: pd.DataFrame) -> pd.DataFrame:
        """Memory-efficient technical indicators for t2.micro"""
        try:
            if df.empty or len(df) < 20:
                logger.warning("Insufficient data for technical indicators")
                return df
            
            # Process in smaller chunks to save memory
            chunk_size = min(50, len(df))  # Process max 50 rows at a time
            result_df = df.copy()
            
            for i in range(0, len(df), chunk_size):
                end_idx = min(i + chunk_size, len(df))
                chunk = df.iloc[i:end_idx].copy()
                
                # Add indicators to chunk
                chunk = self._add_indicators_to_chunk(chunk)
                
                # Update result dataframe
                result_df.iloc[i:end_idx] = chunk
                
                # Force garbage collection after each chunk
                del chunk
                import gc
                gc.collect()
            
            logger.info("Memory-efficient technical indicators added successfully")
            return result_df
            
        except Exception as e:
            logger.error(f"Error adding memory-efficient technical indicators: {e}")
            return df
    
    def _add_indicators_to_chunk(self, chunk: pd.DataFrame) -> pd.DataFrame:
        """Add indicators to a single chunk to save memory"""
        try:
            # Exponential Moving Averages (memory efficient)
            chunk['ema_12'] = chunk['close'].ewm(span=12, adjust=False).mean()
            chunk['ema_26'] = chunk['close'].ewm(span=26, adjust=False).mean()
            
            # MACD
            chunk['macd'] = chunk['ema_12'] - chunk['ema_26']
            chunk['signal_line'] = chunk['macd'].ewm(span=9, adjust=False).mean()
            chunk['macd_histogram'] = chunk['macd'] - chunk['signal_line']
            
            # Simple Moving Average and Bollinger Bands
            chunk['sma_20'] = chunk['close'].rolling(window=min(20, len(chunk))).mean()
            chunk['std_20'] = chunk['close'].rolling(window=min(20, len(chunk))).std()
            chunk['bollinger_upper'] = chunk['sma_20'] + (chunk['std_20'] * 2)
            chunk['bollinger_lower'] = chunk['sma_20'] - (chunk['std_20'] * 2)
            
            # RSI (simplified for memory)
            if len(chunk) >= 14:
                delta = chunk['close'].diff(1)
                gain = delta.where(delta > 0, 0).rolling(window=14, min_periods=1).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14, min_periods=1).mean()
                rs = gain / loss.replace(0, 1)  # Avoid division by zero
                chunk['rsi'] = 100 - (100 / (1 + rs))
            
            # Volume indicators (simplified)
            chunk['volume_ma'] = chunk['volume'].rolling(window=min(20, len(chunk))).mean()
            chunk['volume_ratio'] = chunk['volume'] / chunk['volume_ma'].replace(0, 1)
            
            return chunk
            
        except Exception as e:
            logger.error(f"Error adding indicators to chunk: {e}")
            return chunk
    
    def calculate_volatility(self, ohlcv_data: pd.DataFrame) -> Optional[float]:
        """Calculate price volatility"""
        try:
            if ohlcv_data.empty or len(ohlcv_data) < 2:
                return None
            
            price_changes = ohlcv_data['close'].pct_change().dropna()
            if len(price_changes) == 0:
                return None
            
            volatility = price_changes.std() * 100
            return float(volatility)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {e}")
            return None
    
    def get_support_resistance_levels(self, ohlcv_data: pd.DataFrame) -> Tuple[Optional[float], Optional[float]]:
        """Get support and resistance levels"""
        try:
            if ohlcv_data.empty:
                return None, None
            
            support_level = float(ohlcv_data['low'].min())
            resistance_level = float(ohlcv_data['high'].max())
            
            return support_level, resistance_level
            
        except Exception as e:
            logger.error(f"Error getting support/resistance levels: {e}")
            return None, None
    
    def analyze_price_position(self, current_price: float, support: float, resistance: float) -> str:
        """Analyze current price position relative to support/resistance"""
        try:
            if not all([current_price, support, resistance]):
                return "📊 Insufficient Price History"
            
            price_position = (current_price - support) / (resistance - support)
            
            if price_position < 0.3:
                return "Near Support - Good Entry"
            elif price_position > 0.7:
                return "Near Resistance - Wait for Breakout"
            else:
                return "Mid-Range - Wait for Clear Signal"
                
        except Exception as e:
            logger.error(f"Error analyzing price position: {e}")
            return "📊 Analysis Error"
    
    def get_position_size_recommendation(self, volatility: float) -> str:
        """Get position size recommendation based on volatility"""
        try:
            if volatility > HIGH_VOLATILITY:
                return "SMALL (High Risk)"
            elif volatility > MODERATE_VOLATILITY:
                return "MEDIUM (Moderate Risk)"
            else:
                return "LARGE (Lower Risk)"
                
        except Exception as e:
            logger.error(f"Error getting position size recommendation: {e}")
            return "Unknown"
    
    def analyze_market_structure(self, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market structure and liquidity"""
        try:
            liquidity = safe_float(safe_get_nested(pair_info, 'liquidity', 'usd'), 0.0)
            volume_24h = safe_float(safe_get_nested(pair_info, 'volume', 'h24'), 0.0)
            
            # Liquidity analysis
            liquidity_risk = "Unknown"
            if liquidity < EXTREMELY_LOW_LIQUIDITY:
                liquidity_risk = "Extremely low liquidity, high manipulation risk"
            elif liquidity < LOW_LIQUIDITY:
                liquidity_risk = "Low liquidity, proceed with caution"
            elif liquidity > HIGH_LIQUIDITY:
                liquidity_risk = "Good liquidity providing safer trading"
            
            # Volume analysis
            volume_risk = "Unknown"
            if volume_24h < LOW_VOLUME:
                volume_risk = "Very low trading volume"
            elif volume_24h > HIGH_VOLUME:
                volume_risk = "High trading volume indicating active market"
            
            return {
                'liquidity': liquidity,
                'volume_24h': volume_24h,
                'liquidity_risk': liquidity_risk,
                'volume_risk': volume_risk
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market structure: {e}")
            return {}
    
    def get_final_verdict(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any], rug_data: Optional[Dict[str, Any]] = None) -> Tuple[str, str, float]:
        """Get final trading verdict with comprehensive analysis - OPTIMIZED FOR MEME COINS"""
        try:
            score = 0
            reasons = []
            
            latest_price = float(ohlcv_data['close'].iloc[-1])
            prev_price = float(ohlcv_data['close'].iloc[-2]) if len(ohlcv_data) > 1 else latest_price
            
            # MEME COIN SPECIFIC ANALYSIS
            meme_analysis = self.analyze_meme_coin_patterns(ohlcv_data, pair_info)
            if meme_analysis:
                # Pump detection bonus
                if meme_analysis.get('is_pumping', False):
                    score += 8
                    reasons.append("🚀 MEME COIN PUMP DETECTED - Strong momentum")
                
                # Volume surge analysis
                volume_surge_level = meme_analysis.get('volume_surge_level', 'NORMAL VOLUME')
                if 'EXTREME SURGE' in volume_surge_level:
                    score += 6
                    reasons.append("💥 EXTREME volume surge - Viral potential")
                elif 'MASSIVE SURGE' in volume_surge_level:
                    score += 4
                    reasons.append("🔥 Massive volume surge - Growing interest")
                elif 'HIGH SURGE' in volume_surge_level:
                    score += 2
                    reasons.append("📈 High volume surge - Momentum building")
                
                # Parabolic move detection
                if meme_analysis.get('is_parabolic', False):
                    score += 5
                    reasons.append("📊 Parabolic price action - Exponential growth")
                
                # Meme coin risk assessment
                meme_risk = meme_analysis.get('meme_coin_risk', {})
                if meme_risk:
                    risk_score = meme_risk.get('risk_score', 0)
                    if risk_score >= 80:
                        score -= 15
                        reasons.append("⚠️ EXTREME meme coin risk - High manipulation")
                    elif risk_score >= 60:
                        score -= 10
                        reasons.append("⚠️ Very high meme coin risk - Caution required")
                    elif risk_score >= 40:
                        score -= 5
                        reasons.append("⚠️ High meme coin risk - Proceed carefully")
            
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
            
            if rsi_current < RSI_OVERSOLD_THRESHOLD:
                score += 3
                reasons.append("Extremely oversold conditions (RSI < 25)")
            elif rsi_current < RSI_APPROACHING_OVERSOLD:
                score += 2
                reasons.append("Oversold conditions, potential reversal")
            elif rsi_current > RSI_OVERBOUGHT_THRESHOLD:
                score -= 2
                reasons.append("Overbought conditions, potential correction")
            elif rsi_current > RSI_APPROACHING_OVERBOUGHT:
                score -= 1
                reasons.append("Approaching overbought levels")
            
            # Liquidity and market structure
            market_analysis = self.analyze_market_structure(pair_info)
            liquidity = market_analysis.get('liquidity', 0)
            volume_24h = market_analysis.get('volume_24h', 0)
            
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
            
        except Exception as e:
            logger.error(f"Error getting final verdict: {e}")
            return "ERROR", f"Analysis error: {str(e)}", 0
    
    def get_risk_level_assessment(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any], rug_data: Optional[Dict[str, Any]] = None) -> str:
        """Get comprehensive risk level assessment"""
        try:
            base_risk_factors = []
            
            # Market risk factors
            market_analysis = self.analyze_market_structure(pair_info)
            liquidity = market_analysis.get('liquidity', 0)
            volume_24h = market_analysis.get('volume_24h', 0)
            volatility = self.calculate_volatility(ohlcv_data)
            
            if liquidity < 10000 or volume_24h < 5000 or (volatility and volatility > 20):
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
            
            return risk_level
            
        except Exception as e:
            logger.error(f"Error getting risk level assessment: {e}")
            return "UNKNOWN RISK"
    
    def analyze_volume_profile(self, ohlcv_data: pd.DataFrame) -> str:
        """Analyze volume profile and return description"""
        try:
            if ohlcv_data.empty or len(ohlcv_data) < 10:
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
                
        except Exception as e:
            logger.error(f"Error analyzing volume profile: {e}")
            return "Volume analysis failed"
    
    def calculate_momentum_score(self, ohlcv_data: pd.DataFrame) -> Tuple[float, str]:
        """Calculate momentum score and return description"""
        try:
            if ohlcv_data.empty or len(ohlcv_data) < 20:
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
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 0, "Momentum analysis failed"
    
    def get_position_size_recommendation(self, volatility: float) -> str:
        """Get position size recommendation based on volatility"""
        try:
            if volatility >= 50:
                return "Very Small (1-2% of portfolio)"
            elif volatility >= 30:
                return "Small (2-5% of portfolio)"
            elif volatility >= 15:
                return "Medium (5-10% of portfolio)"
            else:
                return "Normal (10-15% of portfolio)"
                
        except Exception as e:
            logger.error(f"Error getting position size recommendation: {e}")
            return "Consult financial advisor"
    
    def analyze_price_position(self, current_price: float, support: Optional[float], resistance: Optional[float]) -> str:
        """Analyze current price position relative to support/resistance"""
        try:
            if not support or not resistance:
                return "Insufficient data for position analysis"
            
            if support == resistance:
                return "Price at equilibrium level"
            
            position = (current_price - support) / (resistance - support)
            
            if position <= 0.2:
                return "Near support - potential entry point"
            elif position <= 0.4:
                return "Below midpoint - favorable entry"
            elif position <= 0.6:
                return "Mid-range - neutral entry"
            elif position <= 0.8:
                return "Above midpoint - cautious entry"
            else:
                return "Near resistance - wait for pullback"
                
        except Exception as e:
            logger.error(f"Error analyzing price position: {e}")
            return "Position analysis unavailable"
    
    def analyze_meme_coin_patterns(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze patterns specific to meme coins"""
        try:
            if ohlcv_data.empty:
                return {}
            
            analysis = {}
            
            # 1. Pump Detection
            price_changes = ohlcv_data['close'].pct_change()
            recent_changes = price_changes.tail(5)  # Last 5 periods
            
            # Detect exponential growth (meme coin characteristic)
            if len(recent_changes) >= 3:
                growth_acceleration = recent_changes.tail(3).mean() - recent_changes.head(2).mean()
                analysis['growth_acceleration'] = growth_acceleration
                analysis['is_pumping'] = growth_acceleration > 0.1  # 10%+ acceleration
            
            # 2. Volume Analysis for Meme Coins
            volume_data = ohlcv_data['volume']
            recent_volume = volume_data.tail(3).mean()
            avg_volume = volume_data.mean()
            
            volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
            analysis['volume_surge'] = volume_surge
            analysis['volume_surge_level'] = self._classify_volume_surge(volume_surge)
            
            # 3. Volatility Analysis (meme coins are highly volatile)
            volatility = self.calculate_volatility(ohlcv_data)
            analysis['volatility'] = volatility
            analysis['volatility_level'] = self._classify_volatility(volatility)
            
            # 4. Price Action Patterns
            if len(ohlcv_data) >= 10:
                # Detect parabolic moves (common in meme coins)
                recent_prices = ohlcv_data['close'].tail(10)
                price_acceleration = self._calculate_price_acceleration(recent_prices)
                analysis['price_acceleration'] = price_acceleration
                analysis['is_parabolic'] = price_acceleration > 0.15  # 15%+ daily acceleration
            
            # 5. Meme Coin Risk Factors
            analysis['meme_coin_risk'] = self._assess_meme_coin_risk(ohlcv_data, pair_info)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing meme coin patterns: {e}")
            return {}
    
    def _classify_volume_surge(self, volume_surge: float) -> str:
        """Classify volume surge levels for meme coins"""
        if volume_surge >= 10:
            return "EXTREME SURGE"  # 10x+ volume
        elif volume_surge >= 5:
            return "MASSIVE SURGE"   # 5x+ volume
        elif volume_surge >= 3:
            return "HIGH SURGE"      # 3x+ volume
        elif volume_surge >= 2:
            return "MODERATE SURGE"  # 2x+ volume
        else:
            return "NORMAL VOLUME"
    
    def _classify_volatility(self, volatility: Optional[float]) -> str:
        """Classify volatility levels for meme coins"""
        if not volatility:
            return "UNKNOWN"
        
        if volatility >= 50:
            return "EXTREME"      # 50%+ daily swings
        elif volatility >= 30:
            return "VERY HIGH"    # 30%+ daily swings
        elif volatility >= 20:
            return "HIGH"         # 20%+ daily swings
        elif volatility >= 10:
            return "MODERATE"     # 10%+ daily swings
        else:
            return "LOW"
    
    def _calculate_price_acceleration(self, prices: pd.Series) -> float:
        """Calculate price acceleration (rate of change of rate of change)"""
        try:
            if len(prices) < 3:
                return 0.0
            
            # First derivative (price changes)
            price_changes = prices.pct_change().dropna()
            
            # Second derivative (acceleration)
            if len(price_changes) >= 2:
                acceleration = price_changes.diff().mean()
                return float(acceleration)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating price acceleration: {e}")
            return 0.0
    
    def _assess_meme_coin_risk(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """Assess specific risks for meme coins"""
        risk_factors = []
        risk_score = 0
        
        try:
            # 1. Extreme volatility risk
            volatility = self.calculate_volatility(ohlcv_data)
            if volatility and volatility > 40:
                risk_factors.append("Extreme volatility (>40% daily swings)")
                risk_score += 25
            
            # 2. Volume manipulation risk
            volume_data = ohlcv_data['volume']
            if len(volume_data) >= 5:
                recent_volume = volume_data.tail(3).mean()
                avg_volume = volume_data.mean()
                if recent_volume > avg_volume * 5:
                    risk_factors.append("Suspicious volume surge (possible manipulation)")
                    risk_score += 20
            
            # 3. Price manipulation risk
            if len(ohlcv_data) >= 10:
                recent_prices = ohlcv_data['close'].tail(10)
                price_volatility = recent_prices.pct_change().std() * 100
                if price_volatility > 30:
                    risk_factors.append("High price volatility (manipulation risk)")
                    risk_score += 15
            
            # 4. Liquidity risk
            liquidity = safe_float(safe_get_nested(pair_info, 'liquidity', 'usd'), 0)
            if liquidity < 10000:
                risk_factors.append("Very low liquidity (high manipulation risk)")
                risk_score += 30
            
            # 5. Market cap risk
            market_cap = safe_float(safe_get_nested(pair_info, 'fdv'), 0)
            if market_cap > 10000000:  # 10M+ market cap for meme coin
                risk_factors.append("High market cap for meme coin (limited upside)")
                risk_score += 10
            
            return {
                'risk_score': min(risk_score, 100),
                'risk_level': self._get_risk_level(risk_score),
                'risk_factors': risk_factors,
                'total_factors': len(risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Error assessing meme coin risk: {e}")
            return {'risk_score': 50, 'risk_level': 'UNKNOWN', 'risk_factors': [], 'total_factors': 0}
    
    def _get_risk_level(self, risk_score: int) -> str:
        """Get risk level based on score"""
        if risk_score >= 80:
            return "EXTREME RISK"
        elif risk_score >= 60:
            return "VERY HIGH RISK"
        elif risk_score >= 40:
            return "HIGH RISK"
        elif risk_score >= 20:
            return "MODERATE RISK"
        else:
            return "LOWER RISK"

    def analyze_meme_coin_patterns_memory_efficient(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """Memory-efficient meme coin pattern analysis for t2.micro"""
        try:
            if ohlcv_data.empty:
                return {}
            
            analysis = {}
            
            # Process in smaller chunks to save memory
            chunk_size = min(20, len(ohlcv_data))
            
            # 1. Pump Detection (chunked)
            price_changes = ohlcv_data['close'].pct_change()
            recent_changes = price_changes.tail(min(5, len(price_changes)))
            
            if len(recent_changes) >= 3:
                growth_acceleration = recent_changes.tail(3).mean() - recent_changes.head(2).mean()
                analysis['growth_acceleration'] = float(growth_acceleration)
                analysis['is_pumping'] = growth_acceleration > 0.1
            
            # 2. Volume Analysis (chunked)
            volume_data = ohlcv_data['volume']
            recent_volume = volume_data.tail(min(3, len(volume_data))).mean()
            avg_volume = volume_data.mean()
            
            volume_surge = recent_volume / avg_volume if avg_volume > 0 else 1
            analysis['volume_surge'] = float(volume_surge)
            analysis['volume_surge_level'] = self._classify_volume_surge(volume_surge)
            
            # 3. Volatility Analysis (simplified)
            if len(ohlcv_data) >= 10:
                sample_data = ohlcv_data.tail(10)  # Use only last 10 rows
                volatility = self.calculate_volatility(sample_data)
                analysis['volatility'] = volatility
                analysis['volatility_level'] = self._classify_volatility(volatility)
            
            # 4. Price Action Patterns (chunked)
            if len(ohlcv_data) >= 10:
                recent_prices = ohlcv_data['close'].tail(10)
                price_acceleration = self._calculate_price_acceleration_memory_efficient(recent_prices)
                analysis['price_acceleration'] = price_acceleration
                analysis['is_parabolic'] = price_acceleration > 0.15
            
            # 5. Meme Coin Risk Factors (simplified)
            analysis['meme_coin_risk'] = self._assess_meme_coin_risk_memory_efficient(ohlcv_data, pair_info)
            
            # Force garbage collection
            import gc
            gc.collect()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error in memory-efficient meme coin analysis: {e}")
            return {}
    
    def _calculate_price_acceleration_memory_efficient(self, prices: pd.Series) -> float:
        """Memory-efficient price acceleration calculation"""
        try:
            if len(prices) < 3:
                return 0.0
            
            # Use numpy for memory efficiency
            import numpy as np
            price_array = np.array(prices)
            price_changes = np.diff(price_array) / price_array[:-1]
            
            if len(price_changes) >= 2:
                acceleration = np.diff(price_changes).mean()
                return float(acceleration)
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Error calculating memory-efficient price acceleration: {e}")
            return 0.0
    
    def _assess_meme_coin_risk_memory_efficient(self, ohlcv_data: pd.DataFrame, pair_info: Dict[str, Any]) -> Dict[str, Any]:
        """Memory-efficient meme coin risk assessment"""
        risk_factors = []
        risk_score = 0
        
        try:
            # Use only essential data for risk assessment
            if len(ohlcv_data) >= 10:
                sample_data = ohlcv_data.tail(10)
                
                # 1. Volatility risk (simplified)
                volatility = self.calculate_volatility(sample_data)
                if volatility and volatility > 40:
                    risk_factors.append("Extreme volatility")
                    risk_score += 25
                
                # 2. Volume manipulation risk (simplified)
                volume_data = sample_data['volume']
                if len(volume_data) >= 3:
                    recent_volume = volume_data.tail(3).mean()
                    avg_volume = volume_data.mean()
                    if recent_volume > avg_volume * 5:
                        risk_factors.append("Suspicious volume surge")
                        risk_score += 20
            
            # 3. Liquidity risk (from pair info only)
            liquidity = safe_float(safe_get_nested(pair_info, 'liquidity', 'usd'), 0)
            if liquidity < 10000:
                risk_factors.append("Very low liquidity")
                risk_score += 30
            
            return {
                'risk_score': min(risk_score, 100),
                'risk_level': self._get_risk_level(risk_score),
                'risk_factors': risk_factors,
                'total_factors': len(risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Error in memory-efficient risk assessment: {e}")
            return {'risk_score': 50, 'risk_level': 'UNKNOWN', 'risk_factors': [], 'total_factors': 0}

# Create global instance
analysis_engine = TechnicalAnalysisEngine()
