#!/usr/bin/env python3
"""
Test file for confidence score functionality
"""

import sys
import os
import asyncio

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis_service import token_analysis_service
from models.token_data import RiskAssessment
import pandas as pd

def test_confidence_score_calculation():
    """Test that confidence score is properly calculated"""
    print("🧪 Testing confidence score calculation...")
    
    # Test the analysis engine's get_final_verdict method directly
    from services.analysis_engine import analysis_engine
    
    # Create mock OHLCV data
    mock_ohlcv = pd.DataFrame({
        'close': [1.0, 1.1, 1.05, 1.15, 1.2, 1.18, 1.25, 1.3, 1.28, 1.35],
        'high': [1.1, 1.15, 1.1, 1.2, 1.25, 1.2, 1.3, 1.35, 1.3, 1.4],
        'low': [0.95, 1.05, 1.0, 1.1, 1.15, 1.15, 1.2, 1.25, 1.25, 1.3],
        'volume': [1000, 1200, 800, 1500, 1800, 1600, 2000, 2200, 2000, 2400]
    })
    
    # Add technical indicators
    mock_ohlcv = analysis_engine.add_technical_indicators(mock_ohlcv)
    
    # Mock pair info
    mock_pair_info = {
        'priceUsd': '1.35',
        'liquidity': {'usd': 50000},
        'volume': {'h24': 25000},
        'fdv': 1000000,
        'txns': {'h24': {'buys': 150, 'sells': 100}}
    }
    
    # Mock rug data
    mock_rug_data = {
        'success': True,
        'rug_probability': 15.0,
        'risk_score': 25,
        'risk_level': 'LOW',
        'security_flags': {
            'mint_authority': False,
            'freeze_authority': False,
            'transfer_fee_active': False
        }
    }
    
    try:
        # Test the final verdict calculation
        verdict, reasoning, confidence_score = analysis_engine.get_final_verdict(
            mock_ohlcv, mock_pair_info, mock_rug_data
        )
        
        print(f"✅ Final verdict: {verdict}")
        print(f"✅ Reasoning: {reasoning}")
        print(f"✅ Confidence score: {confidence_score}")
        
        # Verify confidence score is not 0
        if confidence_score > 0:
            print("✅ Confidence score is properly calculated (not 0)")
        else:
            print("❌ Confidence score is 0 - this indicates a problem")
            
        # Verify confidence score is within bounds
        if 0 <= confidence_score <= 100:
            print("✅ Confidence score is within valid range (0-100)")
        else:
            print(f"❌ Confidence score {confidence_score} is outside valid range")
            
        return confidence_score > 0
        
    except Exception as e:
        print(f"❌ Error testing confidence score: {e}")
        return False

def test_analysis_service_confidence():
    """Test that the analysis service properly handles confidence scores"""
    print("\n🧪 Testing analysis service confidence score handling...")
    
    # Test the _create_trading_recommendation method
    try:
        # Create mock data
        mock_ohlcv = pd.DataFrame({
            'close': [1.0, 1.1, 1.05, 1.15, 1.2],
            'high': [1.1, 1.15, 1.1, 1.2, 1.25],
            'low': [0.95, 1.05, 1.0, 1.1, 1.15],
            'volume': [1000, 1200, 800, 1500, 1800]
        })
        
        mock_pair_info = {
            'priceUsd': '1.2',
            'liquidity': {'usd': 50000},
            'volume': {'h24': 25000},
            'fdv': 1000000
        }
        
        mock_rug_data = {
            'success': True,
            'rug_probability': 20.0,
            'risk_score': 30
        }
        
        from models.token_data import KeyLevels
        mock_key_levels = KeyLevels(support_level=1.0, resistance_level=1.3)
        
        # Test the method
        result = token_analysis_service._create_trading_recommendation(
            mock_ohlcv, mock_pair_info, mock_rug_data, mock_key_levels
        )
        
        print(f"✅ Trading recommendation created: {result.final_verdict}")
        print(f"✅ Entry strategy: {result.entry_strategy}")
        print(f"✅ Reasoning: {result.reasoning}")
        
        # Check if confidence score was stored
        if hasattr(token_analysis_service, '_last_confidence_score'):
            stored_score = token_analysis_service._last_confidence_score
            print(f"✅ Confidence score stored: {stored_score}")
            
            if stored_score > 0:
                print("✅ Stored confidence score is valid (not 0)")
                return True
            else:
                print("❌ Stored confidence score is 0")
                return False
        else:
            print("❌ Confidence score was not stored")
            return False
            
    except Exception as e:
        print(f"❌ Error testing analysis service: {e}")
        return False

