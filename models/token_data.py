"""
Data models for token information and analysis results
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime

@dataclass
class TokenInfo:
    """Basic token information"""
    address: str
    name: str
    symbol: str
    decimals: Optional[int] = None
    supply: Optional[str] = None

@dataclass
class PriceData:
    """Token price information"""
    current_price: float
    price_change_24h: Optional[float] = None
    price_change_percent: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None

@dataclass
class MarketData:
    """Market-related data"""
    market_cap: Optional[float] = None
    liquidity_usd: Optional[float] = None
    volume_24h: Optional[float] = None
    fdv: Optional[float] = None
    total_supply: Optional[str] = None

@dataclass
class TradingActivity:
    """Trading activity data"""
    buys_24h: int = 0
    sells_24h: int = 0
    total_trades_24h: int = 0
    buy_sell_ratio: Optional[float] = None

@dataclass
class TechnicalIndicators:
    """Technical analysis indicators"""
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    sma_20: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr: Optional[float] = None
    volume_ma: Optional[float] = None
    volume_ratio: Optional[float] = None

@dataclass
class KeyLevels:
    """Support and resistance levels"""
    support_level: Optional[float] = None
    resistance_level: Optional[float] = None
    current_position: Optional[float] = None

@dataclass
class VolumeProfile:
    """Volume analysis data"""
    volume_surge: Optional[str] = None
    volume_trend: Optional[str] = None
    recent_volume: Optional[float] = None
    avg_volume: Optional[float] = None

@dataclass
class MomentumData:
    """Momentum analysis data"""
    momentum_score: float = 0.0
    momentum_description: str = "Neutral"
    price_momentum: float = 0.0
    rsi_momentum: float = 0.0
    macd_momentum: float = 0.0

@dataclass
class RiskAssessment:
    """Risk assessment data"""
    confidence_score: float = 0.0
    risk_level: str = "Unknown"
    position_size: str = "Unknown"
    volatility: Optional[float] = None
    risk_factors: List[str] = field(default_factory=list)

@dataclass
class RugAnalysis:
    """Rug pull analysis data"""
    rug_probability: float = 0.0
    risk_score: int = 0
    risk_level: str = "Unknown"
    risk_emoji: str = "❓"
    security_flags: Dict[str, Any] = field(default_factory=dict)
    holder_info: Dict[str, Any] = field(default_factory=dict)
    liquidity_info: Dict[str, Any] = field(default_factory=dict)
    insider_networks: int = 0
    jupiter_verified: bool = False
    risk_factors: List[str] = field(default_factory=list)

@dataclass
class TradingRecommendation:
    """Trading recommendations"""
    final_verdict: str = "Unknown"
    entry_strategy: str = "Unknown"
    reasoning: str = "No analysis available"
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None

@dataclass
class AnalysisResult:
    """Complete analysis result"""
    # Basic Info
    token_info: TokenInfo
    price_data: PriceData
    market_data: MarketData
    trading_activity: TradingActivity
    
    # Technical Analysis
    technical_indicators: TechnicalIndicators
    key_levels: KeyLevels
    volume_profile: VolumeProfile
    momentum_data: MomentumData
    
    # Risk & Recommendations
    risk_assessment: RiskAssessment
    rug_analysis: RugAnalysis
    trading_recommendation: TradingRecommendation
    
    # Metadata
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    dex_link: Optional[str] = None
    pair_address: Optional[str] = None
    
    # Raw data for debugging
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for backward compatibility"""
        return {
            "token_name": self.token_info.name,
            "token_symbol": self.token_info.symbol,
            "token_address": self.token_info.address,
            "price": f"${self.price_data.current_price:.8f}",
            "price_change_24h": f"{self.price_data.price_change_percent:.2f}%" if self.price_data.price_change_percent else "N/A",
            "market_cap": self._format_number(self.market_data.market_cap),
            "liquidity": self._format_number(self.market_data.liquidity_usd),
            "volume_24h": self._format_number(self.market_data.volume_24h),
            "volatility": f"{self.risk_assessment.volatility:.2f}%" if self.risk_assessment.volatility else "N/A",
            "buys_24h": self.trading_activity.buys_24h,
            "sells_24h": self.trading_activity.sells_24h,
            "total_trades_24h": self.trading_activity.total_trades_24h,
            "buy_sell_ratio": f"{self.trading_activity.buy_sell_ratio:.2f}" if self.trading_activity.buy_sell_ratio else "∞",
            "support_level": f"${self.key_levels.support_level:.8f}" if self.key_levels.support_level else "N/A",
            "resistance_level": f"${self.key_levels.resistance_level:.8f}" if self.key_levels.resistance_level else "N/A",
            "rsi": f"{self.technical_indicators.rsi:.1f}" if self.technical_indicators.rsi else "N/A",
            "momentum": self.momentum_data.momentum_description,
            "volume_profile": self.volume_profile.volume_surge or "N/A",
            "confidence_score": f"{self.risk_assessment.confidence_score:.0f}%",
            "risk_level": self.risk_assessment.risk_level,
            "position_size": self.risk_assessment.position_size,
            "rug_probability": f"{self.rug_analysis.rug_probability:.1f}%",
            "rug_status": f"{self.rug_analysis.risk_emoji} {self.rug_analysis.risk_level}",
            "final_verdict": self.trading_recommendation.final_verdict,
            "entry_strategy": self.trading_recommendation.entry_strategy,
            "reasoning": self.trading_recommendation.reasoning,
            "dex_link": self.dex_link or "N/A"
        }
    
    def _format_number(self, num: Optional[float]) -> str:
        """Format large numbers with appropriate suffixes"""
        if num is None:
            return "N/A"
        
        try:
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

@dataclass
class RugCheckResult:
    """Rug check API result"""
    success: bool
    token_address: str
    token_name: str = "Unknown"
    token_symbol: str = "Unknown"
    risk_score: int = 0
    risk_level: str = "Unknown"
    risk_emoji: str = "❓"
    rug_probability: float = 0.0
    risk_assessment: Dict[str, Any] = field(default_factory=dict)
    risk_factors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    security_flags: Dict[str, Any] = field(default_factory=dict)
    liquidity_info: Dict[str, Any] = field(default_factory=dict)
    holder_analysis: Dict[str, Any] = field(default_factory=dict)
    market_data: Dict[str, Any] = field(default_factory=dict)
    verification: Dict[str, Any] = field(default_factory=dict)
    insider_activity: Dict[str, Any] = field(default_factory=dict)
    launchpad_info: Dict[str, Any] = field(default_factory=dict)
    technical_info: Dict[str, Any] = field(default_factory=dict)
    debug_info: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
