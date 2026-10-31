"""
Refactored Main Bot for the Meme Coin Analyzer Bot
Uses the new modular architecture with concurrent processing
"""

import asyncio
import platform
import sys
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone
import html

# Import from new architecture
from config.settings import (
    BOT_TOKEN, PAYMENT_AMOUNT, PAYMENT_WALLET, GROUP_LINK, GROUP_NAME,
    RATE_LIMIT_SECONDS, RATE_LIMIT_RUGCHECK_SECONDS
)
from config.logging_config import get_logger
from services.analysis_service import token_analysis_service
from concurrent_processing.rate_limiter import rate_limit_manager
from database.subscription_db import subscription_db
from solana_checker import verify_transaction

logger = get_logger(__name__)

class MemeCoinAnalyzerBot:
    """Main bot class with refactored architecture"""
    
    def __init__(self):
        self.token = BOT_TOKEN
        self.payment_amount = PAYMENT_AMOUNT
        self.payment_wallet = PAYMENT_WALLET
        self.group_link = GROUP_LINK
        self.group_name = GROUP_NAME
        self.rate_limit_seconds = RATE_LIMIT_SECONDS
        self.rate_limit_rugcheck_seconds = RATE_LIMIT_RUGCHECK_SECONDS
        
        # Initialize services
        self.analysis_service = token_analysis_service
        self.rate_limit_manager = rate_limit_manager
        self.subscription_db = subscription_db
        
        # Import rug checker service
        from services.rug_checker import rug_checker_service
        self.rug_checker = rug_checker_service
        
        # Bot application
        self.app = None
    
    async def start_concurrent_services(self):
        """Start concurrent processing services"""
        try:
            await self.analysis_service.concurrent_processor.start()
            logger.info("Concurrent processor started successfully")
        except Exception as e:
            logger.error(f"Failed to start concurrent processor: {e}")
    
    async def stop_concurrent_services(self):
        """Stop concurrent processing services"""
        try:
            await self.analysis_service.concurrent_processor.stop()
            logger.info("Concurrent processor stopped successfully")
        except Exception as e:
            logger.error(f"Failed to stop concurrent processor: {e}")
    
    def safe_html_escape(self, text):
        """Safely escape HTML characters and handle None values"""
        if text is None or text == "N/A":
            return "N/A"
        return html.escape(str(text))
    
    def safe_get_escaped(self, data, key, default="N/A"):
        """Get data and escape HTML characters"""
        value = data.get(key, default) if data.get(key) is not None else default
        return self.safe_html_escape(value)
    
    async def button_callback(self, update, context):
        """Handle callback queries from inline keyboards"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "subscribe":
            subscribe_message = (
                "💎 <b>Premium Subscription</b>\n\n"
                "<b>What you get:</b>\n"
                "• Advanced momentum scoring\n"
                "• Multi-timeframe analysis\n"
                "• Volume surge detection\n"
                "• Smart risk assessment\n"
                "• Exclusive coin alerts group\n"
                "• Unlimited analysis (1 per 20 seconds)\n\n"
                "💰 <b>Cost:</b> 0.2 SOL (transaction fees acceptable)\n\n"
                "<b>How to subscribe:</b>\n"
                "1. Send approximately 0.2 SOL to:\n"
                f"<code>{self.payment_wallet}</code>\n\n"
                "2. Copy your transaction hash\n"
                "3. Use: <code>/verify [transaction_hash]</code>\n\n"
                "⚡ Instant activation after verification\n\n"
                "💡 <i>Note: Small deviations due to transaction fees (0.1999, 0.2001) are accepted</i>"
            )
            await query.edit_message_text(subscribe_message, parse_mode='HTML')
    
    async def start(self, update, context):
        """Start command handler"""
        try:
            welcome_message = (
                "🚀 <b>Advanced Meme Coin Analyzer</b>\n\n"
                "<b>Core Features:</b>\n"
                "• Technical analysis with smart signals\n"
                "• Real-time momentum tracking\n"
                "• Risk assessment and scoring\n"
                "• Volume surge detection\n\n"
                "<b>Quick Start:</b>\n"
                "/subscribe - Get premium access\n"
                "/analyze &lt;token_address&gt; - Analyze any token\n"
                "/group - Join our coin alerts group\n\n"
                "Ready to analyze your next trade? 📈"
            )
            await update.message.reply_text(welcome_message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Start command error: {e}")
            await update.message.reply_text("Service temporarily unavailable. Please retry.")
    
    async def subscribe(self, update, context):
        """Subscribe command handler"""
        try:
            subscribe_message = (
                "💎 <b>Premium Subscription</b>\n\n"
                "<b>What you get:</b>\n"
                "• Advanced momentum scoring\n"
                "• Multi-timeframe analysis\n"
                "• Volume surge detection\n"
                "• Smart risk assessment\n"
                "• Exclusive coin alerts group\n"
                "• Unlimited analysis (1 per 20 seconds)\n\n"
                "💰 <b>Cost:</b> 0.2 SOL (transaction fees acceptable)\n\n"
                "<b>How to subscribe:</b>\n"
                "1. Send approximately 0.2 SOL to:\n"
                f"<code>{self.payment_wallet}</code>\n\n"
                "2. Copy your transaction hash\n"
                "3. Use: <code>/verify [transaction_hash]</code>\n\n"
                "⚡ Instant activation after verification\n\n"
                "💡 <i>Note: Small deviations due to transaction fees (0.1999, 0.2001) are accepted</i>"
            )
            await update.message.reply_text(subscribe_message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Subscribe command error: {e}")
            await update.message.reply_text("Service temporarily unavailable. Please retry.")
    
    async def verify(self, update, context):
        """Verify command handler"""
        try:
            user_id = update.effective_user.id

            if not context.args:
                await update.message.reply_text(
                    '❌ <b>Transaction hash required</b>\n\n'
                    '<b>Format:</b>\n'
                    '<code>/verify [transaction_hash]</code>\n\n'
                    '<b>Find your hash in:</b>\n'
                    '• Your Solana wallet history\n'
                    '• Solscan.io transaction details\n'
                    '• Wallet confirmation receipt\n\n'
                    '💡 <i>Transaction fees are acceptable (0.1999-0.2001 SOL)</i>',
                    parse_mode='HTML'
                )
                return

            txn_signature = context.args[0]
            
            verification_msg = await update.message.reply_text(
                '🔍 <b>Verifying transaction...</b>\n'
                'Please wait a moment...',
                parse_mode='HTML'
            )

            # Use the existing verification logic
            verification_result = await verify_transaction(txn_signature)
            
            if verification_result:
                self.subscription_db.activate_subscription(user_id)
                await verification_msg.edit_text(
                    '✅ <b>Subscription activated!</b>\n\n'
                    'Welcome to premium features.\n\n'
                    '<b>Available now:</b>\n'
                    '• /analyze - Advanced token analysis (1 per 20 seconds)\n'
                    '• /group - Coin alerts group\n\n'
                    'Happy trading! 📊',
                    parse_mode='HTML'
                )
            else:
                await verification_msg.edit_text(
                    '❌ <b>Verification failed</b>\n\n'
                    '<b>Common issues:</b>\n'
                    '• Wrong transaction hash\n'
                    '• Amount not approximately 0.2 SOL\n'
                    '• Wrong recipient address\n'
                    '• Transaction still pending\n\n'
                    'Double-check and try again.\n\n'
                    '💡 <i>Acceptable range: 0.19-0.21 SOL (includes transaction fees)</i>',
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Verification error: {e}")
            await update.message.reply_text(
                '⚠️ <b>Verification error</b>\n\n'
                'Please retry in a few minutes.\n'
                'Contact support if issue persists.',
                parse_mode='HTML'
            )
    
    async def analyze(self, update, context):
        """Analyze command handler with new architecture"""
        try:
            user_id = update.effective_user.id
            
            # Check subscription first
            if not self.subscription_db.is_subscribed(user_id):
                keyboard = [[InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔒 <b>Premium feature</b>\n\n"
                    "Advanced analysis requires subscription.\n\n"
                    "<b>Get access to:</b>\n"
                    "• Smart momentum scoring\n"
                    "• Volume surge detection\n"
                    "• Risk assessment tools\n"
                    "• Entry/exit strategies\n"
                    "• Unlimited analysis (1 per 20 seconds)\n\n"
                    "💰 Only 0.2 SOL",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                return

            # Check rate limit
            can_analyze, remaining_time = self.rate_limit_manager.check_analysis_limit(user_id)
            if not can_analyze:
                rate_limit_msg = self.rate_limit_manager.get_rate_limit_message(remaining_time, "analysis")
                await update.message.reply_text(rate_limit_msg, parse_mode='HTML')
                return

            if not context.args:
                await update.message.reply_text(
                    '📋 <b>Token address required</b>\n\n'
                    '<b>Format:</b> <code>/analyze [TOKEN_ADDRESS]</code>\n\n'
                    '<b>Example:</b>\n'
                    '<code>/analyze EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v</code>\n\n'
                    'Find addresses on DexScreener, Jupiter, or Raydium.\n\n'
                    '⏱️ <i>Rate limit: 1 analysis per 20 seconds</i>',
                    parse_mode='HTML'
                )
                return

            token_address = context.args[0]
            
            progress_msg = await update.message.reply_text(
                '🔍 <b>Analyzing token...</b>\n\n'
                '📊 Fetching market data...\n'
                '📈 Calculating indicators...\n'
                '🧮 Processing signals...\n\n'
                '⏳ <i>This takes 5-10 seconds</i>',
                parse_mode='HTML'
            )

            # Use the new analysis service
            try:
                analysis = await self.analysis_service.analyze_token(token_address, user_id)
            except Exception as e:
                logger.error(f"Analysis error: {e}")
                await progress_msg.edit_text(
                    "❌ <b>Analysis failed</b>\n\n"
                    f"<b>Error:</b> {str(e)}\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                # Reset rate limit on error to be user-friendly
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            if isinstance(analysis, str):
                await progress_msg.edit_text(
                    f"❌ <b>Analysis failed</b>\n\n"
                    f"<b>Error:</b> {analysis}\n\n"
                    f"<b>Try this:</b>\n"
                    f"• Check token address is correct\n"
                    f"• Token might be too new\n"
                    f"• Retry in a few minutes\n\n"
                    f"💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                # Reset rate limit on error to be user-friendly
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            # Convert AnalysisResult to dict for backward compatibility
            if hasattr(analysis, 'to_dict'):
                analysis_dict = analysis.to_dict()
            else:
                analysis_dict = analysis

            # Generate response message
            response_msg = self._generate_analysis_response(analysis_dict)
            
            # Send response
            try:
                await progress_msg.edit_text(response_msg, parse_mode="HTML", disable_web_page_preview=True)
            except Exception as html_error:
                logger.error(f"HTML parsing failed: {html_error}")
                # Fallback to plain text
                plain_msg = self._generate_plain_text_response(analysis_dict)
                await progress_msg.edit_text(plain_msg)
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            try:
                if 'progress_msg' in locals():
                    await progress_msg.edit_text(
                        '❌ <b>Analysis error</b>\n\n'
                        'Technical issue occurred.\n'
                        'Please retry with different token.\n\n'
                        '💡 <i>Your rate limit timer has been reset</i>',
                        parse_mode='HTML'
                    )
                else:
                    await update.message.reply_text(
                        '❌ <b>Analysis error</b>\n\n'
                        'Technical issue occurred.\n'
                        'Please retry with different token.\n\n'
                        '💡 <i>Your rate limit timer has been reset</i>',
                        parse_mode='HTML'
                    )
                # Reset rate limit on error
                self.rate_limit_manager.reset_user_limits(user_id)
            except Exception as edit_error:
                logger.error(f"Error handling analysis error: {edit_error}")
    
    def _generate_analysis_response(self, analysis: dict) -> str:
        """Generate HTML response for analysis"""
        return f"""📊 <b>TOKEN ANALYSIS</b>

