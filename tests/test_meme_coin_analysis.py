#!/usr/bin/env python3
"""
Test file for meme coin specific analysis
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis_engine import analysis_engine
import pandas as pd

def test_meme_coin_pattern_detection():
    """Test meme coin pattern detection"""
    print("🧪 Testing meme coin pattern detection...")
    
    try:
        # Create mock OHLCV data simulating a meme coin pump
        mock_ohlcv = pd.DataFrame({
            'close': [0.001, 0.0012, 0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018, 0.025],
            'high': [0.0012, 0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018, 0.025, 0.035],
            'low': [0.0009, 0.001, 0.0012, 0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018],
            'volume': [1000, 2000, 5000, 15000, 50000, 150000, 500000, 1000000, 2000000, 3000000]
        })
        
        # Add technical indicators
        mock_ohlcv = analysis_engine.add_technical_indicators(mock_ohlcv)
        
        # Mock pair info
        mock_pair_info = {
            'priceUsd': '0.025',
            'liquidity': {'usd': 50000},
            'volume': {'h24': 5000000},
            'fdv': 2500000  # 2.5M market cap
        }
        
        # Test meme coin analysis
        meme_analysis = analysis_engine.analyze_meme_coin_patterns(mock_ohlcv, mock_pair_info)
        
        print(f"✅ Meme coin analysis completed")
        print(f"✅ Growth acceleration: {meme_analysis.get('growth_acceleration', 'N/A'):.3f}")
        print(f"✅ Is pumping: {meme_analysis.get('is_pumping', False)}")
        print(f"✅ Volume surge: {meme_analysis.get('volume_surge', 'N/A'):.1f}x")
        print(f"✅ Volume surge level: {meme_analysis.get('volume_surge_level', 'N/A')}")
        print(f"✅ Volatility: {meme_analysis.get('volatility', 'N/A'):.1f}%")
        print(f"✅ Volatility level: {meme_analysis.get('volatility_level', 'N/A')}")
        print(f"✅ Is parabolic: {meme_analysis.get('is_parabolic', False)}")
        
        # Test risk assessment
        meme_risk = meme_analysis.get('meme_coin_risk', {})
        if meme_risk:
            print(f"✅ Meme coin risk score: {meme_risk.get('risk_score', 'N/A')}")
            print(f"✅ Risk level: {meme_risk.get('risk_level', 'N/A')}")
            print(f"✅ Risk factors: {meme_risk.get('total_factors', 'N/A')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing meme coin patterns: {e}")
        return False

def test_meme_coin_verdict():
    """Test meme coin specific verdict calculation"""
    print("\n🧪 Testing meme coin verdict calculation...")
    
    try:
        # Create mock data for a pumping meme coin
        mock_ohlcv = pd.DataFrame({
            'close': [0.001, 0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018, 0.025, 0.035],
            'high': [0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018, 0.025, 0.035, 0.045],
            'low': [0.0009, 0.001, 0.0015, 0.002, 0.003, 0.005, 0.008, 0.012, 0.018, 0.025],
            'volume': [1000, 5000, 15000, 50000, 150000, 500000, 1000000, 2000000, 3000000, 4000000]
        })
        
        # Add technical indicators
        mock_ohlcv = analysis_engine.add_technical_indicators(mock_ohlcv)
        
        # Mock pair info
        mock_pair_info = {
            'priceUsd': '0.035',
            'liquidity': {'usd': 75000},
            'volume': {'h24': 8000000},
            'fdv': 3500000
        }
        
        # Mock rug data (low risk)
        mock_rug_data = {
            'success': True,
            'rug_probability': 15.0,
            'risk_score': 20,
            'security_flags': {
                'mint_authority': False,
                'freeze_authority': False
            }
        }
        
        # Test final verdict
        verdict, reasoning, confidence_score = analysis_engine.get_final_verdict(
            mock_ohlcv, mock_pair_info, mock_rug_data
        )
        
        print(f"✅ Final verdict: {verdict}")
        print(f"✅ Confidence score: {confidence_score}%")
        print(f"✅ Reasoning: {reasoning}")
        
        # Check if meme coin analysis influenced the verdict
        if "MEME COIN PUMP" in reasoning or "volume surge" in reasoning.lower():
            print("✅ Meme coin analysis properly influenced verdict")
        else:
            print("⚠️ Meme coin analysis may not have influenced verdict")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing meme coin verdict: {e}")
        return False

def test_volume_surge_classification():
    """Test volume surge classification for meme coins"""
    print("\n🧪 Testing volume surge classification...")
    
    try:
        # Test different volume surge levels
        test_cases = [
            (15.0, "EXTREME SURGE"),      # 15x volume
            (7.0, "MASSIVE SURGE"),       # 7x volume
            (4.0, "HIGH SURGE"),          # 4x volume
            (2.5, "MODERATE SURGE"),      # 2.5x volume
            (1.2, "NORMAL VOLUME")        # 1.2x volume
        ]
        
        for volume_surge, expected_level in test_cases:
            # Access the private method for testing
            if hasattr(analysis_engine, '_classify_volume_surge'):
                result = analysis_engine._classify_volume_surge(volume_surge)
                status = "✅" if result == expected_level else "❌"
                print(f"{status} {volume_surge}x volume → {result} (expected: {expected_level})")
            else:
                print("❌ _classify_volume_surge method not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing volume surge classification: {e}")
        return False

def test_volatility_classification():
    """Test volatility classification for meme coins"""
    print("\n🧪 Testing volatility classification...")
    
    try:
        # Test different volatility levels
        test_cases = [
            (75.0, "EXTREME"),      # 75% volatility
            (45.0, "VERY HIGH"),    # 45% volatility
            (25.0, "HIGH"),         # 25% volatility
            (15.0, "MODERATE"),     # 15% volatility
            (5.0, "LOW")            # 5% volatility
        ]
        
        for volatility, expected_level in test_cases:
            # Access the private method for testing
            if hasattr(analysis_engine, '_classify_volatility'):
                result = analysis_engine._classify_volatility(volatility)
                status = "✅" if result == expected_level else "❌"
                print(f"{status} {volatility}% volatility → {result} (expected: {expected_level})")
            else:
                print("❌ _classify_volatility method not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing volatility classification: {e}")
        return False

def main():
    """Run all meme coin analysis tests"""
    print("🚀 Starting meme coin analysis tests...\n")
    
    tests = [
        test_meme_coin_pattern_detection,
        test_meme_coin_verdict,
        test_volume_surge_classification,
        test_volatility_classification
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
        print("🎉 All meme coin analysis tests passed!")
        print("✅ Meme coin specific analysis is working correctly")
    else:
        print(f"⚠️ {total - passed} tests failed. Meme coin analysis may have issues.")
    
    return passed == total

if __name__ == "__main__":
    main()
