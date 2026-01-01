"""
Database Schema for Paper Trading Logs
Creates tables to store all paper trading activity
"""
import psycopg2
import yaml

def create_tables():
    """Create paper trading tables in PostgreSQL"""
    
    # Load database config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    
    # Connect to database
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    
    cursor = conn.cursor()
    
    print("Creating paper trading tables...")
    
    # Table 1: Trading Sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trading.sessions (
            session_id SERIAL PRIMARY KEY,
            start_time TIMESTAMP NOT NULL,
            end_time TIMESTAMP,
            games_monitored INTEGER,
            total_signals INTEGER DEFAULT 0,
            total_trades INTEGER DEFAULT 0,
            total_pl DECIMAL(10, 2) DEFAULT 0,
            win_rate DECIMAL(5, 4),
            notes TEXT
        );
    """)
    print("  [OK] Created sessions table")
    
    # Table 2: Price Data
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trading.price_data (
            id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES paper_trading.sessions(session_id),
            timestamp TIMESTAMP NOT NULL,
            game_id VARCHAR(20) NOT NULL,
            away_team VARCHAR(10),
            home_team VARCHAR(10),
            ticker VARCHAR(50),
            price_mid DECIMAL(6, 2),
            price_bid DECIMAL(6, 2),
            price_ask DECIMAL(6, 2),
            score_home INTEGER,
            score_away INTEGER,
            score_diff INTEGER,
            period INTEGER,
            game_minute DECIMAL(6, 2)
        );
    """)
    print("  [OK] Created price_data table")
    
    # Table 3: Signals
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trading.signals (
            signal_id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES paper_trading.sessions(session_id),
            timestamp TIMESTAMP NOT NULL,
            game_id VARCHAR(20) NOT NULL,
            away_team VARCHAR(10),
            home_team VARCHAR(10),
            ticker VARCHAR(50),
            action VARCHAR(10),
            entry_price DECIMAL(6, 2),
            price_bid DECIMAL(6, 2),
            price_ask DECIMAL(6, 2),
            contracts INTEGER,
            probability DECIMAL(5, 4),
            hold_minutes INTEGER,
            score_home INTEGER,
            score_away INTEGER,
            score_diff INTEGER,
            period INTEGER,
            game_minute DECIMAL(6, 2),
            executed BOOLEAN DEFAULT FALSE
        );
    """)
    print("  [OK] Created signals table")
    
    # Table 4: Trades
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trading.trades (
            trade_id SERIAL PRIMARY KEY,
            session_id INTEGER REFERENCES paper_trading.sessions(session_id),
            signal_id INTEGER REFERENCES paper_trading.signals(signal_id),
            game_id VARCHAR(20) NOT NULL,
            entry_timestamp TIMESTAMP NOT NULL,
            exit_timestamp TIMESTAMP NOT NULL,
            entry_minute DECIMAL(6, 2),
            exit_minute DECIMAL(6, 2),
            entry_price DECIMAL(6, 2),
            exit_price DECIMAL(6, 2),
            contracts INTEGER,
            entry_score_home INTEGER,
            entry_score_away INTEGER,
            exit_score_home INTEGER,
            exit_score_away INTEGER,
            gross_profit_cents DECIMAL(10, 2),
            buy_fee DECIMAL(10, 2),
            sell_fee DECIMAL(10, 2),
            net_profit DECIMAL(10, 2),
            probability DECIMAL(5, 4),
            won BOOLEAN,
            hold_duration_actual INTEGER
        );
    """)
    print("  [OK] Created trades table")
    
    # Table 5: Features (for analysis)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS paper_trading.signal_features (
            id SERIAL PRIMARY KEY,
            signal_id INTEGER REFERENCES paper_trading.signals(signal_id),
            feature_name VARCHAR(50),
            feature_value DECIMAL(10, 4)
        );
    """)
    print("  [OK] Created signal_features table")
    
    # Create indexes for better query performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_price_data_game_time 
        ON paper_trading.price_data(game_id, timestamp);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_signals_session 
        ON paper_trading.signals(session_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_session 
        ON paper_trading.trades(session_id);
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_trades_won 
        ON paper_trading.trades(won);
    """)
    
    print("  [OK] Created indexes")
    
    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n[OK] Database schema created successfully!")
    print("\nTables created:")
    print("  - paper_trading.sessions     (trading session tracking)")
    print("  - paper_trading.price_data   (all price/score data)")
    print("  - paper_trading.signals      (all ML signals generated)")
    print("  - paper_trading.trades       (completed trades with P/L)")
    print("  - paper_trading.signal_features (feature values for each signal)")


if __name__ == "__main__":
    # First create schema if it doesn't exist
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    db_config = config['database']
    
    conn = psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )
    
    cursor = conn.cursor()
    cursor.execute("CREATE SCHEMA IF NOT EXISTS paper_trading;")
    conn.commit()
    cursor.close()
    conn.close()
    
    print("Created paper_trading schema\n")
    
    # Create tables
    create_tables()

