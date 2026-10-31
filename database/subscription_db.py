"""
Subscription database service for the Meme Coin Analyzer Bot
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
from config.settings import SUPABASE_URL, SUPABASE_KEY
from config.logging_config import get_logger

logger = get_logger(__name__)

class SubscriptionDatabase:
    """Database service for subscription management"""
    
    def __init__(self):
        if SUPABASE_URL and SUPABASE_KEY:
            try:
                self.supabase: Optional[Client] = create_client(SUPABASE_URL, SUPABASE_KEY)
                logger.info("Subscription database initialized")
            except Exception as e:
                self.supabase = None
                logger.warning(f"Failed to initialize Supabase client: {e}")
        else:
            self.supabase = None
            logger.warning("Supabase credentials not configured. Subscription checks will default to inactive.")
    
    def is_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        if not self.supabase:
            return False
            
        try:
            response = self.supabase.from_('subscriptions').select('expiry').eq('user_id', user_id).limit(1).execute()
            
            if not response.data or len(response.data) == 0:
                return False
            
            try:
                expiry = datetime.fromisoformat(response.data[0]['expiry'].replace('Z', '+00:00'))
            except Exception as e:
                logger.error(f"Error parsing expiry date for user {user_id}: {e}")
                return False
            
            now = datetime.now(timezone.utc)
            return expiry > now
            
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            return False
    
    def activate_subscription(self, user_id: int, days: int = 30):
        """Activate subscription for user"""
        if not self.supabase:
            logger.warning("Supabase not configured; cannot activate subscription.")
            return
            
        try:
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(days=days)
            
            data = {
                'user_id': user_id,
                'subscribed_at': now.isoformat(),
                'expiry': expiry.isoformat()
            }
            
            self.supabase.from_('subscriptions').upsert(data).execute()
            logger.info(f"Subscription activated for user {user_id} until {expiry}")
            
        except Exception as e:
            logger.error(f"Error activating subscription for user {user_id}: {e}")
            raise
    
    def get_subscription_expiry(self, user_id: int) -> Optional[str]:
        """Get subscription expiry date for user"""
        if not self.supabase:
            return None
            
        try:
            response = self.supabase.from_('subscriptions').select('expiry').eq('user_id', user_id).limit(1).execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            return response.data[0]['expiry']
            
        except Exception as e:
            logger.error(f"Error getting subscription expiry for user {user_id}: {e}")
            return None
    
    def get_subscription_status(self, user_id: int) -> dict:
        """Get comprehensive subscription status for user"""
        if not self.supabase:
            return {
                'subscribed': False,
                'expiry': None,
                'days_left': 0,
                'status': 'Database Not Configured'
            }
            
        try:
            if not self.is_subscribed(user_id):
                return {
                    'subscribed': False,
                    'expiry': None,
                    'days_left': 0,
                    'status': 'Inactive'
                }
            
            expiry_iso = self.get_subscription_expiry(user_id)
            if not expiry_iso:
                return {
                    'subscribed': True,
                    'expiry': None,
                    'days_left': 0,
                    'status': 'Active (Unknown expiry)'
                }
            
            try:
                expiry_date = datetime.fromisoformat(expiry_iso.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                
                # Ensure both dates are timezone-aware
                if expiry_date.tzinfo is None:
                    expiry_date = expiry_date.replace(tzinfo=timezone.utc)
                
                time_diff = expiry_date - now
                days_left = time_diff.days
                hours_left = (time_diff.seconds // 3600) if days_left == 0 else 0
                
                # Determine status
                if days_left > 7:
                    status = "Active"
                elif days_left > 2:
                    status = "Active (Expiring Soon)"
                elif days_left > 0:
                    status = "Active (Expiring Today)"
                else:
                    status = "Expired"
                
                return {
                    'subscribed': True,
                    'expiry': expiry_iso,
                    'expiry_date': expiry_date,
                    'days_left': days_left,
                    'hours_left': hours_left,
                    'status': status
                }
                
            except Exception as e:
                logger.error(f"Error parsing expiry date: {e}")
                return {
                    'subscribed': True,
                    'expiry': expiry_iso,
                    'days_left': 0,
                    'status': 'Active (Date Error)'
                }
                
        except Exception as e:
            logger.error(f"Error getting subscription status for user {user_id}: {e}")
            return {
                'subscribed': False,
                'expiry': None,
                'days_left': 0,
                'status': 'Error'
            }
    
    def extend_subscription(self, user_id: int, days: int):
        """Extend existing subscription"""
        if not self.supabase:
            logger.warning("Supabase not configured; cannot extend subscription.")
            return
            
        try:
            current_expiry = self.get_subscription_expiry(user_id)
            
            if current_expiry:
                current_date = datetime.fromisoformat(current_expiry.replace('Z', '+00:00'))
                new_expiry = current_date + timedelta(days=days)
            else:
                now = datetime.now(timezone.utc)
                new_expiry = now + timedelta(days=days)
            
            data = {
                'user_id': user_id,
                'expiry': new_expiry.isoformat()
            }
            
            self.supabase.from_('subscriptions').upsert(data).execute()
            logger.info(f"Subscription extended for user {user_id} until {new_expiry}")
            
        except Exception as e:
            logger.error(f"Error extending subscription for user {user_id}: {e}")
            raise
    
    def cancel_subscription(self, user_id: int):
        """Cancel user subscription"""
        if not self.supabase:
            return
            
        try:
            self.supabase.from_('subscriptions').delete().eq('user_id', user_id).execute()
            logger.info(f"Subscription cancelled for user {user_id}")
            
        except Exception as e:
            logger.error(f"Error cancelling subscription for user {user_id}: {e}")
            raise
    
    def get_all_subscriptions(self) -> list:
        """Get all active subscriptions (admin function)"""
        if not self.supabase:
            return []
            
        try:
            response = self.supabase.from_('subscriptions').select('*').execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"Error getting all subscriptions: {e}")
            return []
    
    def cleanup_expired_subscriptions(self) -> int:
        """Clean up expired subscriptions"""
        if not self.supabase:
            return 0
            
        try:
            now = datetime.now(timezone.utc)
            response = self.supabase.from_('subscriptions').select('*').execute()
            
            if not response.data:
                return 0
            
            expired_count = 0
            for subscription in response.data:
                try:
                    expiry = datetime.fromisoformat(subscription['expiry'].replace('Z', '+00:00'))
                    if expiry < now:
                        self.supabase.from_('subscriptions').delete().eq('id', subscription['id']).execute()
                        expired_count += 1
                except Exception as e:
                    logger.warning(f"Error processing subscription {subscription.get('id')}: {e}")
            
            if expired_count > 0:
                logger.info(f"Cleaned up {expired_count} expired subscriptions")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired subscriptions: {e}")
            return 0

# Create global instance
subscription_db = SubscriptionDatabase()
