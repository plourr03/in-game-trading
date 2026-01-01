"""
Database Logger for Paper Trading
Logs all activity to PostgreSQL database
"""
import psycopg2
import yaml
from datetime import datetime
from typing import Dict, List, Optional


class PaperTradingDB:
    """Database logger for paper trading"""
    
    def __init__(self):
        """Initialize database connection"""
        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        self.db_config = config['database']
        self.session_id = None
        
    def connect(self):
        """Get database connection"""
        return psycopg2.connect(
            host=self.db_config['host'],
            port=self.db_config['port'],
            database=self.db_config['database'],
            user=self.db_config['user'],
            password=self.db_config['password']
        )
    
    def start_session(self, games_monitored: int, notes: str = None) -> int:
        """Start a new trading session"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO paper_trading.sessions (start_time, games_monitored, notes)
            VALUES (%s, %s, %s)
            RETURNING session_id;
        """, (datetime.now(), games_monitored, notes))
        
        self.session_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return self.session_id
    
    def end_session(self, total_signals: int, total_trades: int, 
                   total_pl: float, win_rate: float):
        """End current trading session"""
        if not self.session_id:
            return
        
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE paper_trading.sessions
            SET end_time = %s,
                total_signals = %s,
                total_trades = %s,
                total_pl = %s,
                win_rate = %s
            WHERE session_id = %s;
        """, (datetime.now(), total_signals, total_trades, total_pl, win_rate, self.session_id))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def log_price_data(self, data: Dict):
        """Log price and score data"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO paper_trading.price_data (
                session_id, timestamp, game_id, away_team, home_team, ticker,
                price_mid, price_bid, price_ask,
                score_home, score_away, score_diff,
                period, game_minute
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            self.session_id,
            data['timestamp'],
            data['game_id'],
            data.get('away_team'),
            data.get('home_team'),
            data.get('ticker'),
            data['mid'],
            data['bid'],
            data['ask'],
            data['score_home'],
            data['score_away'],
            data['score_home'] - data['score_away'],
            data['period'],
            data['game_minute']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def log_signal(self, signal: Dict) -> int:
        """Log trading signal, returns signal_id"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO paper_trading.signals (
                session_id, timestamp, game_id, away_team, home_team, ticker,
                action, entry_price, price_bid, price_ask, contracts,
                probability, hold_minutes,
                score_home, score_away, score_diff, period, game_minute
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING signal_id;
        """, (
            self.session_id,
            signal['timestamp'],
            signal['game_id'],
            signal['away_team'],
            signal['home_team'],
            signal.get('ticker'),
            signal['action'],
            signal['entry_price'],
            signal['bid'],
            signal['ask'],
            signal['contracts'],
            signal['probability'],
            signal['hold_minutes'],
            signal['score_home'],
            signal['score_away'],
            signal['score_home'] - signal['score_away'],
            signal['period'],
            signal['game_minute']
        ))
        
        signal_id = cursor.fetchone()[0]
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return signal_id
    
    def log_trade(self, trade: Dict, signal_id: Optional[int] = None):
        """Log completed trade"""
        conn = self.connect()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO paper_trading.trades (
                session_id, signal_id, game_id,
                entry_timestamp, exit_timestamp,
                entry_minute, exit_minute,
                entry_price, exit_price, contracts,
                entry_score_home, entry_score_away,
                exit_score_home, exit_score_away,
                gross_profit_cents, buy_fee, sell_fee, net_profit,
                probability, won, hold_duration_actual
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """, (
            self.session_id,
            signal_id,
            trade['game_id'],
            trade['entry_timestamp'] if 'entry_timestamp' in trade else trade['timestamp'],
            trade['exit_timestamp'] if 'exit_timestamp' in trade else trade['timestamp'],
            trade.get('entry_minute'),
            trade.get('exit_minute'),
            trade['entry_price'],
            trade['exit_price'],
            trade['contracts'],
            trade.get('entry_score_home'),
            trade.get('entry_score_away'),
            trade.get('exit_score_home'),
            trade.get('exit_score_away'),
            trade['gross_profit_cents'],
            trade['buy_fee'],
            trade['sell_fee'],
            trade['net_profit'],
            trade['probability'],
            trade['won'],
            trade.get('hold_duration_actual')
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def log_features(self, signal_id: int, features: Dict):
        """Log feature values for a signal"""
        conn = self.connect()
        cursor = conn.cursor()
        
        for feature_name, feature_value in features.items():
            cursor.execute("""
                INSERT INTO paper_trading.signal_features (signal_id, feature_name, feature_value)
                VALUES (%s, %s, %s);
            """, (signal_id, feature_name, float(feature_value)))
        
        conn.commit()
        cursor.close()
        conn.close()



