"""
Data fetcher service for retrieving token data from various APIs
"""

import requests
import pandas as pd
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from config.settings import (
    DEXSCREENER_BASE_URL, MORALIS_BASE_URL, RUGCHECK_BASE_URL,
    MORALIS_API_KEY, DEFAULT_HEADERS, REQUEST_TIMEOUT, API_TIMEOUT,
    OHLCV_LIMIT
)
from utils.helpers import datetime_to_timestamp
from config.logging_config import get_logger

logger = get_logger(__name__)

class DataFetcher:
    """Service for fetching token data from various APIs"""
    
    def __init__(self):
        self.dexscreeener_base_url = DEXSCREENER_BASE_URL
        self.moralis_base_url = MORALIS_BASE_URL
        self.rugcheck_base_url = RUGCHECK_BASE_URL
        self.moralis_api_key = MORALIS_API_KEY
        self.headers = DEFAULT_HEADERS
        self.timeout = REQUEST_TIMEOUT
        self.api_timeout = API_TIMEOUT
    
    def get_token_pair_address(self, token_address: str) -> Optional[str]:
        """Get pair address for a token from DexScreener"""
        try:
            url = f"{self.dexscreeener_base_url}/tokens/v1/solana/{token_address}"
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    pair_data = data[0]
                    if 'pairAddress' in pair_data:
                        pair_address = pair_data['pairAddress']
                        logger.info(f"Pair address found: {pair_address}")
                        return pair_address
                    else:
                        logger.warning(f"Pair address not found in response for token: {token_address}")
                else:
                    logger.warning(f"No trading pairs found for token: {token_address}")
            else:
                logger.error(f"Failed to fetch data for token: {token_address}, status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error getting pair address for {token_address}: {e}")
        
        return None
    
    def fetch_ohlcv_data(self, pair_address: str, from_date: int, to_date: int, limit: int = OHLCV_LIMIT) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from Moralis API"""
        try:
            url = f'{self.moralis_base_url}/token/mainnet/pairs/{pair_address}/ohlcv'
            params = {
                'limit': limit,
                'fromDate': from_date,
                'toDate': to_date,
                'timeframe': '1min',
                'currency': 'usd'
            }
            headers = {
                'accept': 'application/json',
                'X-Api-Key': self.moralis_api_key
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=self.api_timeout)
            
            if response.status_code == 200:
                data = response.json()
                if 'result' in data:
                    return self._process_ohlcv_data(data)
                else:
                    logger.warning(f"No result in OHLCV response for pair: {pair_address}")
            else:
                logger.error(f"OHLCV API failed for pair {pair_address}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching OHLCV data for pair {pair_address}: {e}")
        
        return None
    
    def fetch_dex_screener_data(self, pair_address: str) -> Optional[Dict[str, Any]]:
        """Fetch market data from DexScreener"""
        try:
            url = f'{self.dexscreeener_base_url}/latest/dex/pairs/solana/{pair_address}'
            response = requests.get(url, headers=self.headers, timeout=self.timeout)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"DexScreener API failed for pair {pair_address}: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error fetching DexScreener data for pair {pair_address}: {e}")
        
        return None
    
    def _process_ohlcv_data(self, data: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """Process raw OHLCV data into DataFrame"""
        try:
            if 'result' not in data or not data['result']:
                logger.warning("No OHLCV result data available")
                return None
            
            df = pd.DataFrame(data['result'])
            
            if df.empty:
                logger.warning("Empty OHLCV DataFrame")
                return None
            
            # Rename columns to standard format
            columns_needed = {'t': 'timestamp', 'o': 'open', 'h': 'high', 'l': 'low', 'c': 'close', 'v': 'volume'}
            df = df.rename(columns=columns_needed)
            
            # Keep only needed columns
            df = df[list(columns_needed.values())]
            
            # Convert timestamp to datetime
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values(by='timestamp', ascending=True).reset_index(drop=True)
            
            # Convert numeric columns
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            logger.info(f"Processed OHLCV data: {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Error processing OHLCV data: {e}")
            return None
    
    def get_ohlcv_data_for_analysis(self, pair_address: str, hours_back: int = 6) -> Optional[pd.DataFrame]:
        """Get OHLCV data for analysis with proper time range"""
        try:
            current_time = datetime.utcnow()
            from_date = datetime_to_timestamp(current_time - timedelta(hours=hours_back))
            to_date = datetime_to_timestamp(current_time)
            
            logger.info(f"Fetching OHLCV data for pair {pair_address} from {hours_back} hours ago")
            ohlcv_data = self.fetch_ohlcv_data(pair_address, from_date, to_date, limit=OHLCV_LIMIT)
            
            if ohlcv_data is not None and not ohlcv_data.empty:
                logger.info(f"Successfully fetched {len(ohlcv_data)} OHLCV records")
                return ohlcv_data
            else:
                logger.warning(f"No OHLCV data available for pair {pair_address}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting OHLCV data for analysis: {e}")
            return None
    
    def get_token_market_data(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get complete market data for a token"""
        try:
            # First get the pair address
            pair_address = self.get_token_pair_address(token_address)
            if not pair_address:
                logger.error(f"Could not get pair address for token {token_address}")
                return None
            
            # Get market data from DexScreener
            dex_data = self.fetch_dex_screener_data(pair_address)
            if not dex_data or 'pairs' not in dex_data or not dex_data['pairs']:
                logger.error(f"Failed to retrieve pair data from DexScreener for {token_address}")
                return None
            
            pair_info = dex_data['pairs'][0]
            
            # Get OHLCV data
            ohlcv_data = self.get_ohlcv_data_for_analysis(pair_address)
            
            return {
                'pair_address': pair_address,
                'pair_info': pair_info,
                'ohlcv_data': ohlcv_data,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error getting token market data for {token_address}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def validate_token_address(self, token_address: str) -> bool:
        """Validate if token address format is correct"""
        if not token_address or len(token_address) < 32 or len(token_address) > 44:
            return False
        
        base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        return all(c in base58_chars for c in token_address)

# Create global instance
data_fetcher = DataFetcher()