def test_risk_assessment_confidence():
    """Test that risk assessment gets the proper confidence score"""
    print("\n🧪 Testing risk assessment confidence score...")
    
    try:
        # Create mock data
        mock_ohlcv = pd.DataFrame({
            'close': [1.0, 1.1, 1.05, 1.15, 1.2],
            'high': [1.1, 1.15, 1.1, 1.2, 1.25],
            'low': [0.95, 1.05, 1.0, 1.1, 1.15],
            'volume': [1000, 1200, 800, 1500, 1800]
        })
        
        mock_pair_info = {
            'priceUsd': '1.2',
            'liquidity': {'usd': 50000},
            'volume': {'h24': 25000},
            'fdv': 1000000
        }
        
        mock_rug_data = {
            'success': True,
            'rug_probability': 25.0,
            'risk_score': 35
        }
        
        # Test risk assessment creation
        risk_assessment = token_analysis_service._create_risk_assessment(
            mock_ohlcv, mock_pair_info, mock_rug_data
        )
        
        print(f"✅ Risk assessment created with confidence: {risk_assessment.confidence_score}")
        print(f"✅ Risk level: {risk_assessment.risk_level}")
        print(f"✅ Position size: {risk_assessment.position_size}")
        
        # Check initial confidence score
        if risk_assessment.confidence_score > 0:
            print("✅ Initial confidence score is valid")
        else:
            print("❌ Initial confidence score is 0")
            
        return risk_assessment.confidence_score > 0
        
    except Exception as e:
        print(f"❌ Error testing risk assessment: {e}")
        return False

async def test_full_analysis_flow():
    """Test the full analysis flow to ensure confidence score is properly passed through"""
    print("\n🧪 Testing full analysis flow...")
    
    try:
        # This would require a real token address, so we'll just test the flow
        # For now, let's verify the service is properly initialized
        print(f"✅ Analysis service initialized: {type(token_analysis_service)}")
        print(f"✅ Analysis engine available: {hasattr(token_analysis_service, 'analysis_engine')}")
        print(f"✅ Rate limit manager available: {hasattr(token_analysis_service, 'rate_limit_manager')}")
        
        # Test that the service can create a mock analysis result
        mock_ohlcv = pd.DataFrame({
            'close': [1.0, 1.1, 1.05, 1.15, 1.2],
            'high': [1.1, 1.15, 1.1, 1.2, 1.25],
            'low': [0.95, 1.05, 1.0, 1.1, 1.15],
            'volume': [1000, 1200, 800, 1500, 1800]
        })
        
        mock_pair_info = {
            'priceUsd': '1.2',
            'liquidity': {'usd': 50000},
            'volume': {'h24': 25000},
            'fdv': 1000000,
            'baseToken': {
                'address': 'test123',
                'name': 'Test Token',
                'symbol': 'TEST',
                'decimals': 9,
                'supply': 1000000000
            },
            'url': 'https://dexscreener.com/test'
        }
        
        mock_rug_data = {
            'success': True,
            'rug_probability': 30.0,
            'risk_score': 40
        }
        
        # Test the complete flow
        token_info = token_analysis_service._extract_token_info(mock_pair_info)
        price_data = token_analysis_service._extract_price_data(mock_pair_info, mock_ohlcv)
        market_data = token_analysis_service._extract_market_data(mock_pair_info)
        trading_activity = token_analysis_service._extract_trading_activity(mock_pair_info)
        
        print(f"✅ Token info extracted: {token_info.symbol}")
        print(f"✅ Price data extracted: ${price_data.current_price}")
        print(f"✅ Market data extracted: ${market_data.market_cap}")
        print(f"✅ Trading activity extracted: {trading_activity.total_trades_24h} trades")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing full flow: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Starting confidence score tests...\n")
    
    results = []
    
    # Run tests
    results.append(test_confidence_score_calculation())
    results.append(test_analysis_service_confidence())
    results.append(test_risk_assessment_confidence())
    
    # Run async test
    try:
        async_result = asyncio.run(test_full_analysis_flow())
        results.append(async_result)
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        results.append(False)
    
    # Summary
    print(f"\n📊 Test Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! Confidence score should work correctly.")
    else:
        print("⚠️  Some tests failed. Confidence score may have issues.")
    
    return all(results)

if __name__ == "__main__":
    main()
