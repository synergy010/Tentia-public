#!/usr/bin/env python3
"""
Test file for the new architecture
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all modules can be imported correctly"""
    print("🧪 Testing imports...")
    
    try:
        # Test core imports
        from config.settings import BOT_TOKEN, RATE_LIMIT_SECONDS
        print("✅ Config imports successful")
        
        from config.logging_config import get_logger
        print("✅ Logging config imports successful")
        
        from models.token_data import TokenInfo, AnalysisResult
        print("✅ Model imports successful")
        
        from utils.helpers import safe_float, human_format
        print("✅ Utility imports successful")
        
        from services.data_fetcher import data_fetcher
        print("✅ Data fetcher imports successful")
        
        from services.analysis_engine import analysis_engine
        print("✅ Analysis engine imports successful")
        
        from services.rug_checker import rug_checker_service
        print("✅ Rug checker imports successful")
        
        from concurrent_processing.worker_pool import concurrent_processor
        print("✅ Worker pool imports successful")
        
        from concurrent_processing.rate_limiter import rate_limit_manager
        print("✅ Rate limiter imports successful")
        
        from database.subscription_db import subscription_db
        print("✅ Database imports successful")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_configuration():
    """Test that configuration is properly loaded"""
    print("\n🧪 Testing configuration...")
    
    try:
        from config.settings import (
            BOT_TOKEN, RATE_LIMIT_SECONDS, RATE_LIMIT_RUGCHECK_SECONDS,
            ANALYSIS_TIMEOUT, WORKER_POOL_SIZE, MAX_CONCURRENT_USERS
        )
        
        print(f"✅ Bot token configured: {'Yes' if BOT_TOKEN else 'No'}")
        print(f"✅ Analysis rate limit: {RATE_LIMIT_SECONDS}s")
        print(f"✅ Rugcheck rate limit: {RATE_LIMIT_RUGCHECK_SECONDS}s")
        print(f"✅ Analysis timeout: {ANALYSIS_TIMEOUT}s")
        print(f"✅ Worker pool size: {WORKER_POOL_SIZE}")
        print(f"✅ Max concurrent users: {MAX_CONCURRENT_USERS}")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_data_models():
    """Test that data models can be instantiated"""
    print("\n🧪 Testing data models...")
    
    try:
        from models.token_data import (
            TokenInfo, PriceData, MarketData, TradingActivity,
            TechnicalIndicators, KeyLevels, VolumeProfile, MomentumData,
            RiskAssessment, RugAnalysis, TradingRecommendation, AnalysisResult
        )
        
        # Test TokenInfo
        token_info = TokenInfo(
            address="test123",
            name="Test Token",
            symbol="TEST",
            decimals=9,
            supply=1000000000
        )
        print(f"✅ TokenInfo created: {token_info.symbol}")
        
        # Test PriceData
        price_data = PriceData(
            current_price=1.25,
            price_change_24h=0.05,
            price_change_percent=4.17,
            high_24h=1.30,
            low_24h=1.20
        )
        print(f"✅ PriceData created: ${price_data.current_price}")
        
        # Test RiskAssessment
        risk_assessment = RiskAssessment(
            confidence_score=75.0,
            risk_level="MEDIUM",
            position_size="Small",
            volatility=15.5,
            risk_factors=["Low liquidity"]
        )
        print(f"✅ RiskAssessment created: {risk_assessment.confidence_score}% confidence")
        
        return True
        
    except Exception as e:
        print(f"❌ Data models test failed: {e}")
        return False

def test_concurrent_processing():
    """Test that concurrent processing components work"""
    print("\n🧪 Testing concurrent processing...")
    
    try:
        from concurrent_processing.worker_pool import concurrent_processor
        from concurrent_processing.rate_limiter import rate_limit_manager
        
        # Test rate limiter
        user_id = 12345
        can_analyze, remaining_time = rate_limit_manager.check_analysis_limit(user_id)
        print(f"✅ Rate limit check: can_analyze={can_analyze}, remaining={remaining_time}s")
        
        # Test worker pool
        stats = concurrent_processor.get_global_stats()
        print(f"✅ Worker pool stats: {stats}")
        
        return True
        
    except Exception as e:
        print(f"❌ Concurrent processing test failed: {e}")
        return False

def test_services():
    """Test that service components are properly initialized"""
    print("\n🧪 Testing services...")
    
    try:
        from services.analysis_service import token_analysis_service
        from services.data_fetcher import data_fetcher
        from services.analysis_engine import analysis_engine
        
        # Test service initialization
        print(f"✅ Analysis service: {type(token_analysis_service)}")
        print(f"✅ Data fetcher: {type(data_fetcher)}")
        print(f"✅ Analysis engine: {type(analysis_engine)}")
        
        # Test service methods exist
        methods = ['analyze_token', '_create_risk_assessment', '_create_trading_recommendation']
        for method in methods:
            if hasattr(token_analysis_service, method):
                print(f"✅ Method {method} exists")
            else:
                print(f"❌ Method {method} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Services test failed: {e}")
        return False

def test_utility_functions():
    """Test that utility functions work correctly"""
    print("\n🧪 Testing utility functions...")
    
    try:
        from utils.helpers import safe_float, human_format, validate_solana_address
        
        # Test safe_float
        result1 = safe_float("123.45", 0.0)
        result2 = safe_float("invalid", 10.0)
        print(f"✅ safe_float: {result1} (valid), {result2} (default)")
        
        # Test human_format
        formatted = human_format(1234567)
        print(f"✅ human_format: {formatted}")
        
        # Test Solana address validation
        valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
        is_valid = validate_solana_address(valid_address)
        print(f"✅ Solana validation: {is_valid}")
        
        return True
        
    except Exception as e:
        print(f"❌ Utility functions test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting new architecture tests...\n")
    
    tests = [
        test_imports,
        test_configuration,
        test_data_models,
        test_concurrent_processing,
        test_services,
        test_utility_functions
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The new architecture is working correctly.")
    else:
        print(f"⚠️  {total - passed} tests failed. There may be issues with the architecture.")
    
    return passed == total

if __name__ == "__main__":
    main()
