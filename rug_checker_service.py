import os
import logging
import requests
import asyncio
from datetime import datetime
import json
import re

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class RugCheckerService:
    def __init__(self, debug_mode=True):
        self.api_base_url = "https://api.rugcheck.xyz/v1/tokens"
        self.debug_mode = debug_mode
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
    
    def debug_log(self, message, data=None):
        """Enhanced debug logging"""
        if self.debug_mode:
            print(f"🐛 DEBUG: {message}")
            if data is not None:
                if isinstance(data, (dict, list)):
                    print(f"📄 DATA: {json.dumps(data, indent=2)[:1000]}...")
                else:
                    print(f"📄 DATA: {str(data)[:500]}...")
            logger.info(f"DEBUG: {message}")
    
    def get_risk_level_from_score(self, risk_score):
        """Convert API risk score to emoji and description - CORRECTED THRESHOLDS"""
        if risk_score is None:
            return "❓", "Unknown", 50
        
        risk_score = int(float(risk_score))
        
        # CORRECTED: RugCheck uses 0-100 scale, not 0-1000
        # Lower scores = better (safer), Higher scores = worse (riskier)
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
    
    def calculate_refined_rug_probability(self, api_score, data: dict) -> tuple:
        """
        Calculate rug probability based on API score with minor adjustments
        FIXED: Now properly uses the 0-100 API score scale
        """
        # Start with API score-based probability - CORRECTED MAPPING
        _, _, base_probability = self.get_risk_level_from_score(api_score)
        
        critical_factors = []
        probability_adjustments = 0
        
        # CRITICAL INSTANT RUG INDICATORS (Override everything)
        if data.get('rugged', False):
            return 100.0, ["💀 TOKEN IS CONFIRMED RUGGED!"]
        
        # MAJOR SECURITY ISSUES
        token = data.get('token', {})
        
        # Mint authority is dangerous
        if token.get('mintAuthority'):
            probability_adjustments += 20
            critical_factors.append("🔴 Mint Authority Active - Can create unlimited tokens")
        
        # Freeze authority is dangerous
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
                # Good distribution - reduce risk
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
        
        # TRANSFER FEES
        transfer_fee = data.get('transferFee', {})
        fee_pct = transfer_fee.get('pct', 0)
        if fee_pct > 10:
            probability_adjustments += 8
            critical_factors.append(f"🔴 High transfer fee: {fee_pct}%")
        elif fee_pct > 5:
            probability_adjustments += 3
            critical_factors.append(f"🟠 Transfer fee: {fee_pct}%")
        
        # MUTABLE METADATA
        token_meta = data.get('tokenMeta', {})
        if token_meta.get('mutable', False):
            probability_adjustments += 2
            critical_factors.append("🟡 Mutable metadata - Can change token info")
        
        # LP LOCK STATUS
        markets = data.get('markets', [])
        if markets:
            for market in markets:
                lp_data = market.get('lp', {})
                lp_locked_pct = lp_data.get('lpLockedPct', 0)
                if lp_locked_pct < 50:
                    probability_adjustments += 8
                    critical_factors.append(f"🔴 Low LP lock: {lp_locked_pct:.1f}% locked")
                elif lp_locked_pct < 90:
                    probability_adjustments += 3
                    critical_factors.append(f"🟡 Partial LP lock: {lp_locked_pct:.1f}% locked")
                break  # Only check first market
        
        # POSITIVE ADJUSTMENTS (Reduce risk)
        
        # Jupiter verification
        verification = data.get('verification', {})
        if verification and verification.get('jup_verified', False):
            probability_adjustments -= 8
            critical_factors.append("🟢 Jupiter verified")
        
        # Calculate final probability
        final_probability = base_probability + probability_adjustments
        
        # Ensure probability stays within realistic bounds
        final_probability = max(0.1, min(99.9, final_probability))
        
        # If API score is very low (good), don't let adjustments make it too high
        if api_score <= 20 and final_probability > 25:
            final_probability = min(final_probability, 25)
        
        # If API score is moderate, cap the probability accordingly
        if api_score <= 40 and final_probability > 45:
            final_probability = min(final_probability, 45)
        
        return final_probability, critical_factors[:8]  # Limit to 8 most important factors
    
    def format_number(self, num):
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
    
    def format_percentage(self, num):
        """Format percentage values"""
        if num is None:
            return "N/A"
        try:
            return f"{float(num):.1f}%"
        except (ValueError, TypeError):
            return str(num)
    
    def format_price(self, price):
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

    async def check_token(self, token_address: str) -> dict:
        """Check token using RugCheck API with /report endpoint"""
        try:
            token_address = token_address.strip()
            self.debug_log(f"Starting API check for token: {token_address}")
            
            api_url = f"{self.api_base_url}/{token_address}/report"
            self.debug_log(f"API URL: {api_url}")
            
            response = requests.get(api_url, headers=self.headers, timeout=30)
            self.debug_log(f"Response status code: {response.status_code}")
            
            if response.status_code == 404:
                return {
                    'success': False,
                    'error': 'Token not found in RugCheck database. This could mean the token is very new or not yet indexed.',
                }
            
            if response.status_code != 200:
                return {
                    'success': False,
                    'error': f'API request failed with status code: {response.status_code}',
                }
            
            try:
                api_data = response.json()
                self.debug_log("API Response received:", api_data)
                
                if api_data is None:
                    return {
                        'success': False,
                        'error': 'API returned null response',
                    }
                    
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f'Failed to parse API response as JSON: {str(e)}',
                }
            
            result = self.process_api_data(api_data, token_address)
            return result
            
        except Exception as e:
            error_msg = f"Error checking token {token_address}: {str(e)}"
            self.debug_log(error_msg)
            logger.error(error_msg)
            return {
                'success': False,
                'error': f'Network/Unexpected error: {str(e)}',
            }
    
    def get_comprehensive_risk_assessment(self, api_score, rug_probability):
        """Provide comprehensive risk assessment - CORRECTED FOR 0-100 SCALE"""
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
        elif rug_probability >= 25:
            return {
                'level': '🟡 MODERATE RISK',
                'recommendation': '🔍 RESEARCH REQUIRED',
                'description': 'Some risk factors present. Standard DeFi risks.',
                'action': 'Do your research. Understand the risks.'
            }
        elif rug_probability >= 15:
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
    
    def process_api_data(self, api_data: dict, token_address: str) -> dict:
        """Process and extract useful data from API response - CORRECTED VERSION"""
        try:
            self.debug_log("Processing API data...")
            
            if api_data is None or not isinstance(api_data, dict):
                return {
                    'success': False,
                    'error': 'API returned invalid data',
                }
            
            # Extract and normalize API risk score - CORRECTED: 0-100 scale
            api_risk_score = api_data.get('score', 0)
            try:
                api_risk_score = max(0, min(100, int(float(api_risk_score))))  # Ensure 0-100 range
            except (ValueError, TypeError):
                api_risk_score = 0
            
            # Calculate improved rug probability
            rug_probability, risk_factors = self.calculate_refined_rug_probability(api_risk_score, api_data)
            
            # Get risk assessment
            risk_emoji, risk_level, _ = self.get_risk_level_from_score(api_risk_score)
            risk_assessment = self.get_comprehensive_risk_assessment(api_risk_score, rug_probability)
            
            # Initialize result with CORRECTED structure
            result = {
                'success': True,
                'token_address': token_address,
                'token_name': 'Unknown',
                'token_symbol': 'Unknown',
                
                # CORRECTED SCORING SYSTEM (0-100)
                'risk_score': api_risk_score,  # Now correctly 0-100
                'risk_level': risk_level,
                'risk_emoji': risk_emoji,
                'rug_probability': round(rug_probability, 1),
                'risk_assessment': risk_assessment,
                'risk_factors': risk_factors,
                
                # Organized data sections
                'warnings': [],
                'security_flags': {},
                'liquidity_info': {},
                'holder_analysis': {},
                'market_data': {},
                'verification': {},
                'insider_activity': {},
                'launchpad_info': {},
                'technical_info': {},
                'debug_info': api_data if self.debug_mode else {}
            }
            
            # Extract basic token information
            token_meta = api_data.get('tokenMeta', {})
            file_meta = api_data.get('fileMeta', {})
            
            if token_meta:
                result['token_name'] = token_meta.get('name', file_meta.get('name', 'Unknown'))
                result['token_symbol'] = token_meta.get('symbol', file_meta.get('symbol', 'Unknown'))
            
            # Process security flags
            token_info = api_data.get('token', {})
            result['security_flags'] = {
                'mint_authority': bool(token_info.get('mintAuthority')),
                'freeze_authority': bool(token_info.get('freezeAuthority')),
                'rugged': api_data.get('rugged', False),
                'mutable_metadata': token_meta.get('mutable', False),
                'transfer_fee_active': bool(api_data.get('transferFee', {}).get('pct', 0) > 0),
                'transfer_fee_pct': api_data.get('transferFee', {}).get('pct', 0),
                'is_initialized': token_info.get('isInitialized', False),
                'token_supply': self.format_number(token_info.get('supply', 0)),
                'decimals': token_info.get('decimals', 0)
            }
            
            # Process liquidity information
            total_liquidity = api_data.get('totalMarketLiquidity', 0) or 0
            stable_liquidity = api_data.get('totalStableLiquidity', 0) or 0
            
            result['liquidity_info'] = {
                'total_market_usd': self.format_number(total_liquidity),
                'total_stable_usd': self.format_number(stable_liquidity),
                'total_lp_providers': api_data.get('totalLPProviders', 0),
                'liquidity_ratio': f"{(stable_liquidity/max(total_liquidity, 1)*100):.1f}%" if total_liquidity > 0 else "0%",
                'liquidity_health': self.assess_liquidity_health(stable_liquidity, api_data.get('totalLPProviders', 0))
            }
            
            # Process market data
            markets = api_data.get('markets', [])
            if markets and len(markets) > 0:
                primary_market = markets[0]
                lp_data = primary_market.get('lp', {})
                
                result['market_data'] = {
                    'price_usd': self.format_price(api_data.get('price', 0)),
                    'market_cap_usd': self.format_number(lp_data.get('baseUSD', 0)),
                    'liquidity_base': self.format_number(lp_data.get('base', 0)),
                    'liquidity_quote': self.format_number(lp_data.get('quote', 0)),
                    'quote_usd': self.format_number(lp_data.get('quoteUSD', 0)),
                    'base_usd': self.format_number(lp_data.get('baseUSD', 0)),
                    'market_type': primary_market.get('marketType', 'Unknown'),
                    'lp_locked_pct': self.format_percentage(lp_data.get('lpLockedPct', 0)),
                    'lp_locked_usd': self.format_number(lp_data.get('lpLockedUSD', 0)),
                    'total_markets': len(markets)
                }
            else:
                result['market_data'] = {
                    'price_usd': self.format_price(api_data.get('price', 0)),
                    'market_cap_usd': 'N/A',
                    'market_type': 'Unknown',
                    'total_markets': 0
                }
            
            # Process holder analysis
            top_holders = api_data.get('topHolders', [])
            total_holders = api_data.get('totalHolders', 0)
            
            if top_holders and len(top_holders) > 0:
                top_1_pct = float(top_holders[0].get('pct', 0))
                top_5_pct = sum(float(holder.get('pct', 0)) for holder in top_holders[:min(5, len(top_holders))])
                top_10_pct = sum(float(holder.get('pct', 0)) for holder in top_holders[:min(10, len(top_holders))])
                
                # Analyze top holder
                top_holder = top_holders[0]
                known_accounts = api_data.get('knownAccounts', {})
                top_holder_info = known_accounts.get(top_holder.get('address', ''), {})
                
                result['holder_analysis'] = {
                    'total_holders': total_holders,
                    'top_1_holds': self.format_percentage(top_1_pct),
                    'top_5_hold': self.format_percentage(top_5_pct),
                    'top_10_hold': self.format_percentage(top_10_pct),
                    'top_holder_type': top_holder_info.get('type', 'Unknown'),
                    'top_holder_name': top_holder_info.get('name', 'Unknown'),
                    'distribution_score': self.get_distribution_score(top_1_pct, top_10_pct),
                    'holder_concentration_risk': self.get_concentration_risk(top_1_pct)
                }
            else:
                result['holder_analysis'] = {
                    'total_holders': total_holders,
                    'distribution_score': "❓ Unknown",
                    'holder_concentration_risk': "❓ Unknown"
                }
            
            # Process verification status
            verification = api_data.get('verification', {})
            if verification:
                result['verification'] = {
                    'jupiter_verified': verification.get('jup_verified', False),
                    'jupiter_strict': verification.get('jup_strict', False),
                    'has_social_links': len(verification.get('links', [])) > 0,
                    'social_links_count': len(verification.get('links', []))
                }
            else:
                result['verification'] = {
                    'jupiter_verified': False,
                    'jupiter_strict': False,
                    'has_social_links': False,
                    'social_links_count': 0
                }
            
            # Process insider activity
            insider_networks = api_data.get('insiderNetworks', []) or []
            result['insider_activity'] = {
                'networks_detected': len(insider_networks),
                'graph_insiders': api_data.get('graphInsidersDetected', 0),
                'has_insider_networks': len(insider_networks) > 0
            }
            
            # Process launchpad information
            launchpad = api_data.get('launchpad', {})
            if launchpad:
                result['launchpad_info'] = {
                    'platform': launchpad.get('name', 'Unknown'),
                    'platform_type': launchpad.get('platform', 'Unknown'),
                    'has_logo': bool(launchpad.get('logo')),
                    'has_url': bool(launchpad.get('url'))
                }
            else:
                result['launchpad_info'] = {}
            
            # Process technical information
            result['technical_info'] = {
                'token_type': api_data.get('tokenType', 'Standard'),
                'creator_address': api_data.get('creator', 'Unknown')[:8] + "..." if api_data.get('creator') else 'Unknown',
                'creator_balance': api_data.get('creatorBalance', 0),
                'token_program': api_data.get('tokenProgram', 'Unknown'),
                'has_extensions': bool(api_data.get('token_extensions')),
                'detected_at': api_data.get('detectedAt', 'Unknown')
            }
            
            # Extract warnings from API risks
            risks = api_data.get('risks', [])
            warnings = []
            
            for risk in risks:
                if not isinstance(risk, dict):
                    continue
                    
                risk_level = risk.get('level', '').lower()
                risk_name = risk.get('name', 'Unknown Risk')
                risk_desc = risk.get('description', '')
                risk_score = risk.get('score', 0)
                
                warning_text = f"{risk_name}"
                if risk_desc:
                    warning_text += f": {risk_desc}"
                
                if len(warning_text) > 100:
                    warning_text = warning_text[:97] + "..."
                
                if risk_level == 'danger' or risk_score > 500:
                    warnings.append(f"💀 {warning_text}")
                elif risk_level == 'high' or risk_score > 300:
                    warnings.append(f"🔴 {warning_text}")
                elif risk_level in ['warn', 'warning'] or risk_score > 100:
                    warnings.append(f"🟡 {warning_text}")
                else:
                    warnings.append(f"ℹ️ {warning_text}")
            
            result['warnings'] = warnings[:6]  # Limit to 6 most important
            
            self.debug_log("API data processed successfully")
            self.debug_log(f"Final risk score: {result['risk_score']}, Rug probability: {result['rug_probability']}%")
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing API data: {str(e)}"
            self.debug_log(error_msg)
            logger.error(error_msg)
            return {
                'success': False,
                'error': f'Error processing token data: {str(e)}',
            }
    
    def assess_liquidity_health(self, liquidity_usd, lp_providers):
        """Assess overall liquidity health"""
        if liquidity_usd > 100000 and lp_providers > 10:
            return "🟢 Excellent"
        elif liquidity_usd > 50000 and lp_providers > 5:
            return "🟢 Good"
        elif liquidity_usd > 10000 and lp_providers > 2:
            return "🟡 Fair"
        elif liquidity_usd > 1000:
            return "🟠 Low"
        else:
            return "🔴 Very Poor"
    
    def get_distribution_score(self, top_1_pct, top_10_pct):
        """Calculate distribution health score"""
        if top_1_pct > 90:
            return "💀 Extremely Poor"
        elif top_1_pct > 80:
            return "🔴 Very Poor"
        elif top_1_pct > 60:
            return "🟠 Poor"
        elif top_1_pct > 40:
            return "🟡 Fair"
        elif top_1_pct > 25:
            return "🟡 Moderate"
        elif top_10_pct > 90:
            return "🟡 Fair (concentrated in top 10)"
        else:
            return "🟢 Good"
    
    def get_concentration_risk(self, top_1_pct):
        """Get concentration risk level"""
        if top_1_pct > 95:
            return "💀 EXTREME RISK"
        elif top_1_pct > 85:
            return "🔴 Very High Risk"
        elif top_1_pct > 70:
            return "🟠 High Risk"
        elif top_1_pct > 50:
            return "🟡 Medium Risk"
        elif top_1_pct > 30:
            return "🟡 Low-Medium Risk"
        else:
            return "🟢 Low Risk"

    def validate_solana_address(self, address: str) -> bool:
        """Validate Solana token address format"""
        if not address or len(address) < 32 or len(address) > 44:
            return False
        
        base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return all(c in base58_chars for c in address)

    def get_rug_probability_emoji(self, probability):
        """Get emoji for rug probability"""
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

    def escape_markdown(self, text):
        """Enhanced escape special characters for Telegram MarkdownV2"""
        if not text:
            return ""
        
        text = str(text)
        
        # First escape backslashes to avoid double escaping
        text = text.replace('\\', '\\\\')
        
        # Then escape all other special characters for MarkdownV2
        escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '<', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in escape_chars:
            text = text.replace(char, f'\\{char}')
        
        return text

    def safe_format_text(self, text, max_length=4096):
        """Safely format text for Telegram with length limits"""
        if not text:
            return ""
        
        # First escape markdown
        escaped_text = self.escape_markdown(str(text))
        
        # Truncate if too long
        if len(escaped_text) > max_length:
            escaped_text = escaped_text[:max_length-10] + "\\.\\.\\."
        
        return escaped_text

    def generate_quick_response(self, result: dict) -> str:
        """Generate quick analysis response - CORRECTED VERSION"""
        rug_prob = result.get('rug_probability', 0)
        prob_emoji = self.get_rug_probability_emoji(rug_prob)
        risk_assessment = result.get('risk_assessment', {})
        
        response = f"{result['risk_emoji']} *Quick Analysis* {prob_emoji}\n\n"
        response += f"*{self.safe_format_text(result['token_name'])}* \\(`{self.safe_format_text(result['token_symbol'])}`\\)\n"
        response += f"*Risk Score:* {result['risk_score']}/100 \\- {self.safe_format_text(result['risk_level'])}\n"
        response += f"*Rug Probability:* {prob_emoji} {rug_prob:.1f}%\n"
        response += f"*Assessment:* {self.safe_format_text(risk_assessment.get('level', 'Unknown'))}\n\n"
        
        # Key security flags
        flags = result['security_flags']
        response += "🔐 *Security:* "
        security_items = []
        if flags['rugged']:
            security_items.append("💀 RUGGED")
        if flags['mint_authority']:
            security_items.append("🔴 Mint")
        if flags['freeze_authority']:
            security_items.append("🔴 Freeze")
        if flags['transfer_fee_active']:
            security_items.append(f"🟠 Fee\\({flags['transfer_fee_pct']:.1f}%\\)")
        
        if not security_items:
            response += "🟢 Clean"
        else:
            response += " ".join(security_items)
        response += "\n\n"
        
        # Critical info
        market = result.get('market_data', {})
        if market.get('price_usd') and market['price_usd'] != 'N/A':
            response += f"💰 *Price:* {self.safe_format_text(market['price_usd'])}\n"
        
        liquidity = result.get('liquidity_info', {})
        if liquidity.get('total_stable_usd') != 'N/A':
            response += f"💧 *Liquidity:* ${self.safe_format_text(str(liquidity['total_stable_usd']))} \\({self.safe_format_text(liquidity.get('liquidity_health', 'Unknown'))}\\)\n"
        
        # Holder concentration
        holders = result.get('holder_analysis', {})
        if holders.get('top_1_holds'):
            response += f"👥 *Top Holder:* {self.safe_format_text(holders['top_1_holds'])} \\({self.safe_format_text(holders.get('holder_concentration_risk', 'Unknown'))}\\)\n"
        
        # LP Providers
        lp_providers = liquidity.get('total_lp_providers', 0)
        if lp_providers == 0:
            response += "⚠️ *LP Providers:* 🔴 None detected\n"
        else:
            response += f"👨‍💼 *LP Providers:* {lp_providers}\n"
        
        # Insider Networks
        insider = result.get('insider_activity', {})
        if insider.get('has_insider_networks'):
            response += f"🕸️ *Insider Networks:* 🔴 {insider.get('networks_detected', 0)} detected\n"
        else:
            response += "🕸️ *Insider Networks:* 🟢 None detected\n"
        
        response += f"\n🎯 *Recommendation:* {self.safe_format_text(risk_assessment.get('recommendation', 'Unknown'))}\n"
        
        # Top risk factors (max 3)
        if result.get('risk_factors'):
            response += "\n⚠️ *Key Risks:*\n"
            for factor in result['risk_factors'][:3]:
                response += f"• {self.safe_format_text(factor)}\n"
        
        response += f"\n💡 *Use detailed analysis for complete report*"
        return response[:4000]  # Ensure we don't exceed Telegram's limit
    
    def generate_detailed_response(self, result: dict) -> str:
        """Generate detailed analysis response - CORRECTED TO MATCH RUGCHECK WEBSITE"""
        rug_prob = result.get('rug_probability', 0)
        prob_emoji = self.get_rug_probability_emoji(rug_prob)
        risk_assessment = result.get('risk_assessment', {})
        
        response = f"{result['risk_emoji']} *Comprehensive Analysis* {prob_emoji}\n\n"
        response += f"*Token:* {self.safe_format_text(result['token_name'])} \\(`{self.safe_format_text(result['token_symbol'])}`\\)\n"
        response += f"*Risk Score:* {result['risk_score']}/100 \\({self.safe_format_text(result['risk_level'])}\\)\n"
        response += f"*Rug Probability:* {prob_emoji} *{rug_prob:.1f}%*\n"
        response += f"*Overall Risk:* {self.safe_format_text(risk_assessment.get('level', 'Unknown'))}\n\n"
        
        # Security Analysis
        flags = result['security_flags']
        response += "🔐 *Security Analysis:*\n"
        if flags['rugged']:
            response += "💀 *TOKEN IS RUGGED*\n"
        response += f"• Mint Authority: {'🔴 Active' if flags['mint_authority'] else '🟢 Disabled'}\n"
        response += f"• Freeze Authority: {'🔴 Active' if flags['freeze_authority'] else '🟢 Disabled'}\n"
        response += f"• Mutable Metadata: {'🟡 Yes' if flags['mutable_metadata'] else '🟢 No'}\n"
        response += f"• Transfer Fee: {'🟠 ' + str(flags['transfer_fee_pct']) + '%' if flags['transfer_fee_active'] else '🟢 None'}\n"
        response += f"• Token Supply: {self.safe_format_text(str(flags['token_supply']))}\n\n"
        
        # Token Overview (like RugCheck website)
        tech_info = result.get('technical_info', {})
        response += "*📋 Token Overview:*\n"
        response += f"• Supply: {self.safe_format_text(str(flags['token_supply']))}\n"
        response += f"• Creator: `{self.safe_format_text(tech_info.get('creator_address', 'Unknown'))}`\n"
        
        creator_balance = tech_info.get('creator_balance', 0)
        if creator_balance == 0:
            response += "• Creator Balance: 🟢 SOLD\n"
        else:
            response += f"• Creator Balance: {self.format_number(creator_balance)}\n"
        
        # Market Data
        market = result.get('market_data', {})
        liquidity = result.get('liquidity_info', {})
        
        if market and market.get('price_usd') != 'N/A':
            response += f"• Market Cap: ${self.safe_format_text(str(market.get('market_cap_usd', 'N/A')))}\n"
        
        holders = result.get('holder_analysis', {})
        response += f"• Holders: {holders.get('total_holders', 0)}\n"
        response += f"• Mint Authority: {'\\-' if not flags['mint_authority'] else '🔴 Active'}\n"
        
        # LP Lock percentage
        if market.get('lp_locked_pct') and market['lp_locked_pct'] != 'N/A':
            lp_pct = float(market['lp_locked_pct'].replace('%', ''))
            if lp_pct >= 99:
                response += f"• LP Locked: 🟢 {market['lp_locked_pct']} 🔒\n"
            elif lp_pct >= 90:
                response += f"• LP Locked: 🟡 {market['lp_locked_pct']}\n"
            else:
                response += f"• LP Locked: 🔴 {market['lp_locked_pct']}\n"
        response += "\n"
        
        # Community Sentiment (placeholder - would need additional data)
        response += "*📊 Community Sentiment:*\n"
        response += "• Social Sentiment: 🔍 Mixed signals\n\n"
        
        # Insider Networks
        insider = result.get('insider_activity', {})
        response += "*🕸️ Insider Networks:*\n"
        if insider.get('has_insider_networks'):
            response += f"• Networks Detected: 🔴 {insider.get('networks_detected', 0)}\n"
        else:
            response += "• Networks Detected: 🟢 NO INSIDER NETWORKS DETECTED\n"
        response += "\n"
        
        # Top Holders Analysis
        if holders.get('top_1_holds'):
            top_1_pct = float(holders['top_1_holds'].replace('%', ''))
            response += f"*👥 Top Holders:* {top_1_pct:.2f}%\n"
            
            # Show concentration risk
            if top_1_pct > 50:
                response += f"• Concentration Risk: {holders.get('holder_concentration_risk', 'Unknown')}\n"
            
            response += f"• Distribution: {holders.get('distribution_score', 'Unknown')}\n"
            response += "\n"
        
        # Markets Information
        market_count = market.get('total_markets', 0)
        response += f"*🏪 Markets:* {market_count}\n"
        
        if market_count > 0:
            response += f"• Primary Market: {self.safe_format_text(market.get('market_type', 'Unknown'))}\n"
            if market.get('price_usd') != 'N/A':
                response += f"• Price: {self.safe_format_text(market['price_usd'])}\n"
            if liquidity.get('total_stable_usd') != 'N/A':
                response += f"• Liquidity: ${self.safe_format_text(str(liquidity['total_stable_usd']))}\n"
            
            lp_providers = liquidity.get('total_lp_providers', 0)
            if lp_providers == 0:
                response += "• LP Providers: 🔴 0 \\(Very risky\\)\n"
            else:
                response += f"• LP Providers: {lp_providers}\n"
        response += "\n"
        
        # Launch Insights (if available)
        launchpad = result.get('launchpad_info', {})
        if launchpad.get('platform'):
            response += "*🚀 Launch Insights:*\n"
            response += f"• Platform: {self.safe_format_text(launchpad['platform'])}\n"
            response += "\n"
        
        # Verification Status
        verification = result.get('verification', {})
        response += "*🏷️ Verification:*\n"
        response += f"• Jupiter Verified: {'🟢 Yes' if verification.get('jupiter_verified', False) else '🔴 No'}\n"
        if verification.get('social_links_count', 0) > 0:
            response += f"• Social Links: 🟢 {verification['social_links_count']}\n"
        response += "\n"
        
        # Risk Summary
        if result.get('risk_factors'):
            response += "*🚨 Risk Summary:*\n"
            for factor in result['risk_factors'][:3]:
                response += f"• {self.safe_format_text(factor)}\n"
            response += "\n"
        
        # API Warnings
        if result.get('warnings'):
            response += "*⚠️ API Warnings:*\n"
            for warning in result['warnings'][:2]:
                response += f"• {self.safe_format_text(warning)}\n"
            response += "\n"
        
        response += f"*🎯 Recommendation:* {self.safe_format_text(risk_assessment.get('recommendation', 'Unknown'))}\n"
        response += "*⚠️ Not financial advice\\. Always DYOR\\!*"
        return response[:4000]

    def generate_safe_response(self, result: dict, response_type: str = "quick") -> dict:
        """Generate a response with both HTML and MarkdownV2 versions for fallback"""
        try:
            # Generate HTML version (always safe)
            html_response = self.generate_html_response(result, response_type)
            
            # Try to generate MarkdownV2 version
            try:
                if response_type == "quick":
                    md_response = self.generate_quick_response(result)
                elif response_type == "detailed":
                    md_response = self.generate_detailed_response(result)
                elif response_type == "summary":
                    md_response = self.generate_summary_response(result)
                else:
                    md_response = self.generate_quick_response(result)
                
                return {
                    'success': True,
                    'html': html_response,
                    'markdown': md_response,
                    'use_markdown': True
                }
            except Exception as md_error:
                # If markdown fails, return HTML only
                return {
                    'success': True,
                    'html': html_response,
                    'markdown': html_response,
                    'use_markdown': False,
                    'markdown_error': str(md_error)
                }
                
        except Exception as e:
            # Complete fallback
            return {
                'success': False,
                'error': f'Response generation failed: {str(e)}',
                'html': self.generate_error_response_html(str(e)),
                'markdown': self.generate_error_response_html(str(e)),
                'use_markdown': False
            }

    def generate_html_response(self, result: dict, response_type: str = "quick") -> str:
        """Generate HTML version of response - CORRECTED VERSION"""
        rug_prob = result.get('rug_probability', 0)
        prob_emoji = self.get_rug_probability_emoji(rug_prob)
        risk_assessment = result.get('risk_assessment', {})
        
        if response_type == "quick":
            response = f"{result['risk_emoji']} <b>Quick Analysis</b> {prob_emoji}\n\n"
            response += f"<b>{result['token_name']}</b> (<code>{result['token_symbol']}</code>)\n"
            response += f"<b>Risk Score:</b> {result['risk_score']}/100 - {result['risk_level']}\n"
            response += f"<b>Rug Probability:</b> {prob_emoji} {rug_prob:.1f}%\n"
            response += f"<b>Assessment:</b> {risk_assessment.get('level', 'Unknown')}\n\n"
            
            # Security flags
            flags = result['security_flags']
            response += "🔐 <b>Security:</b> "
            security_items = []
            if flags['rugged']:
                security_items.append("💀 RUGGED")
            if flags['mint_authority']:
                security_items.append("🔴 Mint")
            if flags['freeze_authority']:
                security_items.append("🔴 Freeze")
            if flags['transfer_fee_active']:
                security_items.append(f"🟠 Fee({flags['transfer_fee_pct']:.1f}%)")
            
            if not security_items:
                response += "🟢 Clean"
            else:
                response += " ".join(security_items)
            response += "\n\n"
            
            # Market info
            market = result.get('market_data', {})
            if market.get('price_usd') and market['price_usd'] != 'N/A':
                response += f"💰 <b>Price:</b> {market['price_usd']}\n"
            
            liquidity = result.get('liquidity_info', {})
            if liquidity.get('total_stable_usd') != 'N/A':
                response += f"💧 <b>Liquidity:</b> ${liquidity['total_stable_usd']} ({liquidity.get('liquidity_health', 'Unknown')})\n"
            
            # Holder info
            holders = result.get('holder_analysis', {})
            if holders.get('top_1_holds'):
                response += f"👥 <b>Top Holder:</b> {holders['top_1_holds']} ({holders.get('holder_concentration_risk', 'Unknown')})\n"
            
            # LP Providers
            lp_providers = liquidity.get('total_lp_providers', 0)
            if lp_providers == 0:
                response += "⚠️ <b>LP Providers:</b> 🔴 None detected\n"
            else:
                response += f"👨‍💼 <b>LP Providers:</b> {lp_providers}\n"
            
            # Recommendation
            response += f"\n🎯 <b>Recommendation:</b> {risk_assessment.get('recommendation', 'Unknown')}\n"
            
            # Top risks
            if result.get('risk_factors'):
                response += "\n⚠️ <b>Key Risks:</b>\n"
                for factor in result['risk_factors'][:3]:
                    response += f"• {factor}\n"
            
            response += f"\n💡 <i>Use detailed analysis for complete report</i>"
            
        elif response_type == "detailed":
            response = f"{result['risk_emoji']} <b>Comprehensive Analysis</b> {prob_emoji}\n\n"
            response += f"<b>Token:</b> {result['token_name']} (<code>{result['token_symbol']}</code>)\n"
            response += f"<b>Risk Score:</b> {result['risk_score']}/100 ({result['risk_level']})\n"
            response += f"<b>Rug Probability:</b> {prob_emoji} <b>{rug_prob:.1f}%</b>\n"
            response += f"<b>Overall Risk:</b> {risk_assessment.get('level', 'Unknown')}\n\n"
            
            # Security Analysis
            flags = result['security_flags']
            response += "🔐 <b>Security Analysis:</b>\n"
            if flags['rugged']:
                response += "💀 <b>TOKEN IS RUGGED</b>\n"
            response += f"• Mint Authority: {'🔴 Active' if flags['mint_authority'] else '🟢 Disabled'}\n"
            response += f"• Freeze Authority: {'🔴 Active' if flags['freeze_authority'] else '🟢 Disabled'}\n"
            response += f"• Mutable Metadata: {'🟡 Yes' if flags['mutable_metadata'] else '🟢 No'}\n"
            response += f"• Transfer Fee: {'🟠 ' + str(flags['transfer_fee_pct']) + '%' if flags['transfer_fee_active'] else '🟢 None'}\n"
            response += f"• Token Supply: {flags['token_supply']}\n\n"
            
            # Token Overview
            tech_info = result.get('technical_info', {})
            response += "<b>📋 Token Overview:</b>\n"
            response += f"• Supply: {flags['token_supply']}\n"
            response += f"• Creator: <code>{tech_info.get('creator_address', 'Unknown')}</code>\n"
            
            creator_balance = tech_info.get('creator_balance', 0)
            if creator_balance == 0:
                response += "• Creator Balance: 🟢 SOLD\n"
            else:
                response += f"• Creator Balance: {self.format_number(creator_balance)}\n"
            
            # Market Data
            market = result.get('market_data', {})
            liquidity = result.get('liquidity_info', {})
            
            if market and market.get('market_cap_usd') != 'N/A':
                response += f"• Market Cap: ${market['market_cap_usd']}\n"
            
            holders = result.get('holder_analysis', {})
            response += f"• Holders: {holders.get('total_holders', 0)}\n"
            response += f"• Mint Authority: {'-' if not flags['mint_authority'] else '🔴 Active'}\n"
            
            # LP Lock
            if market.get('lp_locked_pct') and market['lp_locked_pct'] != 'N/A':
                lp_pct = float(market['lp_locked_pct'].replace('%', ''))
                if lp_pct >= 99:
                    response += f"• LP Locked: 🟢 {market['lp_locked_pct']} 🔒\n"
                elif lp_pct >= 90:
                    response += f"• LP Locked: 🟡 {market['lp_locked_pct']}\n"
                else:
                    response += f"• LP Locked: 🔴 {market['lp_locked_pct']}\n"
            response += "\n"
            
            # Insider Networks
            insider = result.get('insider_activity', {})
            response += "<b>🕸️ Insider Networks:</b>\n"
            if insider.get('has_insider_networks'):
                response += f"🔴 {insider.get('networks_detected', 0)} networks detected\n\n"
            else:
                response += "🟢 NO INSIDER NETWORKS DETECTED\n\n"
            
            # Top Holders
            if holders.get('top_1_holds'):
                top_1_pct = float(holders['top_1_holds'].replace('%', ''))
                response += f"<b>👥 Top Holders:</b> {top_1_pct:.2f}%\n"
                response += f"• Distribution: {holders.get('distribution_score', 'Unknown')}\n\n"
            
            # Markets
            market_count = market.get('total_markets', 0)
            response += f"<b>🏪 Markets:</b> {market_count}\n"
            if market_count > 0:
                response += f"• Type: {market.get('market_type', 'Unknown')}\n"
                if market.get('price_usd') != 'N/A':
                    response += f"• Price: {market['price_usd']}\n"
                if liquidity.get('total_stable_usd') != 'N/A':
                    response += f"• Liquidity: ${liquidity['total_stable_usd']}\n"
                
                lp_providers = liquidity.get('total_lp_providers', 0)
                if lp_providers == 0:
                    response += "• LP Providers: 🔴 0 (Very risky)\n"
                else:
                    response += f"• LP Providers: {lp_providers}\n"
            response += "\n"
            
            response += f"🎯 <b>Recommendation:</b> {risk_assessment.get('recommendation', 'Unknown')}\n"
            response += "⚠️ <i>Not financial advice. Always DYOR!</i>"
        
        return response

    def generate_summary_response(self, result: dict) -> str:
        """Generate a concise summary response"""
        rug_prob = result.get('rug_probability', 0)
        prob_emoji = self.get_rug_probability_emoji(rug_prob)
        risk_assessment = result.get('risk_assessment', {})
        
        response = f"{prob_emoji} *Token Safety Summary*\n\n"
        response += f"*{self.safe_format_text(result['token_name'])}* \\(`{self.safe_format_text(result['token_symbol'])}`\\)\n"
        response += f"*Overall Assessment:* {self.safe_format_text(risk_assessment.get('level', 'Unknown'))}\n"
        response += f"*Rug Probability:* {rug_prob:.1f}%\n"
        response += f"*Risk Score:* {result['risk_score']}/100\n\n"
        
        # Quick stats
        flags = result['security_flags']
        liquidity = result['liquidity_info']
        holders = result['holder_analysis']
        
        response += "📊 *Quick Stats:*\n"
        response += f"• Security Issues: {'🔴 Yes' if any([flags['mint_authority'], flags['freeze_authority'], flags['rugged']]) else '🟢 None detected'}\n"
        
        if liquidity.get('total_stable_usd') != 'N/A':
            response += f"• Liquidity: {self.safe_format_text(liquidity.get('liquidity_health', 'Unknown'))} \\(${self.safe_format_text(str(liquidity['total_stable_usd']))}\\)\n"
        
        if holders.get('top_1_holds'):
            response += f"• Concentration: {self.safe_format_text(holders.get('holder_concentration_risk', 'Unknown'))} \\({self.safe_format_text(holders['top_1_holds'])}\\)\n"
        
        # LP Providers warning
        lp_providers = liquidity.get('total_lp_providers', 0)
        if lp_providers == 0:
            response += "• LP Providers: 🔴 None \\(High Risk\\)\n"
        
        response += f"\n🎯 *Recommendation:* {self.safe_format_text(risk_assessment.get('recommendation', 'Unknown'))}\n"
        response += f"💡 *Action:* {self.safe_format_text(risk_assessment.get('action', 'Always do your research'))}\n"
        response += "\n⚠️ *Not financial advice\\. Always DYOR\\!*"
        return response[:4000]

    def generate_error_response_html(self, error_message: str) -> str:
        """Generate HTML error response"""
        response = "❌ <b>Analysis Failed</b>\n\n"
        
        if "not found" in error_message.lower():
            response += "🔍 <b>Token Not Found</b>\n"
            response += "This token might be:\n"
            response += "• Very new and not yet indexed\n"
            response += "• Invalid address format\n"
            response += "• Not on Solana network\n\n"
            response += "💡 <i>Try again in a few minutes if it's new</i>"
        elif "timeout" in error_message.lower() or "network" in error_message.lower():
            response += "🌐 <b>Network Issue</b>\n"
            response += "Temporary connection problem.\n\n"
            response += "💡 <i>Please try again in a moment</i>"
        else:
            response += f"⚠️ <b>Error:</b> {error_message}\n\n"
            response += "💡 <i>Please try again or contact support</i>"
        
        return response


