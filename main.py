from telegram.ext import ApplicationBuilder, CommandHandler ,CallbackQueryHandler
from subscription_manager import is_subscribed, activate_subscription, get_subscription_expiry
from solana_checker import verify_transaction
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from datetime import datetime, timezone, timedelta
from paste import generate_analysis
import re
from telegram.helpers import escape_markdown
from telegram import InputFile
import pytz
import asyncio
import sys
import platform
import logging
import time
import html
from collections import defaultdict
from rug_checker_service import rug_checker_service

# Set up logging with Railway optimization
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(sys.stdout)  # Railway logging optimization
    ]
)
logger = logging.getLogger(__name__)

# Configuration
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

PAYMENT_AMOUNT = os.getenv("PAYMENT_AMOUNT", "0.2 SOL")
PAYMENT_WALLET = os.getenv("PAYMENT_WALLET", "")
GROUP_LINK = os.getenv("GROUP_LINK", "")
GROUP_NAME = os.getenv("GROUP_NAME", "Tentia Coin Alerts")


# Rate limiting configuration
RATE_LIMIT_SECONDS = 20  # 20 seconds between analyses for premium users
user_last_analysis = defaultdict(float)  # Track last analysis time per user

# Rate limiting for rug checker (separate from analyze)
user_last_rugcheck = defaultdict(float)  # Track last rugcheck time per user

def check_rugcheck_rate_limit(user_id):
    """Check if user can perform rugcheck (rate limiting)"""
    current_time = time.time()
    last_rugcheck = user_last_rugcheck[user_id]
    time_passed = current_time - last_rugcheck
    
    if time_passed >= RATE_LIMIT_SECONDS:
        user_last_rugcheck[user_id] = current_time
        return True, 0
    else:
        remaining_time = RATE_LIMIT_SECONDS - time_passed
        return False, int(remaining_time)

def get_rugcheck_rate_limit_message(remaining_seconds):
    """Get user-friendly rate limit message for rugcheck"""
    if remaining_seconds > 20:
        minutes = remaining_seconds // 20
        seconds = remaining_seconds % 20
        return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{minutes}m {seconds}s</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
    else:
        return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{remaining_seconds} seconds</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"

def check_rate_limit(user_id):
    """Check if user can perform analysis (rate limiting)"""
    current_time = time.time()
    last_analysis = user_last_analysis[user_id]
    time_passed = current_time - last_analysis
    
    if time_passed >= RATE_LIMIT_SECONDS:
        user_last_analysis[user_id] = current_time
        return True, 0
    else:
        remaining_time = RATE_LIMIT_SECONDS - time_passed
        return False, int(remaining_time)

def get_rate_limit_message(remaining_seconds):
    """Get user-friendly rate limit message"""
    if remaining_seconds > 60:
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        return f"⏱️ <b>Rate limit active</b>\n\nNext analysis available in: <b>{minutes}m {seconds}s</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
    else:
        return f"⏱️ <b>Rate limit active</b>\n\nNext analysis available in: <b>{remaining_seconds} seconds</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"

def safe_html_escape(text):
    """Safely escape HTML characters and handle None values"""
    if text is None or text == "N/A":
        return "N/A"
    return html.escape(str(text))

def safe_get_escaped(data, key, default="N/A"):
    """Get data and escape HTML characters"""
    value = data.get(key, default) if data.get(key) is not None else default
    return safe_html_escape(value)

# NEW: Callback Query Handler for Subscribe Button
async def button_callback(update, context):
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
            f"<code>{PAYMENT_WALLET}</code>\n\n"
            "2. Copy your transaction hash\n"
            "3. Use: <code>/verify [transaction_hash]</code>\n\n"
            "⚡ Instant activation after verification\n\n"
            "💡 <i>Note: Small deviations due to transaction fees (0.1999, 0.2001) are accepted</i>"
        )
        await query.edit_message_text(subscribe_message, parse_mode='HTML')

# Start Command - Fixed HTML parsing issue
async def start(update, context):
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

