"""
Advanced rate limiter for managing user request limits
"""

import time
from typing import Dict, Tuple, Optional
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta
from config.settings import RATE_LIMIT_SECONDS, RATE_LIMIT_RUGCHECK_SECONDS
from config.logging_config import get_logger

logger = get_logger(__name__)

@dataclass
class RateLimitConfig:
    """Configuration for rate limiting"""
    max_requests: int
    time_window: float  # in seconds
    burst_limit: int = 1  # Allow burst of requests
    penalty_time: float = 0  # Additional penalty time for violations

class RateLimiter:
    """Advanced rate limiter with user-specific configurations"""
    
    def __init__(self):
        self.user_limits: Dict[int, RateLimitConfig] = {}
        self.user_requests: Dict[int, deque] = defaultdict(deque)
        self.user_violations: Dict[int, int] = defaultdict(int)
        self.user_penalties: Dict[int, float] = defaultdict(float)
        
        # Default rate limit configurations for t2.micro
        self.default_analysis_limit = RateLimitConfig(
            max_requests=3,  # Reduced from 5 for t2.micro
            time_window=60,  # 1 minute
            burst_limit=0,   # No burst for t2.micro
            penalty_time=120  # 2 minute penalty
        )

        self.default_rugcheck_limit = RateLimitConfig(
            max_requests=2,  # Reduced from 3 for t2.micro
            time_window=60,  # 1 minute
            burst_limit=0,   # No burst for t2.micro
            penalty_time=180  # 3 minute penalty
        )
    
    def set_user_limit(self, user_id: int, config: RateLimitConfig):
        """Set custom rate limit for a specific user"""
        self.user_limits[user_id] = config
        logger.info(f"Set rate limit for user {user_id}: {config.max_requests} requests per {config.time_window}s")
    
    def get_user_limit(self, user_id: int, request_type: str = "analysis") -> RateLimitConfig:
        """Get rate limit configuration for a user"""
        if user_id in self.user_limits:
            return self.user_limits[user_id]
        
        # Return default based on request type
        if request_type == "rugcheck":
            return self.default_rugcheck_limit
        else:
            return self.default_analysis_limit
    
    def can_make_request(self, user_id: int, request_type: str = "analysis") -> Tuple[bool, float]:
        """
        Check if user can make a request
        
        Returns:
            Tuple of (can_request, remaining_time)
        """
        config = self.get_user_limit(user_id, request_type)
        current_time = time.time()
        
        # Check if user is under penalty
        if user_id in self.user_penalties:
            penalty_end = self.user_penalties[user_id]
            if current_time < penalty_end:
                remaining_penalty = penalty_end - current_time
                return False, remaining_penalty
        
        # Get user's request history
        requests = self.user_requests[user_id]
        
        # Remove old requests outside the time window
        cutoff_time = current_time - config.time_window
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        # Check if user can make request
        if len(requests) < config.max_requests:
            return True, 0.0
        
        # Check burst limit
        if len(requests) < config.max_requests + config.burst_limit:
            # Allow burst but warn
            logger.warning(f"User {user_id} using burst limit for {request_type}")
            return True, 0.0
        
        # Calculate time until next request is allowed
        oldest_request = requests[0]
        next_allowed = oldest_request + config.time_window
        remaining_time = next_allowed - current_time
        
        return False, max(0.0, remaining_time)
    
    def record_request(self, user_id: int, request_type: str = "analysis"):
        """Record a user request"""
        current_time = time.time()
        requests = self.user_requests[user_id]
        requests.append(current_time)
        
        # Keep only recent requests (within 2x time window for safety)
        config = self.get_user_limit(user_id, request_type)
        cutoff_time = current_time - (config.time_window * 2)
        while requests and requests[0] < cutoff_time:
            requests.popleft()
        
        logger.debug(f"Recorded {request_type} request for user {user_id}")
    
    def record_violation(self, user_id: int, request_type: str = "analysis"):
        """Record a rate limit violation"""
        self.user_violations[user_id] += 1
        config = self.get_user_limit(user_id, request_type)
        
        # Apply penalty based on violation count
        violation_count = self.user_violations[user_id]
        penalty_multiplier = min(violation_count, 5)  # Cap at 5x
        
        penalty_time = config.penalty_time * penalty_multiplier
        if penalty_time > 0:
            self.user_penalties[user_id] = time.time() + penalty_time
            logger.warning(f"User {user_id} penalized for {penalty_time}s due to {violation_count} violations")
        
        logger.warning(f"Rate limit violation for user {user_id} ({request_type}): {violation_count} total violations")
    
    def reset_user_limits(self, user_id: int):
        """Reset rate limits for a user (remove penalties and violations)"""
        if user_id in self.user_requests:
            self.user_requests[user_id].clear()
        if user_id in self.user_violations:
            self.user_violations[user_id] = 0
        if user_id in self.user_penalties:
            del self.user_penalties[user_id]
        
        logger.info(f"Reset rate limits for user {user_id}")
    
    def get_user_status(self, user_id: int, request_type: str = "analysis") -> Dict:
        """Get detailed rate limit status for a user"""
        config = self.get_user_limit(user_id, request_type)
        current_time = time.time()
        
        # Check penalty status
        penalty_remaining = 0.0
        if user_id in self.user_penalties:
            penalty_end = self.user_penalties[user_id]
            if current_time < penalty_end:
                penalty_remaining = penalty_end - current_time
        
        # Get request count in current window
        requests = self.user_requests[user_id]
        cutoff_time = current_time - config.time_window
        current_requests = sum(1 for req_time in requests if req_time >= cutoff_time)
        
        # Check if can make request
        can_request, remaining_time = self.can_make_request(user_id, request_type)
        
        return {
            'user_id': user_id,
            'request_type': request_type,
            'can_make_request': can_request,
            'remaining_time': remaining_time,
            'current_requests': current_requests,
            'max_requests': config.max_requests,
            'time_window': config.time_window,
            'burst_limit': config.burst_limit,
            'penalty_remaining': penalty_remaining,
            'violation_count': self.user_violations.get(user_id, 0),
            'next_request_allowed': current_time + remaining_time if remaining_time > 0 else current_time
        }
    
    def get_global_stats(self) -> Dict:
        """Get global rate limiting statistics"""
        total_users = len(self.user_requests)
        total_violations = sum(self.user_violations.values())
        total_penalties = len([p for p in self.user_penalties.values() if p > time.time()])
        
        return {
            'total_users': total_users,
            'total_violations': total_violations,
            'active_penalties': total_penalties,
            'default_analysis_limit': {
                'max_requests': self.default_analysis_limit.max_requests,
                'time_window': self.default_analysis_limit.time_window
            },
            'default_rugcheck_limit': {
                'max_requests': self.default_rugcheck_limit.max_requests,
                'time_window': self.default_rugcheck_limit.time_window
            }
        }
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """Clean up old rate limiting data"""
        current_time = time.time()
        cutoff_time = current_time - (max_age_hours * 3600)
        
        # Clean up old requests
        for user_id in list(self.user_requests.keys()):
            requests = self.user_requests[user_id]
            # Remove old requests
            while requests and requests[0] < cutoff_time:
                requests.popleft()
            
            # Remove user if no recent activity
            if not requests:
                del self.user_requests[user_id]
        
        # Clean up expired penalties
        expired_penalties = [
            user_id for user_id, penalty_end in self.user_penalties.items()
            if penalty_end < current_time
        ]
        for user_id in expired_penalties:
            del self.user_penalties[user_id]
        
        if expired_penalties:
            logger.info(f"Cleaned up {len(expired_penalties)} expired penalties")