🪙 <b>{self.safe_get_escaped(analysis, 'token_name')} ({self.safe_get_escaped(analysis, 'token_symbol')})</b>
<code>{self.safe_get_escaped(analysis, 'token_address')}</code>

💰 <b>Price Data</b>
Current: <code>{self.safe_get_escaped(analysis, 'price')}</code>
24h Change: <b>{self.safe_get_escaped(analysis, 'price_change_24h')}</b>
Market Cap: <b>{self.safe_get_escaped(analysis, 'market_cap')}</b>
Liquidity: <b>{self.safe_get_escaped(analysis, 'liquidity')}</b>

📈 <b>Trading Activity</b>
Volume 24h: <b>{self.safe_get_escaped(analysis, 'volume_24h')}</b>
Buys: <b>{self.safe_get_escaped(analysis, 'buys_24h')}</b> | Sells: <b>{self.safe_get_escaped(analysis, 'sells_24h')}</b>
Buy/Sell Ratio: <b>{self.safe_get_escaped(analysis, 'buy_sell_ratio')}</b>
Total Trades: <b>{self.safe_get_escaped(analysis, 'total_trades_24h')}</b>

🎯 <b>Technical Indicators</b>
RSI: <b>{self.safe_get_escaped(analysis, 'rsi')}</b>
Momentum: <b>{self.safe_get_escaped(analysis, 'momentum')}</b>
Volume Profile: <b>{self.safe_get_escaped(analysis, 'volume_profile')}</b>
Volatility: <b>{self.safe_get_escaped(analysis, 'volatility')}</b>

