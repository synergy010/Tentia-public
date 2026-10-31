"""
Rug checker service integration for the Meme Coin Analyzer Bot
"""

import asyncio
from typing import Dict, Any, Optional
from config.settings import RUGCHECK_DEBUG_MODE
from config.logging_config import get_logger

# Import the existing rug checker service
try:
    from rug_checker_service import rug_checker_service
except ImportError:
    # Fallback if the original file is not available
    rug_checker_service = None

logger = get_logger(__name__)

class RugCheckerService:
    """Service wrapper for rug checking functionality"""
    
    def __init__(self):
        self.original_service = rug_checker_service
        if not self.original_service:
            logger.warning("Original rug checker service not available")
    
    async def check_token(self, token_address: str) -> Dict[str, Any]:
        """
        Check token for rug pull risks
        
        Args:
            token_address: Solana token address
            
        Returns:
            Dictionary with rug check results
        """
        try:
            if not self.original_service:
                return {
                    'success': False,
                    'error': 'Rug checker service not available'
                }
            
            logger.info(f"Starting rug check for token: {token_address}")
            
            # Use the original service's check_token method
            result = await self.original_service.check_token(token_address)
            
            if result and result.get('success'):
                logger.info(f"Rug check completed for {token_address}")
            else:
                logger.warning(f"Rug check failed for {token_address}: {result.get('error', 'Unknown error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in rug check for {token_address}: {e}")
            return {
                'success': False,
                'error': f'Rug check error: {str(e)}'
            }
    
    def generate_safe_response(self, result: Dict[str, Any], response_type: str = "quick") -> Dict[str, Any]:
        """
        Generate safe response using the original service
        
        Args:
            result: Rug check result
            response_type: Type of response (quick, detailed, summary)
            
        Returns:
            Dictionary with HTML and markdown responses
        """
        try:
            if not self.original_service:
                return {
                    'success': False,
                    'error': 'Rug checker service not available',
                    'html': 'Rug checker service not available',
                    'markdown': 'Rug checker service not available'
                }
            
            # Use the original service's generate_safe_response method
            return self.original_service.generate_safe_response(result, response_type)
            
        except Exception as e:
            logger.error(f"Error generating safe response: {e}")
            return {
                'success': False,
                'error': f'Response generation error: {str(e)}',
                'html': f'Error generating response: {str(e)}',
                'markdown': f'Error generating response: {str(e)}'
            }
    
    def validate_solana_address(self, address: str) -> bool:
        """Validate Solana token address format"""
        try:
            if not self.original_service:
                # Fallback validation
                if not address or len(address) < 32 or len(address) > 44:
                    return False
                
                base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
                return all(c in base58_chars for c in address)
            
            # Use the original service's validation
            return self.original_service.validate_solana_address(address)
            
        except Exception as e:
            logger.error(f"Error validating address {address}: {e}")
            return False
    
    def get_rug_probability_emoji(self, probability: float) -> str:
        """Get emoji for rug probability"""
        try:
            if not self.original_service:
                # Fallback emoji logic
                if probability >= 85:
                    return "💀"
                elif probability >= 65:
                    return "🔴"
                elif probability >= 45:
                    return "🟠"
                elif probability >= 25:
                    return "🟡"
                else:
                    return "🟢"
            
            # Use the original service's emoji logic
            return self.original_service.get_rug_probability_emoji(probability)
            
        except Exception as e:
            logger.error(f"Error getting rug probability emoji: {e}")
            return "❓"
    
    def get_comprehensive_risk_assessment(self, api_score: float, rug_probability: float) -> Dict[str, str]:
        """Get comprehensive risk assessment"""
        try:
            if not self.original_service:
                # Fallback risk assessment
                if rug_probability >= 85:
                    return {
                        'level': '💀 EXTREME DANGER',
                        'recommendation': '❌ AVOID AT ALL COSTS',
                        'description': 'Critical red flags detected. Very high probability of rug pull.',
                        'action': 'Do not invest. Exit immediately if holding.'
                    }
                elif rug_probability >= 65:
                    return {
                        'level': '🔴 VERY HIGH RISK',
                        'recommendation': '⚠️ EXTREME CAUTION',
                        'description': 'Significant risks detected. High chance of losing funds.',
                        'action': 'Only for very experienced traders with small amounts.'
                    }
                elif rug_probability >= 45:
                    return {
                        'level': '🟠 HIGH RISK',
                        'recommendation': '⚠️ HIGH CAUTION',
                        'description': 'Several concerning factors. Above average risk.',
                        'action': 'Thorough research required. Consider risks carefully.'
                    }
                else:
                    return {
                        'level': '🟢 LOW-MODERATE RISK',
                        'recommendation': '✅ ACCEPTABLE WITH CAUTION',
                        'description': 'Below average risk but still requires caution.',
                        'action': 'Standard due diligence recommended.'
                    }
            
            # Use the original service's risk assessment
            return self.original_service.get_comprehensive_risk_assessment(api_score, rug_probability)
            
        except Exception as e:
            logger.error(f"Error getting risk assessment: {e}")
            return {
                'level': '❓ UNKNOWN RISK',
                'recommendation': '🔍 RESEARCH REQUIRED',
                'description': 'Unable to assess risk level.',
                'action': 'Do your own research before investing.'
            }
    
    def format_number(self, num: Any) -> str:
        """Format large numbers with appropriate suffixes"""
        try:
            if not self.original_service:
                # Fallback formatting
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
            
            # Use the original service's formatting
            return self.original_service.format_number(num)
            
        except Exception as e:
            logger.error(f"Error formatting number {num}: {e}")
            return str(num)
    
    def format_percentage(self, num: Any) -> str:
        """Format percentage values"""
        try:
            if not self.original_service:
                # Fallback formatting
                if num is None:
                    return "N/A"
                try:
                    return f"{float(num):.1f}%"
                except (ValueError, TypeError):
                    return str(num)
            
            # Use the original service's formatting
            return self.original_service.format_percentage(num)
            
        except Exception as e:
            logger.error(f"Error formatting percentage {num}: {e}")
            return str(num)
    
    def format_price(self, price: Any) -> str:
        """Format price with appropriate decimal places"""
        try:
            if not self.original_service:
                # Fallback formatting
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
            
            # Use the original service's formatting
            return self.original_service.format_price(price)
            
        except Exception as e:
            logger.error(f"Error formatting price {price}: {e}")
            return str(price)
    
    def get_service_status(self) -> Dict[str, Any]:
        """Get service status information"""
        return {
            'service_available': self.original_service is not None,
            'debug_mode': RUGCHECK_DEBUG_MODE,
            'original_service_type': type(self.original_service).__name__ if self.original_service else None
        }

# Create global instance
rug_checker_service = RugCheckerService()