# Subscribe Command - Updated with fee tolerance info
async def subscribe(update, context):
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
            f"<code>{PAYMENT_WALLET}</code>\n\n"
            "2. Copy your transaction hash\n"
            "3. Use: <code>/verify [transaction_hash]</code>\n\n"
            "⚡ Instant activation after verification\n\n"
            "💡 <i>Note: Small deviations due to transaction fees (0.1999, 0.2001) are accepted</i>"
        )
        await update.message.reply_text(subscribe_message, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Subscribe command error: {e}")
        await update.message.reply_text("Service temporarily unavailable. Please retry.")

# Verify Command - Updated to accept transaction fee variations
async def verify(update, context):
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

        # Updated verification logic to accept transaction fee variations
        verification_result = await verify_transaction(txn_signature)
        
        if verification_result:
            activate_subscription(user_id)
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

# Analyze Command - Just use the existing format_analysis_output from paste.py
# Analyze Command - ONLY COMMAND WITH RATE LIMITING
async def analyze(update, context):
    try:
        user_id = update.effective_user.id
        
        # Check subscription first
        if not is_subscribed(user_id):
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

        # RATE LIMIT CHECK - ONLY FOR ANALYZE FUNCTION
        can_analyze, remaining_time = check_rate_limit(user_id)
        if not can_analyze:
            rate_limit_msg = check_rate_limit(remaining_time)
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

        # Optimized analysis call with timeout
        try:
            analysis = await asyncio.wait_for(generate_analysis(token_address), timeout=30.0)
        except asyncio.TimeoutError:
            await progress_msg.edit_text(
                "⏱️ <b>Analysis timeout</b>\n\n"
                "Token analysis took too long.\n"
                "Please try again with a different token.\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            # Reset rate limit on timeout to be user-friendly
            user_last_analysis[user_id] = 0
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
            user_last_analysis[user_id] = 0
            return

        if not analysis or not isinstance(analysis, dict):
            await progress_msg.edit_text(
                "❌ <b>Analysis failed</b>\n\n"
                "Unable to retrieve token data. Check address and retry.\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            # Reset rate limit on error
            user_last_analysis[user_id] = 0
            return

        def safe_get(data, key, default="N/A"):
            return str(data.get(key, default)) if data.get(key) is not None else default


        # Clean, focused output with proper HTML escaping
        response_msg = f"""📊 <b>TOKEN ANALYSIS</b>

🪙 <b>{safe_get_escaped(analysis, 'token_name')} ({safe_get_escaped(analysis, 'token_symbol')})</b>
<code>{safe_get_escaped(analysis, 'token_address')}</code>

💰 <b>Price Data</b>
Current: <code>{safe_get_escaped(analysis, 'price')}</code>
24h Change: <b>{safe_get_escaped(analysis, 'price_change_24h')}</b>
Market Cap: <b>{safe_get_escaped(analysis, 'market_cap')}</b>
Liquidity: <b>{safe_get_escaped(analysis, 'liquidity')}</b>

📈 <b>Trading Activity</b>
Volume 24h: <b>{safe_get_escaped(analysis, 'volume_24h')}</b>
Buys: <b>{safe_get_escaped(analysis, 'buys_24h')}</b> | Sells: <b>{safe_get_escaped(analysis, 'sells_24h')}</b>
Buy/Sell Ratio: <b>{safe_get_escaped(analysis, 'buy_sell_ratio')}</b>
Total Trades: <b>{safe_get_escaped(analysis, 'total_trades_24h')}</b>

🎯 <b>Technical Indicators</b>
RSI: <b>{safe_get_escaped(analysis, 'rsi')}</b>
Momentum: <b>{safe_get_escaped(analysis, 'momentum')}</b>
Volume Profile: <b>{safe_get_escaped(analysis, 'volume_profile')}</b>
Volatility: <b>{safe_get_escaped(analysis, 'volatility')}</b>

📊 <b>Key Levels</b>
Support: <code>{safe_get_escaped(analysis, 'support_level')}</code>
Resistance: <code>{safe_get_escaped(analysis, 'resistance_level')}</code>

📋 <b>Assessment</b>
Confidence: <b>{safe_get_escaped(analysis, 'confidence_score')}</b>
Risk Level: <b>{safe_get_escaped(analysis, 'rug_risk_level')}</b>
Position Size: <b>{safe_get_escaped(analysis, 'position_size')}</b>
Rug Risk: <b>{safe_get_escaped(analysis, 'rug_probability')}</b>
Rug Status: <b>{safe_get_escaped(analysis, 'rug_status')}</b>

⚡ <b>FINAL VERDICT</b>
<b>{safe_get_escaped(analysis, 'final_verdict')}</b>

🎯 <b>Entry Strategy</b>
{safe_get_escaped(analysis, 'entry_strategy')}

💭 <b>Analysis Summary</b>
{safe_get_escaped(analysis, 'reasoning')}

<i>📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}</i>
⏱️ <i>Next analysis available in 20 seconds</i>"""

# 3. ADD BETTER ERROR HANDLING TO THE MESSAGE SENDING:
        try:
            # Try HTML first
            await progress_msg.edit_text(response_msg, parse_mode="HTML", disable_web_page_preview=True)
        except Exception as html_error:
            logger.error(f"HTML parsing failed: {html_error}")
            # Fallback to plain text
            try:
                plain_msg = f"""TOKEN ANALYSIS

Token: {safe_get(analysis, 'token_name')} ({safe_get(analysis, 'token_symbol')})
Address: {safe_get(analysis, 'token_address')}

Price: {safe_get(analysis, 'price')}
24h Change: {safe_get(analysis, 'price_change_24h')}
Market Cap: {safe_get(analysis, 'market_cap')}
Liquidity: {safe_get(analysis, 'liquidity')}

Volume 24h: {safe_get(analysis, 'volume_24h')}
RSI: {safe_get(analysis, 'rsi')}
Risk Level: {safe_get(analysis, 'rug_risk_level')}

Final Verdict: {safe_get(analysis, 'final_verdict')}

Next analysis available in 20 seconds"""
                
                await progress_msg.edit_text(plain_msg)
            except Exception as plain_error:
                logger.error(f"Plain text also failed: {plain_error}")
                await progress_msg.edit_text("Analysis completed but display error occurred. Please try again.")

        dex_link = analysis.get('dex_link')
        if dex_link and dex_link != "N/A":
            response_msg += f"\n\n🔗 <a href=\"{dex_link}\">View Chart</a>"

        await progress_msg.edit_text(response_msg, parse_mode="HTML", disable_web_page_preview=True)
        
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
            user_last_analysis[user_id] = 0
        except Exception as edit_error:
            logger.error(f"Error handling analysis error: {edit_error}")
            
async def quick(update, context):
    """Handle /rugcheck_quick command for brief rug analysis"""
    try:
        user_id = update.effective_user.id
        
        # Check subscription first
        if not is_subscribed(user_id):
            keyboard = [[InlineKeyboardButton("💎 Subscribe Now", callback_data="subscribe")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔒 <b>Premium RugCheck feature</b>\n\n"
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
        can_analyze, remaining_time = check_rugcheck_rate_limit(user_id)
        if not can_analyze:
            rate_limit_msg = get_rugcheck_rate_limit_message(remaining_time)
            await update.message.reply_text(rate_limit_msg, parse_mode='HTML')
            return

        if not context.args:
            await update.message.reply_text(
                '📋 <b>Token address required</b>\n\n'
                '<b>Format:</b> <code>/rugcheck_quick [TOKEN_ADDRESS]</code>\n\n'
                '<b>Example:</b>\n'
                '<code>/rugcheck_quick EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v</code>\n\n'
                'Find addresses on DexScreener, Jupiter, or Raydium.\n\n'
                '⏱️ <i>Rate limit: 1 rugcheck per 20 seconds</i>',
                parse_mode='HTML'
            )
            return

        token_address = context.args[0]
        
        # Validate address format
        if not rug_checker_service.validate_solana_address(token_address):
            await update.message.reply_text(
                "❌ <b>Invalid Solana address format</b>\n\n"
                "Please provide a valid base58 address (32-44 characters).\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            check_rugcheck_rate_limit[user_id] = 0  # Reset rate limit on error
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
            result = await rug_checker_service.check_token(token_address)
        except Exception as e:
            await progress_msg.edit_text(
                "⏱️ <b>RugCheck timeout</b>\n\n"
                "Token analysis took too long.\n"
                "Please try again with a different token.\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            check_rugcheck_rate_limit[user_id] = 0  # Reset rate limit on timeout
            return

        if not result['success']:
            await progress_msg.edit_text(
                f"❌ <b>RugCheck failed</b>\n\n"
                f"<b>Error:</b> {result['error']}\n\n"
                f"<b>Try this:</b>\n"
                f"• Check token address is correct\n"
                f"• Token might be too new\n"
                f"• Retry in a few minutes\n\n"
                f"💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            check_rugcheck_rate_limit[user_id] = 0  # Reset rate limit on error
            return

        # Generate safe response with fallback
        response_data = rug_checker_service.generate_safe_response(result, "quick")
        response_text = response_data['html']  # Use HTML version
        response_text += f"\n\n⏱️ <i>Next rugcheck available in 20 seconds</i>"
        
        # Try to send with HTML (always safe)
        try:
            await progress_msg.edit_text(
                response_text, 
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        except Exception as send_error:
            # Final fallback - plain text
            logger.error(f"HTML send failed: {send_error}")
            plain_response = f"Quick RugCheck Analysis\n\n"
            plain_response += f"Token: {result['token_name']} ({result['token_symbol']})\n"
            plain_response += f"Risk Score: {result['risk_score']}/1000\n"
            plain_response += f"Rug Probability: {result['rug_probability']}%\n\n"
            plain_response += f"Next rugcheck available in 20 seconds"
            
            await progress_msg.edit_text(plain_response)
        
    except Exception as e:
        logger.error(f"RugCheck quick error: {e}")
        try:
            if 'progress_msg' in locals():
                await progress_msg.edit_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on error
        except Exception as edit_error:
            logger.error(f"Error handling rugcheck error: {edit_error}")

async def rugcheck(update, context):
    """Handle /rugcheck command for detailed rug analysis"""
    try:
        user_id = update.effective_user.id
        
        # Check subscription first
        if not is_subscribed(user_id):
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
        can_analyze, remaining_time = check_rugcheck_rate_limit(user_id)
        if not can_analyze:
            rate_limit_msg = get_rugcheck_rate_limit_message(remaining_time)
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
        if not rug_checker_service.validate_solana_address(token_address):
            await update.message.reply_text(
                "❌ <b>Invalid Solana address format</b>\n\n"
                "Please provide a valid base58 address (32-44 characters).\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on error
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
            result = await rug_checker_service.check_token(token_address)
        except Exception as e:
            await progress_msg.edit_text(
                "⏱️ <b>RugCheck timeout</b>\n\n"
                "Token analysis took too long.\n"
                "Please try again with a different token.\n\n"
                "💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on timeout
            return

        if not result['success']:
            await progress_msg.edit_text(
                f"❌ <b>RugCheck failed</b>\n\n"
                f"<b>Error:</b> {result['error']}\n\n"
                f"<b>Try this:</b>\n"
                f"• Check token address is correct\n"
                f"• Token might be too new\n"
                f"• Retry in a few minutes\n\n"
                f"💡 <i>Your rate limit timer has been reset</i>",
                parse_mode='HTML'
            )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on error
            return

        # Generate safe response
        response_data = rug_checker_service.generate_safe_response(result, "detailed")
        response_text = response_data['html']
        response_text += f"\n\n⏱️ <i>Next rugcheck available in 20 seconds</i>"
        
        # Send response (split if too long for HTML)
        if len(response_text) > 4096:
            parts = [response_text[i:i+4000] for i in range(0, len(response_text), 4000)]
            await progress_msg.edit_text(parts[0], parse_mode='HTML')
            for part in parts[1:]:
                await update.message.reply_text(part, parse_mode='HTML')
        else:
            await progress_msg.edit_text(
                response_text, 
                parse_mode='HTML',
                disable_web_page_preview=True
            )
        
    except Exception as e:
        logger.error(f"RugCheck detailed error: {e}")
        try:
            if 'progress_msg' in locals():
                await progress_msg.edit_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on error
        except Exception as edit_error:
            logger.error(f"Error handling rugcheck error: {edit_error}")

        
    except Exception as e:
        logger.error(f"RugCheck risk error: {e}")
        try:
            if 'progress_msg' in locals():
                await progress_msg.edit_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            else:
                await update.message.reply_text(
                    '❌ <b>RugCheck error</b>\n\n'
                    'Technical issue occurred.\n'
                    'Please retry with different token.\n\n'
                    '💡 <i>Your rate limit timer has been reset</i>',
                    parse_mode='HTML'
                )
            user_last_rugcheck[user_id] = 0  # Reset rate limit on error
        except Exception as edit_error:
            logger.error(f"Error handling rugcheck error: {edit_error}")

# Group Command - Updated to emphasize alpha calls and coin spotting
async def group(update, context):
    try:
        user_id = update.effective_user.id

        if not is_subscribed(user_id):
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
        
        keyboard = [[InlineKeyboardButton("🚀 Join Alerts Group", url=GROUP_LINK)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = (
            f"🔥 <b>EXCLUSIVE COIN ALERTS GROUP</b>\n\n"
            f"📊 <b>{GROUP_NAME}</b>\n\n"
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

# Status Command - Improved date handling with updated messaging
async def status(update, context):
    try:
        user_id = update.effective_user.id

        if is_subscribed(user_id):
            expiry_iso = get_subscription_expiry(user_id)
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
                can_analyze, remaining_time = check_rate_limit(user_id)
                rate_status = "✅ Ready" if can_analyze else f"⏱️ {remaining_time}s remaining"
                
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
                    f"• 🚨 Coin alets group access\n"
                    f"• 💎 New coin spotting alerts\n\n"
                )
                
                if days_left <= 2:
                    status_message += "⚠️ <b>Renewal reminder:</b> Subscription expires soon!"
                else:
                    status_message += "🚀 Enjoy your premium features!"

                await update.message.reply_text(status_message, parse_mode='HTML')
                
            except Exception as date_error:
                logger.error(f"Date parsing error: {date_error}")
                can_analyze, remaining_time = check_rate_limit(user_id)
                rate_status = "✅ Ready" if can_analyze else f"⏱️ {remaining_time}s remaining"
                
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

# Help Command - Updated with rate limit info and alpha calls messaging
async def help_command(update, context):
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
            "/rugcheck [address] - Rugcheck analysis (1 per 20s)\n"
            "/quick [address] - Short Rugcheck (1 per 20s)\n\n"
            "💎 <b>Premium Features</b>\n"
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

# Enhanced error handler for Railway
async def error_handler(update, context):
    """Log errors caused by Updates."""
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

# Set up bot commands with enhanced error handling
async def setup_application(app):
    """Setup the application with commands and handlers"""
    try:
        commands = [
            BotCommand("start", "🚀 Bot overview"),
            BotCommand("subscribe", "💎 Premium access"),
            BotCommand("verify", "✅ Verify payment"), 
            BotCommand("status", "📊 Subscription & rate limits"),
            BotCommand("analyze", "🔍 Analyze tokens (1 per 20s)"),
            BotCommand("rugcheck", "🚨 Detailed rug analysis"),           # NEW
            BotCommand("quick", "⚡ Quick rug check"),           # NEW
            BotCommand("group", "🚨 Coin alerts group"),
            BotCommand("help", "❓ Commands guide")
        ]
        await app.bot.set_my_commands(commands)
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("subscribe", subscribe))
        app.add_handler(CommandHandler("verify", verify))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("analyze", analyze))
        app.add_handler(CommandHandler("rugcheck", rugcheck))
        app.add_handler(CommandHandler("quick", quick))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("group", group))
        
        # CRITICAL: Add the missing CallbackQueryHandler
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_error_handler(error_handler)
        
        
        logger.info("All handlers registered successfully")
        
    except Exception as e:
        logger.error(f"Error setting up application: {e}")
        raise

def main():
    """Alternative main function with proper timeout configuration"""
    print("🚀 Advanced Meme Coin Analyzer Bot - Starting...")
    print(f"Platform: {platform.system()}")
    print("Analysis engine loaded ⚡")
    print("Premium features ready 💎")
    print("Rate limiting active ⏱️")
    print("Bot ready for token analysis 📊")
    
    # Railway environment optimization
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        # Use environment variable for token in production
        import os
        token = os.getenv('TELEGRAM_BOT_TOKEN') or os.getenv('BOT_TOKEN', '')
        if not token:
            logger.error("TELEGRAM_BOT_TOKEN is not set.")
            print("❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
            return
        
        # Configure timeouts via ApplicationBuilder
        app = (ApplicationBuilder()
               .token(token)
               .connect_timeout(30)
               .read_timeout(30)
               .write_timeout(30)
               .build())
        
        print("Setting up bot services...")
        
        async def initialize_and_run():
            try:
                await app.initialize()
                await setup_application(app)
                
                print("✅ Bot configured successfully!")
                print("🚀 Starting polling... Bot is LIVE!")
                print("📱 Users can now interact with the bot!")
                print("⏱️ Rate limiting: 1 analysis per 20 seconds for premium users")
                print("\n💡 Press Ctrl+C to stop\n")
                
                await app.start()
                # Clean start_polling call without invalid parameters
                await app.updater.start_polling(drop_pending_updates=True)
                await asyncio.Event().wait()
                
            except Exception as e:
                logger.error(f"Error during bot execution: {e}")
                raise
            finally:
                try:
                    if hasattr(app, 'updater') and app.updater.running:
                        await app.updater.stop()
                    if app.running:
                        await app.stop()
                    await app.shutdown()
                except Exception as cleanup_error:
                    logger.error(f"Error during cleanup: {cleanup_error}")
        
        try:
            asyncio.run(initialize_and_run())
        except KeyboardInterrupt:
            print("\n🛑 Bot shutdown requested...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            print(f"❌ Error: {e}")
        finally:
            print("✅ Bot stopped cleanly")
              
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        print(f"❌ Startup failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check module installations:")
        print("   pip install python-telegram-bot")
        print("2. Verify paste.py exists")
        print("3. Check subscription_manager.py")
        print("4. Confirm solana_checker.py works")

if __name__ == '__main__':
    main()  # or use main_with_timeouts() for the alternative approach