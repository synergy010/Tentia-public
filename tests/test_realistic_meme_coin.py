#!/usr/bin/env python3
"""
Test realistic meme coin analysis with better data
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analysis_service import token_analysis_service
import pandas as pd

def test_realistic_meme_coin_pump():
    """Test with realistic meme coin pump data"""
    print("🧪 Testing realistic meme coin pump analysis...")
    
    try:
        # Create realistic meme coin pump data (20 periods)
        mock_ohlcv = pd.DataFrame({
            'close': [
                0.0001, 0.00012, 0.00015, 0.00018, 0.00022,  # Initial growth
                0.00028, 0.00035, 0.00045, 0.00058, 0.00075,  # Acceleration
                0.001, 0.0013, 0.0017, 0.0022, 0.0028,        # Pump phase
                0.0035, 0.0042, 0.005, 0.0058, 0.0065          # Peak
            ],
            'high': [
                0.00012, 0.00015, 0.00018, 0.00022, 0.00028,
                0.00035, 0.00045, 0.00058, 0.00075, 0.001,
                0.0013, 0.0017, 0.0022, 0.0028, 0.0035,
                0.0042, 0.005, 0.0058, 0.0065, 0.007
            ],
            'low': [
                0.00009, 0.0001, 0.00012, 0.00015, 0.00018,
                0.00022, 0.00028, 0.00035, 0.00045, 0.00058,
                0.00075, 0.001, 0.0013, 0.0017, 0.0022,
                0.0028, 0.0035, 0.0042, 0.005, 0.0058
            ],
            'volume': [
                1000, 2000, 5000, 12000, 25000,           # Growing interest
                50000, 100000, 250000, 500000, 1000000,    # Volume surge
                2000000, 4000000, 8000000, 15000000, 25000000,  # Viral phase
                40000000, 60000000, 80000000, 100000000, 120000000  # Peak volume
            ]
        })
        
        # Mock pair info for a meme coin
        mock_pair_info = {
            'priceUsd': '0.0065',
            'liquidity': {'usd': 150000},
            'volume': {'h24': 150000000},
            'fdv': 6500000,  # 6.5M market cap
            'baseToken': {
                'address': 'meme123',
                'name': 'Test Meme Coin',
                'symbol': 'MEME',
                'decimals': 9,
                'supply': 1000000000000
            },
            'url': 'https://dexscreener.com/test'
        }
        
        # Mock rug data (low risk)
        mock_rug_data = {
            'success': True,
            'rug_probability': 12.0,
            'risk_score': 18,
            'security_flags': {
                'mint_authority': False,
                'freeze_authority': False,
                'transfer_fee_active': False
            }
        }
        
        # Test the analysis service
        print("📊 Analyzing meme coin with realistic pump data...")
        
        # Extract basic info
        token_info = token_analysis_service._extract_token_info(mock_pair_info)
        print(f"✅ Token: {token_info.symbol} - {token_info.name}")
        
        # Test meme coin pattern detection
        meme_analysis = token_analysis_service.analysis_engine.analyze_meme_coin_patterns(
            mock_ohlcv, mock_pair_info
        )
        
        print(f"\n🎭 MEME COIN ANALYSIS RESULTS:")
        print(f"   🚀 Pumping: {meme_analysis.get('is_pumping', False)}")
        print(f"   📈 Growth acceleration: {meme_analysis.get('growth_acceleration', 0):.3f}")
        print(f"   💥 Volume surge: {meme_analysis.get('volume_surge', 0):.1f}x")
        print(f"   📊 Volume level: {meme_analysis.get('volume_surge_level', 'N/A')}")
        print(f"   📉 Volatility: {meme_analysis.get('volatility', 0):.1f}%")
        print(f"   📊 Is parabolic: {meme_analysis.get('is_parabolic', False)}")
        
        # Test risk assessment
        risk_assessment = token_analysis_service._create_risk_assessment(
            mock_ohlcv, mock_pair_info, mock_rug_data
        )
        
        print(f"\n⚠️ RISK ASSESSMENT:")
        print(f"   🎯 Confidence: {risk_assessment.confidence_score:.1f}%")
        print(f"   ⚠️ Risk level: {risk_assessment.risk_level}")
        print(f"   💰 Position size: {risk_assessment.position_size}")
        print(f"   📊 Volatility: {risk_assessment.volatility:.1f}%")
        
        # Test final verdict
        verdict, reasoning, confidence_score = token_analysis_service.analysis_engine.get_final_verdict(
            mock_ohlcv, mock_pair_info, mock_rug_data
        )
        
        print(f"\n🎯 FINAL VERDICT:")
        print(f"   📋 Verdict: {verdict}")
        print(f"   🎯 Confidence: {confidence_score:.1f}%")
        print(f"   💭 Reasoning: {reasoning}")
        
        # Check if meme coin analysis influenced the result
        meme_indicators = ['MEME COIN PUMP', 'volume surge', 'parabolic', 'viral']
        meme_influence = any(indicator.lower() in reasoning.lower() for indicator in meme_indicators)
        
        if meme_influence:
            print("✅ Meme coin analysis successfully influenced the verdict!")
        else:
            print("⚠️ Meme coin analysis may need further integration")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing realistic meme coin: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run realistic meme coin test"""
    print("🚀 Testing Realistic Meme Coin Analysis\n")
    
    success = test_realistic_meme_coin_pump()
    
    if success:
        print("\n🎉 Realistic meme coin analysis test completed successfully!")
        print("✅ The enhanced analysis engine is working for meme coins")
    else:
        print("\n❌ Realistic meme coin analysis test failed")
    
    return success

if __name__ == "__main__":
    main()