📊 <b>Key Levels</b>
Support: <code>{self.safe_get_escaped(analysis, 'support_level')}</code>
Resistance: <code>{self.safe_get_escaped(analysis, 'resistance_level')}</code>

📋 <b>Assessment</b>
Confidence: <b>{self.safe_get_escaped(analysis, 'confidence_score')}</b>
Risk Level: <b>{self.safe_get_escaped(analysis, 'risk_level')}</b>
Position Size: <b>{self.safe_get_escaped(analysis, 'position_size')}</b>
Rug Risk: <b>{self.safe_get_escaped(analysis, 'rug_probability')}</b>
Rug Status: <b>{self.safe_get_escaped(analysis, 'rug_status')}</b>

⚡ <b>FINAL VERDICT</b>
<b>{self.safe_get_escaped(analysis, 'final_verdict')}</b>

🎯 <b>Entry Strategy</b>
{self.safe_get_escaped(analysis, 'entry_strategy')}

💭 <b>Analysis Summary</b>
{self.safe_get_escaped(analysis, 'reasoning')}

<i>📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>
⏱️ <i>Next analysis available in 20 seconds</i>"""
    
    def _generate_plain_text_response(self, analysis: dict) -> str:
        """Generate plain text response for analysis"""
        return f"""TOKEN ANALYSIS

