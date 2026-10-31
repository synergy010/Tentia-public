"""
Main analysis service that orchestrates token analysis
"""

import asyncio
import pandas as pd
from typing import Optional, Dict, Any, Union
from datetime import datetime
from config.settings import ANALYSIS_TIMEOUT
from services.data_fetcher import data_fetcher
from services.analysis_engine import analysis_engine
from services.rug_checker import rug_checker_service
from concurrent_processing.worker_pool import concurrent_processor
from concurrent_processing.rate_limiter import rate_limit_manager
from models.token_data import AnalysisResult, TokenInfo, PriceData, MarketData, TradingActivity
from models.token_data import TechnicalIndicators, KeyLevels, VolumeProfile, MomentumData
from models.token_data import RiskAssessment, RugAnalysis, TradingRecommendation
from utils.helpers import safe_float, safe_get_nested, human_format
from config.logging_config import get_logger

logger = get_logger(__name__)

class TokenAnalysisService:
    """Main service for token analysis"""
    
    def __init__(self):
        self.data_fetcher = data_fetcher
        self.analysis_engine = analysis_engine
        self.rug_checker = rug_checker_service
        self.concurrent_processor = concurrent_processor
        self.rate_limit_manager = rate_limit_manager
    
    async def analyze_token(self, token_address: str, user_id: int) -> Union[AnalysisResult, str]:
        """
        Analyze a token with comprehensive analysis
        
        Args:
            token_address: Solana token address
            user_id: Telegram user ID for rate limiting
            
        Returns:
            AnalysisResult object or error string
        """
        try:
            logger.info(f"Starting analysis for token {token_address} by user {user_id}")
            
            # Check rate limit
            can_analyze, remaining_time = self.rate_limit_manager.check_analysis_limit(user_id)
            if not can_analyze:
                logger.warning(f"Rate limit hit for user {user_id}, {remaining_time}s remaining")
                return f"Rate limit active. Next analysis available in {int(remaining_time)} seconds."
            
            # Record the request
            self.rate_limit_manager.record_analysis(user_id)
            
            # Get market data
            market_data = self.data_fetcher.get_token_market_data(token_address)
            if not market_data or not market_data.get('success'):
                error_msg = market_data.get('error', 'Failed to retrieve market data') if market_data else 'Failed to retrieve market data'
                logger.error(f"Market data retrieval failed for {token_address}: {error_msg}")
                return "Unable to retrieve market data for this token. It may be too new or not yet listed on major exchanges."
            
            pair_address = market_data['pair_address']
            pair_info = market_data['pair_info']
            ohlcv_data = market_data['ohlcv_data']
            
            if ohlcv_data is None or ohlcv_data.empty:
                return "This coin was just launched and has no trading data yet."
            
            # Add technical indicators (memory-efficient for t2.micro)
            ohlcv_data = self.analysis_engine.add_technical_indicators_memory_efficient(ohlcv_data)
            
            # Force garbage collection after heavy operations
            import gc
            gc.collect()
            
            # Run rug check in parallel
            rug_check_task = asyncio.create_task(
                self.rug_checker.check_token(token_address)
            )
            
            # Process market data
            token_info = self._extract_token_info(pair_info)
            price_data = self._extract_price_data(pair_info, ohlcv_data)
            market_data_obj = self._extract_market_data(pair_info)
            trading_activity = self._extract_trading_activity(pair_info)
            
            # Technical analysis
            technical_indicators = self._extract_technical_indicators(ohlcv_data)
            key_levels = self._extract_key_levels(ohlcv_data)
            volume_profile = self._extract_volume_profile(ohlcv_data)
            momentum_data = self._extract_momentum_data(ohlcv_data)
            
            # MEME COIN SPECIFIC ANALYSIS (memory-efficient for t2.micro)
            meme_coin_analysis = self.analysis_engine.analyze_meme_coin_patterns_memory_efficient(ohlcv_data, pair_info)
            self._meme_coin_analysis = meme_coin_analysis  # Store for later use
            
            # Force garbage collection after meme coin analysis
            gc.collect()
            
            # Wait for rug check
            try:
                rug_data = await asyncio.wait_for(rug_check_task, timeout=ANALYSIS_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(f"Rug check timeout for {token_address}")
                rug_data = {'success': False, 'error': 'Rug check timeout'}
            
            # Risk assessment
            risk_assessment = self._create_risk_assessment(ohlcv_data, pair_info, rug_data)
            rug_analysis = self._create_rug_analysis(rug_data)
            
            # Trading recommendations
            trading_recommendation = self._create_trading_recommendation(
                ohlcv_data, pair_info, rug_data, key_levels
            )
            
            # Update confidence score with final verdict confidence
            # Use the confidence score from the trading recommendation calculation
            if hasattr(self, '_last_confidence_score'):
                risk_assessment.confidence_score = self._last_confidence_score
                logger.debug(f"Updated confidence score to: {self._last_confidence_score}")
            else:
                logger.warning("No confidence score available from final verdict")
                # Keep the default confidence score from risk assessment
            
            # Create final result
            analysis_result = AnalysisResult(
                token_info=token_info,
                price_data=price_data,
                market_data=market_data_obj,
                trading_activity=trading_activity,
                technical_indicators=technical_indicators,
                key_levels=key_levels,
                volume_profile=volume_profile,
                momentum_data=momentum_data,
                risk_assessment=risk_assessment,
                rug_analysis=rug_analysis,
                trading_recommendation=trading_recommendation,
                pair_address=pair_address,
                dex_link=pair_info.get('url'),
                raw_data={
                    'pair_info': pair_info,
                    'ohlcv_data': ohlcv_data,
                    'rug_data': rug_data
                }
            )
            
            logger.info(f"Analysis completed successfully for {token_address}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            # Reset rate limit on error to be user-friendly
            self.rate_limit_manager.reset_user_limits(user_id)
            # Return user-friendly message instead of technical error
            return "Analysis failed due to technical issues. Please try again with a different token or contact support if the problem persists."
    
    def _extract_token_info(self, pair_info: Dict[str, Any]) -> TokenInfo:
        """Extract basic token information"""
        base_token = pair_info.get('baseToken', {})
        return TokenInfo(
            address=base_token.get('address', 'Unknown'),
            name=base_token.get('name', 'Unknown'),
            symbol=base_token.get('symbol', 'Unknown'),
            decimals=base_token.get('decimals'),
            supply=base_token.get('supply')
        )
    
    def _extract_price_data(self, pair_info: Dict[str, Any], ohlcv_data) -> PriceData:
        """Extract price information"""
        current_price = float(pair_info.get('priceUsd', 0))
        
        # Calculate 24h change
        price_change_24h = None
        price_change_percent = None
        
        if not ohlcv_data.empty and len(ohlcv_data) > 1:
            latest_price = float(ohlcv_data['close'].iloc[-1])
            prev_price = float(ohlcv_data['close'].iloc[-2])
            if prev_price > 0:
                price_change_24h = latest_price - prev_price
                price_change_percent = (price_change_24h / prev_price) * 100
        
        return PriceData(
            current_price=current_price,
            price_change_24h=price_change_24h,
            price_change_percent=price_change_percent,
            high_24h=float(ohlcv_data['high'].max()) if not ohlcv_data.empty else None,
            low_24h=float(ohlcv_data['low'].min()) if not ohlcv_data.empty else None
        )
    
    def _extract_market_data(self, pair_info: Dict[str, Any]) -> MarketData:
        """Extract market data"""
        liquidity_data = pair_info.get('liquidity', {})
        liquidity_usd = safe_float(safe_get_nested(liquidity_data, 'usd'), 0.0)
        
        return MarketData(
            market_cap=safe_float(safe_get_nested(pair_info, 'fdv'), 0.0),
            liquidity_usd=liquidity_usd,
            volume_24h=safe_float(safe_get_nested(pair_info, 'volume', 'h24'), 0.0),
            fdv=safe_float(safe_get_nested(pair_info, 'fdv'), 0.0),
            total_supply=pair_info.get('baseToken', {}).get('supply')
        )
    
    def _extract_trading_activity(self, pair_info: Dict[str, Any]) -> TradingActivity:
        """Extract trading activity data"""
        buy_tx = safe_get_nested(pair_info, 'txns', 'h24', 'buys', default=0)
        sell_tx = safe_get_nested(pair_info, 'txns', 'h24', 'sells', default=0)
        total_tx = buy_tx + sell_tx
        buy_sell_ratio = buy_tx / sell_tx if sell_tx > 0 else None
        
        return TradingActivity(
            buys_24h=buy_tx,
            sells_24h=sell_tx,
            total_trades_24h=total_tx,
            buy_sell_ratio=buy_sell_ratio
        )
    
    def _extract_technical_indicators(self, ohlcv_data) -> TechnicalIndicators:
        """Extract technical indicators"""
        if ohlcv_data.empty:
            return TechnicalIndicators()
        
        latest = ohlcv_data.iloc[-1]
        
        return TechnicalIndicators(
            rsi=float(latest.get('rsi', 50)) if 'rsi' in latest and not pd.isna(latest['rsi']) else None,
            macd=float(latest.get('macd', 0)) if 'macd' in latest and not pd.isna(latest['macd']) else None,
            macd_signal=float(latest.get('signal_line', 0)) if 'signal_line' in latest and not pd.isna(latest['signal_line']) else None,
            macd_histogram=float(latest.get('macd_histogram', 0)) if 'macd_histogram' in latest and not pd.isna(latest['macd_histogram']) else None,
            ema_12=float(latest.get('ema_12', 0)) if 'ema_12' in latest and not pd.isna(latest['ema_12']) else None,
            ema_26=float(latest.get('ema_26', 0)) if 'ema_26' in latest and not pd.isna(latest['ema_26']) else None,
            sma_20=float(latest.get('sma_20', 0)) if 'sma_20' in latest and not pd.isna(latest['sma_20']) else None,
            bollinger_upper=float(latest.get('bollinger_upper', 0)) if 'bollinger_upper' in latest and not pd.isna(latest['bollinger_upper']) else None,
            bollinger_lower=float(latest.get('bollinger_lower', 0)) if 'bollinger_lower' in latest and not pd.isna(latest['bollinger_lower']) else None,
            atr=float(latest.get('atr', 0)) if 'atr' in latest and not pd.isna(latest['atr']) else None,
            volume_ma=float(latest.get('volume_ma', 0)) if 'volume_ma' in latest and not pd.isna(latest['volume_ma']) else None,
            volume_ratio=float(latest.get('volume_ratio', 0)) if 'volume_ratio' in latest and not pd.isna(latest['volume_ratio']) else None
        )
    
    def _extract_key_levels(self, ohlcv_data) -> KeyLevels:
        """Extract support and resistance levels"""
        if ohlcv_data.empty:
            return KeyLevels()
        
        support, resistance = self.analysis_engine.get_support_resistance_levels(ohlcv_data)
        current_price = float(ohlcv_data['close'].iloc[-1])
        
        # Calculate current position
        current_position = None
        if support and resistance:
            current_position = (current_price - support) / (resistance - support)
        
        return KeyLevels(
            support_level=support,
            resistance_level=resistance,
            current_position=current_position
        )
    
    def _extract_volume_profile(self, ohlcv_data) -> VolumeProfile:
        """Extract volume profile data"""
        if ohlcv_data.empty:
            return VolumeProfile()
        
        recent_volume = ohlcv_data['volume'].tail(5).mean()
        avg_volume = ohlcv_data['volume'].mean()
        
        return VolumeProfile(
            volume_surge=self.analysis_engine.analyze_volume_profile(ohlcv_data),
            volume_trend="Increasing" if recent_volume > avg_volume else "Decreasing",
            recent_volume=float(recent_volume),
            avg_volume=float(avg_volume)
        )
    
    def _extract_momentum_data(self, ohlcv_data) -> MomentumData:
        """Extract momentum data"""
        if ohlcv_data.empty:
            return MomentumData()
        
        momentum_score, momentum_desc = self.analysis_engine.calculate_momentum_score(ohlcv_data)
        
        return MomentumData(
            momentum_score=momentum_score,
            momentum_description=momentum_desc,
            price_momentum=0.0,  # Will be calculated in risk assessment
            rsi_momentum=0.0,    # Will be calculated in risk assessment
            macd_momentum=0.0    # Will be calculated in risk assessment
        )
    
    def _create_risk_assessment(self, ohlcv_data, pair_info: Dict[str, Any], rug_data: Dict[str, Any]) -> RiskAssessment:
        """Create risk assessment with MEME COIN specific considerations"""
        volatility = self.analysis_engine.calculate_volatility(ohlcv_data)
        risk_level = self.analysis_engine.get_risk_level_assessment(ohlcv_data, pair_info, rug_data)
        position_size = self.analysis_engine.get_position_size_recommendation(volatility or 0)
        
        # Calculate initial confidence score based on data quality
        confidence_score = 50.0  # Base confidence
        
        # Adjust confidence based on data availability
        if not ohlcv_data.empty and len(ohlcv_data) >= 20:
            confidence_score += 20  # Good data quality
        elif not ohlcv_data.empty and len(ohlcv_data) >= 10:
            confidence_score += 10  # Moderate data quality
        
        # Adjust confidence based on rug data availability
        if rug_data and rug_data.get('success'):
            confidence_score += 15  # Rug data available
        else:
            confidence_score -= 10  # No rug data
        
        # MEME COIN SPECIFIC CONFIDENCE ADJUSTMENTS
        meme_coin_analysis = getattr(self, '_meme_coin_analysis', {})
        if meme_coin_analysis:
            # Boost confidence for strong meme coin signals
            if meme_coin_analysis.get('is_pumping', False):
                confidence_score += 10
            if meme_coin_analysis.get('volume_surge_level', '') in ['EXTREME SURGE', 'MASSIVE SURGE']:
                confidence_score += 8
            if meme_coin_analysis.get('is_parabolic', False):
                confidence_score += 5
            
            # Reduce confidence for high meme coin risks
            meme_risk = meme_coin_analysis.get('meme_coin_risk', {})
            if meme_risk:
                risk_score = meme_risk.get('risk_score', 0)
                if risk_score >= 80:
                    confidence_score -= 20
                elif risk_score >= 60:
                    confidence_score -= 15
                elif risk_score >= 40:
                    confidence_score -= 10
        
        # Ensure confidence is within bounds
        confidence_score = max(0.0, min(100.0, confidence_score))
        
        return RiskAssessment(
            confidence_score=confidence_score,
            risk_level=risk_level,
            position_size=position_size,
            volatility=volatility,
            risk_factors=[]  # Will be populated in final verdict
        )
    
    def _create_rug_analysis(self, rug_data: Dict[str, Any]) -> RugAnalysis:
        """Create rug analysis object"""
        if not rug_data or not rug_data.get('success'):
            return RugAnalysis(
                token_address="Unknown",
                error=rug_data.get('error', 'Rug check failed') if rug_data else 'Rug check unavailable'
            )
        
        return RugAnalysis(
            rug_probability=rug_data.get('rug_probability', 0.0),
            risk_score=rug_data.get('risk_score', 0),
            risk_level=rug_data.get('risk_level', 'Unknown'),
            risk_emoji=rug_data.get('risk_emoji', '❓'),
            security_flags=rug_data.get('security_flags', {}),
            holder_info=rug_data.get('holder_analysis', {}),
            liquidity_info=rug_data.get('liquidity_info', {}),
            insider_networks=rug_data.get('insider_activity', {}).get('networks_detected', 0),
            jupiter_verified=rug_data.get('verification', {}).get('jupiter_verified', False),
            risk_factors=rug_data.get('risk_factors', [])
        )
    
    def _create_trading_recommendation(self, ohlcv_data, pair_info: Dict[str, Any], 
                                     rug_data: Dict[str, Any], key_levels: KeyLevels) -> TradingRecommendation:
        """Create trading recommendation"""
        verdict, reasoning, confidence_score = self.analysis_engine.get_final_verdict(
            ohlcv_data, pair_info, rug_data
        )
        
        entry_strategy = self.analysis_engine.analyze_price_position(
            float(ohlcv_data['close'].iloc[-1]) if not ohlcv_data.empty else 0,
            key_levels.support_level,
            key_levels.resistance_level
        )
        
        # Store confidence score for later use
        self._last_confidence_score = confidence_score
        
        return TradingRecommendation(
            final_verdict=verdict,
            entry_strategy=entry_strategy,
            reasoning=reasoning
        )
    
    async def analyze_token_concurrent(self, token_address: str, user_id: int) -> Union[AnalysisResult, str]:
        """Analyze token using concurrent processing"""
        try:
            # Check if user can submit more tasks
            if not self.concurrent_processor.can_process_user(user_id):
                return "Too many concurrent requests. Please wait for current analysis to complete."
            
            # Submit analysis task
            result = await self.concurrent_processor.process_async(
                user_id, self.analyze_token, token_address, user_id
            )
            
            if result.success:
                return result.result
            else:
                logger.error(f"Concurrent analysis failed for user {user_id}: {result.error}")
                return f"Analysis failed: {result.error}"
                
        except Exception as e:
            logger.error(f"Error in concurrent analysis for {token_address}: {e}")
            return f"Concurrent analysis failed: {str(e)}"
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis service statistics"""
        return {
            'concurrent_processor': self.concurrent_processor.get_global_stats(),
            'rate_limiter': self.rate_limit_manager.rate_limiter.get_global_stats(),
            'data_fetcher': {
                'status': 'Active',
                'last_request': datetime.utcnow().isoformat()
            }
        }

# Create global instance
token_analysis_service = TokenAnalysisService()
