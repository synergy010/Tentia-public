import os
from datetime import datetime, timezone, timedelta
from typing import Optional
from supabase import create_client, Client

try:
    from config.settings import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

supabase: Optional[Client] = (
    create_client(SUPABASE_URL, SUPABASE_KEY) if (SUPABASE_URL and SUPABASE_KEY) else None
)

def is_subscribed(user_id: int) -> bool:
    if not supabase:
        return False

    try:
        response = supabase.from_('subscriptions').select('expiry').eq('user_id', user_id).limit(1).execute()

        if not response.data or len(response.data) == 0:
            return False

        try:
            expiry = datetime.fromisoformat(response.data[0]['expiry'].replace('Z', '+00:00'))
        except Exception:
            return False

        now = datetime.now(timezone.utc)
        return expiry > now
    except Exception:
        return False

def activate_subscription(user_id: int, days: int = 30):
    if not supabase:
        return

    now = datetime.now(timezone.utc)
    expiry = now + timedelta(days=days)

    data = {
        'user_id': user_id,
        'subscribed_at': now.isoformat(),
        'expiry': expiry.isoformat()
    }

    supabase.from_('subscriptions').upsert(data).execute()

def get_subscription_expiry(user_id: int) -> Optional[str]:
    if not supabase:
        return None

    try:
        response = supabase.from_('subscriptions').select('expiry').eq('user_id', user_id).limit(1).execute()

        if not response.data or len(response.data) == 0:
            return None

        return response.data[0]['expiry']
    except Exception:
        return None