Token: {analysis.get('token_name', 'Unknown')} ({analysis.get('token_symbol', 'Unknown')})
Address: {analysis.get('token_address', 'Unknown')}

Price: {analysis.get('price', 'N/A')}
24h Change: {analysis.get('price_change_24h', 'N/A')}
Market Cap: {analysis.get('market_cap', 'N/A')}
Liquidity: {analysis.get('liquidity', 'N/A')}

Volume 24h: {analysis.get('volume_24h', 'N/A')}
RSI: {analysis.get('rsi', 'N/A')}
Risk Level: {analysis.get('risk_level', 'N/A')}

Final Verdict: {analysis.get('final_verdict', 'N/A')}

Next analysis available in 20 seconds"""
    
    async def status(self, update, context):
        """Status command handler"""
        try:
            user_id = update.effective_user.id

            if self.subscription_db.is_subscribed(user_id):
                expiry_iso = self.subscription_db.get_subscription_expiry(user_id)
                try:
                    expiry_date = datetime.fromisoformat(expiry_iso)
                    now = datetime.now(timezone.utc)
                    
                    # Ensure both dates are timezone-aware
                    if expiry_date.tzinfo is None:
                        expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                    
                    time_diff = expiry_date - now
                    days_left = time_diff.days
                    hours_left = (time_diff.seconds // 3600) if days_left == 0 else 0

                    status_emoji = "🟢" if days_left > 7 else "🟡" if days_left > 2 else "🔴"
                    
                    # Check rate limit status
                    can_analyze, remaining_time = self.rate_limit_manager.check_analysis_limit(user_id)
                    rate_status = "✅ Ready" if can_analyze else f"⏱️ {int(remaining_time)}s remaining"
                    
                    status_message = (
                        f"{status_emoji} <b>SUBSCRIPTION STATUS</b>\n\n"
                        f"✅ <b>Status:</b> ACTIVE\n"
                        f"📅 <b>Expires:</b> {expiry_date.strftime('%Y-%m-%d %H:%M UTC')}\n"
                        f"⏰ <b>Time left:</b> {days_left} days"
                    )
                    
                    if days_left == 0:
                        status_message += f", {hours_left} hours"
                    
                    status_message += (
                        f"\n🔍 <b>Analysis:</b> {rate_status}\n\n"
                        f"🎯 <b>Active features:</b>\n"
                        f"• 📊 Advanced token analysis\n"
                        f"• 🚨 Coin alerts group access\n"
                        f"• 💎 New coin spotting alerts\n\n"
                    )
                    
                    if days_left <= 2:
                        status_message += "⚠️ <b>Renewal reminder:</b> Subscription expires soon!"
                    else:
                        status_message += "🚀 Enjoy your premium features!"

                    await update.message.reply_text(status_message, parse_mode='HTML')
                    
                except Exception as date_error:
                    logger.error(f"Date parsing error: {date_error}")
                    can_analyze, remaining_time = self.rate_limit_manager.check_analysis_limit(user_id)
                    rate_status = "✅ Ready" if can_analyze else f"⏱️ {int(remaining_time)}s remaining"
                    
                    await update.message.reply_text(
                        "✅ <b>SUBSCRIPTION STATUS</b>\n\n"
                        "Status: ACTIVE\n"
                        "Unable to display expiry date.\n"
                        f"🔍 <b>Analysis:</b> {rate_status}\n\n"
                        "🚀 All premium features available!",
                        parse_mode='HTML'
                    )
                
            else:
                keyboard = [[InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "❌ <b>No active subscription</b>\n\n"
                    "<b>Premium features available:</b>\n"
                    "• 📊 Advanced analysis with signals\n"
                    "• 🎯 Smart trading recommendations\n"
                    "• 🚨 Coin alerts group access\n"
                    "• ⏱️ Unlimited analysis (1 per 20 seconds)\n\n"
                    "💰 <b>Only 0.2 SOL for full access</b>",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
        except Exception as e:
            logger.error(f"Status error: {e}")
            await update.message.reply_text("Service temporarily unavailable. Please retry.")
    
    async def group(self, update, context):
        """Group command handler"""
        try:
            user_id = update.effective_user.id

            if not self.subscription_db.is_subscribed(user_id):
                await update.message.reply_text(
                    "🔒 <b>Exclusive Coin alerts group</b>\n\n"
                    "<b>Premium group features:</b>\n"
                    "• 🚨 Real-time pump alerts\n"
                    "• 💎 New coin spotting alerts\n"
                    "• 📊 Potential gem discoveries\n"
                    "• 🎯 Early entry signals\n"
                    "• 📈 High-potential token alerts\n\n"
                    "💎 Subscribe to access alpha calls.",
                    parse_mode='HTML'
                )
                return
            
            keyboard = [[InlineKeyboardButton("🚀 Join Alerts Group", url=self.group_link)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            message_text = (
                f"🔥 <b>EXCLUSIVE COIN ALERTS GROUP</b>\n\n"
                f"📊 <b>{self.group_name}</b>\n\n"
                f"<b>What you get:</b>\n"
                f"• 🚨 Instant pump alerts\n"
                f"• 💎 New coin spotting alerts\n"
                f"• 📈 High-potential token discoveries\n"
                f"• 🎯 Early entry opportunities\n"
                f"• 🔍 Gem identification signals\n"
                f"• ⚡ Real-time market alerts\n\n"
                f"Ready to catch the next gem? 💎"
            )
            
            await update.message.reply_text(
                message_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Group command error: {e}")
            await update.message.reply_text("Service temporarily unavailable. Please retry.")
    
    async def help_command(self, update, context):
        """Help command handler"""
        try:
            help_message = (
                "🤖 <b>MEME COIN ANALYZER - COMMANDS</b>\n\n"
                "🚀 <b>Getting Started</b>\n"
                "/start - Bot overview\n"
                "/subscribe - Get premium access (0.2 SOL)\n"
                "/verify [hash] - Activate subscription\n"
                "/status - Check subscription & rate limits\n\n"
                "📊 <b>Analysis</b>\n"
                "/analyze [address] - Token analysis (1 per 20s)\n"
                "/group - Coin alerts\n\n"
                "❓ <b>Support</b>\n"
                "/help - This guide\n\n"
                "<b>Analysis includes:</b>\n"
                "• Smart momentum scoring\n"
                "• Volume surge detection\n"
                "• Risk assessment\n"
                "• Entry/exit strategies\n"
                "• Real-time market data\n\n"
                "⏱️ <b>Rate Limits:</b>\n"
                "• Premium: 1 analysis per 20 seconds\n"
                "• Free: No access to analysis\n\n"
                "💡 <b>Payment Info:</b>\n"
                "• Transaction fees acceptable (0.1999-0.2001 SOL)\n\n"
                "Ready to find your next gem? 💎"
            )
            await update.message.reply_text(help_message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Help command error: {e}")
            await update.message.reply_text("Service temporarily unavailable. Please retry.")
    
    def _get_rugcheck_rate_limit_message(self, remaining_seconds):
        """Get user-friendly rate limit message for rugcheck"""
        if remaining_seconds > 20:
            minutes = remaining_seconds // 20
            seconds = remaining_seconds % 20
            return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{minutes}m {seconds}s</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
        else:
            return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{remaining_seconds} seconds</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
    
    def _validate_solana_address(self, address):
        """Validate Solana address format"""
        import re
        # Solana addresses are base58 encoded, 32-44 characters
        pattern = r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'
        return bool(re.match(pattern, address))
    
    async def is_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        try:
            return self.subscription_db.is_subscribed(user_id)
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            return False
    
    async def rugcheck(self, update, context):
        """Handle /rugcheck command for detailed rug analysis"""
        try:
            user_id = update.effective_user.id
            
            # Check subscription first
            if not await self.is_subscribed(user_id):
                keyboard = [[InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔒 <b>Premium RugCheck feature</b>\n\n"
                    "Comprehensive rug analysis requires subscription.\n\n"
                    "<b>Get detailed insights on:</b>\n"
                    "• Complete security analysis\n"
                    "• Market & liquidity data\n"
                    "• Holder distribution patterns\n"
                    "• Verification status\n"
                    "• Insider activity detection\n"
                    "• Technical token details\n\n"
                    "💰 Only 0.2 SOL",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                return

            # Check rate limit for premium users
            can_analyze, remaining_time = self.rate_limit_manager.check_rugcheck_limit(user_id)
            if not can_analyze:
                rate_limit_msg = self._get_rugcheck_rate_limit_message(remaining_time)
                await update.message.reply_text(rate_limit_msg, parse_mode='HTML')
                return

            if not context.args:
                await update.message.reply_text(
                    '📋 <b>Token address required</b>\n\n'
                    '<b>Format:</b> <code>/rugcheck [TOKEN_ADDRESS]</code>\n\n'
                    '<b>Example:</b>\n'
                    '<code>/rugcheck EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v</code>\n\n'
                    'Find addresses on DexScreener, Jupiter, or Raydium.\n\n'
                    '⏱️ <i>Rate limit: 1 rugcheck per 20 seconds</i>',
                    parse_mode='HTML'
                )
                return

            token_address = context.args[0]
            
            # Validate address format
            if not self._validate_solana_address(token_address):
                await update.message.reply_text(
                    "❌ <b>Invalid Solana address format</b>\n\n"
                    "Please provide a valid base58 address (32-44 characters).\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return
            
            progress_msg = await update.message.reply_text(
                '🔍 <b>Comprehensive RugCheck Analysis...</b>\n\n'
                '🚨 Deep scanning for rug risks...\n'
                '🔒 Comprehensive security audit...\n'
                '📊 Market & liquidity analysis...\n'
                '👥 Holder distribution study...\n'
                '🕵️ Insider activity detection...\n\n'
                '⏳ <i>This takes 10-15 seconds</i>',
                parse_mode='HTML'
            )

            try:
                result = await self.rug_checker.check_token(token_address)
            except Exception as e:
                await progress_msg.edit_text(
                    "⏱️ <b>RugCheck timeout</b>\n\n"
                    "Token analysis took too long.\n"
                    "Please try again with a different token.\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            if not result.get('success'):
                await progress_msg.edit_text(
                    f"❌ <b>RugCheck failed</b>\n\n"
                    f"<b>Issue:</b> Unable to analyze this token\n\n"
                    f"<b>Try this:</b>\n"
                    f"• Check token address is correct\n"
                    f"• Token might be too new\n"
                    f"• Retry in a few minutes\n\n"
                    f"💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            # Generate safe response
            response_data = self.rug_checker.generate_safe_response(result, "detailed")
            response_text = response_data.get('html', 'Analysis completed')
            
            # Send the response
            try:
                await progress_msg.edit_text(response_text, parse_mode='HTML')
            except Exception as send_error:
                # Fallback to plain text if HTML fails
                await progress_msg.edit_text(
                    "✅ <b>RugCheck completed</b>\n\n"
                    "Analysis finished successfully.\n\n"
                    "💡 <i>Next rugcheck available in 20 seconds</i>",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Rugcheck command error: {e}")
            await update.message.reply_text(
                "⚠️ Service temporarily unavailable. Please try again later.",
                parse_mode='HTML'
            )
    
    async def quick(self, update, context):
        """Handle /quick command for brief rug analysis"""
        try:
            user_id = update.effective_user.id
            
            # Check subscription first
            if not await self.is_subscribed(user_id):
                keyboard = [[InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔒 <b>Premium Quick Check feature</b>\n\n"
                    "Advanced rug analysis requires subscription.\n\n"
                    "<b>Get access to:</b>\n"
                    "• Smart rug probability scoring\n"
                    "• Security flags detection\n"
                    "• Holder concentration analysis\n"
                    "• Liquidity risk assessment\n"
                    "• Insider activity detection\n\n"
                    "💰 Only 0.2 SOL",
                    parse_mode='HTML',
                    reply_markup=reply_markup
                )
                return

            # Check rate limit for premium users
            can_analyze, remaining_time = self.rate_limit_manager.check_rugcheck_limit(user_id)
            if not can_analyze:
                rate_limit_msg = self._get_rugcheck_rate_limit_message(remaining_time)
                await update.message.reply_text(rate_limit_msg, parse_mode='HTML')
                return

            if not context.args:
                await update.message.reply_text(
                    '📋 <b>Token address required</b>\n\n'
                    '<b>Format:</b> <code>/quick [TOKEN_ADDRESS]</code>\n\n'
                    '<b>Example:</b>\n'
                    '<code>/quick EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v</code>\n\n'
                    'Find addresses on DexScreener, Jupiter, or Raydium.\n\n'
                    '⏱️ <i>Rate limit: 1 quick check per 20 seconds</i>',
                    parse_mode='HTML'
                )
                return

            token_address = context.args[0]
            
            # Validate address format
            if not self._validate_solana_address(token_address):
                await update.message.reply_text(
                    "❌ <b>Invalid Solana address format</b>\n\n"
                    "Please provide a valid base58 address (32-44 characters).\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return
            
            progress_msg = await update.message.reply_text(
                '🔍 <b>Quick RugCheck Analysis...</b>\n\n'
                '🚨 Checking rug probability...\n'
                '🔒 Analyzing security flags...\n'
                '👥 Evaluating holder concentration...\n\n'
                '⏳ <i>This takes 5-10 seconds</i>',
                parse_mode='HTML'
            )

            try:
                result = await self.rug_checker.check_token(token_address)
            except Exception as e:
                await progress_msg.edit_text(
                    "⏱️ <b>Quick Check timeout</b>\n\n"
                    "Token analysis took too long.\n"
                    "Please try again with a different token.\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            if not result.get('success'):
                await progress_msg.edit_text(
                    f"❌ <b>Quick Check failed</b>\n\n"
                    f"<b>Issue:</b> Unable to analyze this token\n\n"
                    f"<b>Try this:</b>\n"
                    f"• Check token address is correct\n"
                    "• Token might be too new\n"
                    "• Retry in a few minutes\n\n"
                    "💡 <i>Your rate limit timer has been reset</i>",
                    parse_mode='HTML'
                )
                self.rate_limit_manager.reset_user_limits(user_id)
                return

            # Generate safe response with fallback
            response_data = self.rug_checker.generate_safe_response(result, "quick")
            response_text = response_data.get('html', 'Quick check completed')
            response_text += f"\n\n⏱️ <i>Next quick check available in 20 seconds</i>"
            
            # Send the response
            try:
                await progress_msg.edit_text(response_text, parse_mode='HTML')
            except Exception as send_error:
                # Fallback to plain text if HTML fails
                await progress_msg.edit_text(
                    "✅ <b>Quick Check completed</b>\n\n"
                    "Analysis finished successfully.\n\n"
                    "💡 <i>Next quick check available in 20 seconds</i>",
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Quick command error: {e}")
            await update.message.reply_text(
                "⚠️ Service temporarily unavailable. Please try again later.",
                parse_mode='HTML'
            )
    
    async def error_handler(self, update, context):
        """Error handler for the bot"""
        logger.error(f'Update {update} caused error {context.error}')
        
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="⚠️ An error occurred. Please try again.",
                    parse_mode='HTML'
                )
            except Exception as send_error:
                logger.error(f"Failed to send error message: {send_error}")
    
    async def setup_application(self):
        """Setup the application with commands and handlers"""
        try:
            commands = [
                BotCommand("start", "🚀 Bot overview"),
                BotCommand("subscribe", "💎 Premium access"),
                BotCommand("verify", "✅ Verify payment"), 
                BotCommand("status", "📊 Subscription & rate limits"),
                BotCommand("analyze", "🔍 Analyze tokens (1 per 20s)"),
                BotCommand("rugcheck", "🚨 Detailed rug analysis"),
                BotCommand("quick", "⚡ Quick rug check"),
                BotCommand("group", "🚨 Coin alerts group"),
                BotCommand("help", "❓ Commands guide")
            ]
            await self.app.bot.set_my_commands(commands)
            
            # Add handlers
            self.app.add_handler(CommandHandler("start", self.start))
            self.app.add_handler(CommandHandler("subscribe", self.subscribe))
            self.app.add_handler(CommandHandler("verify", self.verify))
            self.app.add_handler(CommandHandler("status", self.status))
            self.app.add_handler(CommandHandler("analyze", self.analyze))
            self.app.add_handler(CommandHandler("rugcheck", self.rugcheck))
            self.app.add_handler(CommandHandler("quick", self.quick))
            self.app.add_handler(CommandHandler("help", self.help_command))
            self.app.add_handler(CommandHandler("group", self.group))
            
            # Add callback query handler
            self.app.add_handler(CallbackQueryHandler(self.button_callback))
            self.app.add_error_handler(self.error_handler)
            
            logger.info("All handlers registered successfully")
            
        except Exception as e:
            logger.error(f"Error setting up application: {e}")
            raise
    
    async def run(self):
        """Run the bot"""
        if not self.token:
            logger.error("BOT_TOKEN is not set. Set TELEGRAM_BOT_TOKEN in .env or environment.")
            print("❌ Error: TELEGRAM_BOT_TOKEN is not set.")
            return

        try:
            # Start concurrent services
            await self.start_concurrent_services()
            
            # Create application
            self.app = (ApplicationBuilder()
                       .token(self.token)
                       .connect_timeout(30)
                       .read_timeout(30)
                       .write_timeout(30)
                       .build())
            
            # Setup application
            await self.setup_application()
            
            logger.info("✅ Bot configured successfully!")
            logger.info("🚀 Starting polling... Bot is LIVE!")
            logger.info("📱 Users can now interact with the bot!")
            logger.info("⏱️ Rate limiting: 1 analysis per 20 seconds for premium users")
            logger.info("🔄 Concurrent processing: Unlimited users supported")
            
            # Start the bot
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(drop_pending_updates=True)
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot shutdown requested...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            raise
        finally:
            # Stop concurrent services
            await self.stop_concurrent_services()
            
            # Stop bot
            if self.app:
                try:
                    if hasattr(self.app, 'updater') and self.app.updater.running:
                        await self.app.updater.stop()
                    if self.app.running:
                        await self.app.stop()
                    await self.app.shutdown()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
            
            logger.info("✅ Bot stopped cleanly")

def main():
    """Main function"""
    print("🚀 Advanced Meme Coin Analyzer Bot - Starting...")
    print(f"Platform: {platform.system()}")
    print("New Architecture: Modular & Concurrent ⚡")
    print("Analysis engine loaded 📊")
    print("Premium features ready 💎")
    print("Rate limiting active ⏱️")
    print("Unlimited concurrent users supported 🔄")
    print("Bot ready for token analysis 🚀")
    
    # Railway environment optimization
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        # Create and run bot
        bot = MemeCoinAnalyzerBot()
        asyncio.run(bot.run())
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Startup failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check module installations:")
        print("   pip install python-telegram-bot")
        print("2. Verify all new architecture files exist")
        print("3. Check configuration in config/settings.py")
        print("4. Ensure original files are accessible")

if __name__ == '__main__':
    main()