class RateLimitManager:
    """High-level rate limit manager for the bot"""
    
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.analysis_limits = defaultdict(lambda: RATE_LIMIT_SECONDS)
        self.rugcheck_limits = defaultdict(lambda: RATE_LIMIT_RUGCHECK_SECONDS)
    
    def check_analysis_limit(self, user_id: int) -> Tuple[bool, float]:
        """Check if user can perform analysis"""
        return self.rate_limiter.can_make_request(user_id, "analysis")
    
    def check_rugcheck_limit(self, user_id: int) -> Tuple[bool, float]:
        """Check if user can perform rugcheck"""
        return self.rate_limiter.can_make_request(user_id, "rugcheck")
    
    def record_analysis(self, user_id: int):
        """Record an analysis request"""
        self.rate_limiter.record_request(user_id, "analysis")
    
    def record_rugcheck(self, user_id: int):
        """Record a rugcheck request"""
        self.rate_limiter.record_request(user_id, "rugcheck")
    
    def record_violation(self, user_id: int, request_type: str = "analysis"):
        """Record a rate limit violation"""
        self.rate_limiter.record_violation(user_id, request_type)
    
    def reset_user_limits(self, user_id: int):
        """Reset rate limits for a user"""
        self.rate_limiter.reset_user_limits(user_id)
    
    def get_user_status(self, user_id: int) -> Dict:
        """Get comprehensive user status"""
        analysis_status = self.rate_limiter.get_user_status(user_id, "analysis")
        rugcheck_status = self.rate_limiter.get_user_status(user_id, "rugcheck")
        
        return {
            'user_id': user_id,
            'analysis': analysis_status,
            'rugcheck': rugcheck_status,
            'can_analyze': analysis_status['can_make_request'],
            'can_rugcheck': rugcheck_status['can_make_request'],
            'analysis_remaining': analysis_status['remaining_time'],
            'rugcheck_remaining': rugcheck_status['remaining_time']
        }
    
    def get_rate_limit_message(self, remaining_seconds: float, request_type: str = "analysis") -> str:
        """Generate user-friendly rate limit message"""
        if request_type == "rugcheck":
            if remaining_seconds > 20:
                minutes = int(remaining_seconds // 20)
                seconds = int(remaining_seconds % 20)
                return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{minutes}m {seconds}s</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
            else:
                return f"⏱️ <b>RugCheck rate limit active</b>\n\nNext rugcheck available in: <b>{int(remaining_seconds)} seconds</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
        else:
            if remaining_seconds > 60:
                minutes = int(remaining_seconds // 60)
                seconds = int(remaining_seconds % 60)
                return f"⏱️ <b>Rate limit active</b>\n\nNext analysis available in: <b>{minutes}m {seconds}s</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"
            else:
                return f"⏱️ <b>Rate limit active</b>\n\nNext analysis available in: <b>{int(remaining_seconds)} seconds</b>\n\n💡 <i>This prevents overload and ensures quality analysis for all users</i>"

# Create global instance
rate_limit_manager = RateLimitManager()