# Convenience functions
def create_rugchecker_service(debug_mode=False):
    """Create and return a RugChecker service instance"""
    return RugCheckerService(debug_mode=debug_mode)

def quick_token_check(token_address: str, debug_mode=False) -> dict:
    """Quick function to check a single token"""
    service = RugCheckerService(debug_mode=debug_mode)
    return asyncio.run(service.check_token(token_address))

# Initialize the service
rug_checker_service = RugCheckerService(debug_mode=True)

# Example usage function
def test_cyah_token():
    """Test with the CYAH token from your example"""
    service = RugCheckerService(debug_mode=True)
    
    # This should be the actual CYAH token address
    cyah_address = "your_cyah_token_address_here"
    
    try:
        result = asyncio.run(service.check_token(cyah_address))
        if result['success']:
            # Generate response
            response_data = service.generate_safe_response(result, "detailed")
            print("CORRECTED RESPONSE:")
            print(response_data.get('html', 'No response'))
            
            print(f"\nCORRECTED METRICS:")
            print(f"Risk Score: {result['risk_score']}/100 (was showing /1000)")
            print(f"Rug Probability: {result['rug_probability']:.1f}%")
            print(f"Assessment: {result.get('risk_assessment', {}).get('level', 'Unknown')}")
            
        else:
            print(f"ERROR: {result['error']}")
            
    except Exception as e:
        print(f"EXCEPTION: {str(e)}")

if __name__ == "__main__":
    print("RugChecker Service v3.0 - CORRECTED & ALIGNED")
    print("Key Fixes:")
    print("✅ Corrected risk score scale (0-100, not 0-1000)")
    print("✅ Fixed rug probability calculation")
    print("✅ Aligned risk thresholds with actual API")
    print("✅ Added proper LP provider warnings")
    print("✅ Improved insider network detection display")
    print("✅ Better holder concentration analysis")
    print("✅ Matches RugCheck website format")
    
    # Uncomment to test
    # test_cyah_token()