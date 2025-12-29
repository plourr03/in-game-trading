"""
Real-time Kalshi API client for fetching live market data
"""
import requests
import time
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class KalshiAPIClient:
    """Client for fetching live Kalshi market data"""
    
    def __init__(self, api_key: str, private_key: str):
        """
        Initialize Kalshi API client
        
        Args:
            api_key: Kalshi API key ID
            private_key: RSA private key string
        """
        self.api_key = api_key
        self.private_key = private_key
        self.base_url = "https://api.elections.kalshi.com/trade-api/v2"
        self.session = requests.Session()
        self.auth_token = None
        self.token_expiry = 0
        
    def _sign_request(self, method: str, path: str, body: str = "") -> str:
        """Sign a request using the private key"""
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
            from cryptography.hazmat.backends import default_backend
            import base64
            
            # Load private key
            private_key_obj = serialization.load_pem_private_key(
                self.private_key.encode(),
                password=None,
                backend=default_backend()
            )
            
            # Create message to sign (method + path + body)
            message = f"{method}{path}{body}"
            
            # Sign message
            signature = private_key_obj.sign(
                message.encode(),
                padding.PKCS1v15(),
                hashes.SHA256()
            )
            
            # Encode signature as base64
            signature_b64 = base64.b64encode(signature).decode()
            return signature_b64
            
        except Exception as e:
            logger.error(f"Signing error: {e}")
            return None
    
    def _get_auth_headers(self, method: str, path: str, body: str = "") -> Dict:
        """Get authentication headers for a request"""
        signature = self._sign_request(method, path, body)
        if not signature:
            return {}
        
        return {
            "Content-Type": "application/json",
            "KALSHI-ACCESS-KEY": self.api_key,
            "KALSHI-ACCESS-SIGNATURE": signature,
            "KALSHI-ACCESS-TIMESTAMP": str(int(time.time()))
        }
    
    def find_nba_markets(self, team1: str, team2: str, date: str = None) -> List[Dict]:
        """
        Find NBA markets for a specific game
        
        Args:
            team1: First team abbreviation (e.g., 'LAL')
            team2: Second team abbreviation (e.g., 'SAC')
            date: Game date in YYYY-MM-DD format (defaults to today)
            
        Returns:
            List of market dictionaries
        """
        try:
            # Search for NBA markets
            path = "/markets"
            params = {
                'series_ticker': 'KXNBAGAME',
                'limit': 200
            }
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            full_path = f"{path}?{query_string}"
            
            headers = self._get_auth_headers("GET", full_path)
            response = requests.get(
                f"{self.base_url}{full_path}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch markets: {response.status_code} - {response.text}")
                return []
            
            data = response.json()
            markets = data.get('markets', [])
            
            # Filter for our game
            game_markets = []
            for market in markets:
                ticker = market.get('ticker', '').upper()
                title = market.get('title', '').upper()
                if (team1.upper() in ticker or team1.upper() in title) and \
                   (team2.upper() in ticker or team2.upper() in title):
                    game_markets.append(market)
            
            logger.info(f"Found {len(game_markets)} markets for {team1} vs {team2}")
            return game_markets
            
        except Exception as e:
            logger.error(f"Error finding markets: {e}")
            return []
    
    def get_market_orderbook(self, ticker: str) -> Optional[Dict]:
        """
        Get current orderbook for a market
        
        Args:
            ticker: Market ticker
            
        Returns:
            Orderbook dictionary with best bid/ask
        """
        try:
            path = f"/markets/{ticker}/orderbook"
            headers = self._get_auth_headers("GET", path)
            
            response = requests.get(
                f"{self.base_url}{path}",
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to fetch orderbook for {ticker}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return None
    
    def get_live_price(self, ticker: str) -> Optional[Dict]:
        """
        Get current price for a market
        
        Args:
            ticker: Market ticker
            
        Returns:
            Dictionary with price info: {'bid': X, 'ask': Y, 'last': Z, 'timestamp': T}
        """
        orderbook = self.get_market_orderbook(ticker)
        if not orderbook:
            return None
        
        try:
            # Get best bid and ask
            yes_bids = orderbook.get('orderbook', {}).get('yes', [])
            no_asks = orderbook.get('orderbook', {}).get('no', [])
            
            # Best yes bid = highest price someone will pay for yes
            best_yes_bid = max([bid[0] for bid in yes_bids]) if yes_bids else None
            
            # Best no ask = lowest price someone will sell no for
            # Which means best yes ask = 100 - best no ask
            best_no_ask = min([ask[0] for ask in no_asks]) if no_asks else None
            best_yes_ask = (100 - best_no_ask) if best_no_ask else None
            
            # Mid price
            if best_yes_bid and best_yes_ask:
                mid_price = (best_yes_bid + best_yes_ask) / 2
            elif best_yes_bid:
                mid_price = best_yes_bid
            elif best_yes_ask:
                mid_price = best_yes_ask
            else:
                mid_price = None
            
            return {
                'ticker': ticker,
                'bid': best_yes_bid,
                'ask': best_yes_ask,
                'mid': mid_price,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error parsing orderbook: {e}")
            return None
    
    def stream_market_prices(self, ticker: str, duration_seconds: int = 60, 
                            interval_seconds: int = 5) -> pd.DataFrame:
        """
        Stream market prices for a period of time
        
        Args:
            ticker: Market ticker
            duration_seconds: How long to stream for
            interval_seconds: Seconds between price fetches
            
        Returns:
            DataFrame with timestamp, bid, ask, mid columns
        """
        prices = []
        start_time = time.time()
        
        logger.info(f"Streaming {ticker} for {duration_seconds} seconds...")
        
        while time.time() - start_time < duration_seconds:
            price_data = self.get_live_price(ticker)
            if price_data:
                prices.append(price_data)
                logger.info(f"  {ticker}: Bid={price_data['bid']}, Ask={price_data['ask']}, Mid={price_data['mid']}")
            
            time.sleep(interval_seconds)
        
        df = pd.DataFrame(prices)
        logger.info(f"Collected {len(df)} price samples")
        return df


def load_kalshi_credentials(keys_file: str = "keys.md") -> tuple:
    """
    Load Kalshi API credentials from keys file
    
    Returns:
        (api_key, private_key) tuple
    """
    try:
        with open(keys_file, 'r') as f:
            lines = f.readlines()
        
        # First line is API key
        api_key = lines[0].strip()
        
        # Rest is private key
        private_key_lines = []
        in_key = False
        for line in lines[1:]:
            if '-----BEGIN RSA PRIVATE KEY-----' in line:
                in_key = True
            if in_key:
                private_key_lines.append(line)
            if '-----END RSA PRIVATE KEY-----' in line:
                break
        
        private_key = ''.join(private_key_lines)
        
        return api_key, private_key
        
    except Exception as e:
        logger.error(f"Failed to load credentials: {e}")
        return None, None


if __name__ == "__main__":
    # Test the API
    logging.basicConfig(level=logging.INFO)
    
    api_key, private_key = load_kalshi_credentials()
    if not api_key or not private_key:
        print("Failed to load credentials")
        exit(1)
    
    client = KalshiAPIClient(api_key, private_key)
    
    # Find today's games
    print("\nSearching for Lakers vs Kings...")
    markets = client.find_nba_markets('LAL', 'SAC')
    
    if markets:
        print(f"\nFound {len(markets)} markets:")
        for market in markets[:3]:  # Show first 3
            print(f"  - {market.get('title')}")
            print(f"    Ticker: {market.get('ticker')}")
            
        # Get live price for first market
        if markets:
            ticker = markets[0].get('ticker')
            print(f"\nFetching live price for {ticker}...")
            price = client.get_live_price(ticker)
            if price:
                print(f"  Bid: {price['bid']}¢")
                print(f"  Ask: {price['ask']}¢")
                print(f"  Mid: {price['mid']}¢")
    else:
        print("No markets found")

