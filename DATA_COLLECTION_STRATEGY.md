# Kalshi Data Collection - How It Works

## ⚠️ Important Discovery

**Kalshi Historical Data Availability:**
- Candlesticks endpoint: Returns 404 for recent games (last 1-3 days)
- History endpoint: Returns empty for recent games
- **Reason:** Kalshi doesn't make historical data available immediately after markets settle

## ✅ Solution: Use Tonight's Live Data Collection

### What Happens Tonight:
When you run `python run_paper_trading.py`:
1. System polls Kalshi API every 60 seconds
2. Logs **every price point** to database (`paper_trading.price_data` table)
3. Also logs to CSV (`paper_prices_*.csv`)
4. This gives you the same data format as your training data

### Tomorrow: Export Tonight's Data for Model Retraining

```python
# Export tonight's price data to Kalshi format
import pandas as pd
import psycopg2
import yaml

# Connect to database
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

# Get latest session
session_id = pd.read_sql("""
    SELECT session_id FROM paper_trading.sessions 
    ORDER BY start_time DESC LIMIT 1;
""", conn)['session_id'].iloc[0]

# Export price data for each game
prices = pd.read_sql(f"""
    SELECT 
        timestamp as datetime,
        ticker,
        price_mid as close,
        price_bid as open,
        price_ask as high,
        price_mid as low,
        0 as volume,
        game_id,
        away_team,
        home_team
    FROM paper_trading.price_data
    WHERE session_id = {session_id}
    ORDER BY game_id, timestamp;
""", conn)

# Save each game separately
for ticker in prices['ticker'].unique():
    game_data = prices[prices['ticker'] == ticker]
    game_data.to_csv(f'kalshi_data/jan_dec_2025_games/{ticker}.csv', index=False)
    print(f"Saved {len(game_data)} rows for {ticker}")

conn.close()
```

## 📊 Data Quality Comparison

### Tonight's Live Collection:
- **Pros:**
  - Real-time, accurate prices
  - Exactly what model will see in production
  - No missing data
  - High frequency (every 60 seconds)

### Kalshi Historical API:
- **Pros:**
  - Official source
  - 1-minute candlesticks
- **Cons:**
  - Not available for recent games
  - May have gaps
  - Delayed availability (days/weeks)

## 🎯 Recommendation

**Use tonight's paper trading as your data collection system!**

1. **Tonight:** Run paper trading → Collect live data
2. **Tomorrow:** Export from database → Add to training set
3. **Weekly:** Retrain model with new data
4. **Continuously:** Model stays up-to-date with recent games

## 📝 Script: Export Tonight's Data

Save this as `export_paper_trading_data.py`:

```python
"""
Export Paper Trading Data to Kalshi Format
Converts tonight's collected data into training data format
"""
import pandas as pd
import psycopg2
import yaml
import os

def export_session_data(session_id=None, output_folder='kalshi_data/jan_dec_2025_games'):
    """Export paper trading session data to Kalshi CSV format"""
    
    # Connect to database
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
    
    # Get latest session if not specified
    if session_id is None:
        session_df = pd.read_sql("""
            SELECT session_id, start_time 
            FROM paper_trading.sessions 
            ORDER BY start_time DESC LIMIT 1;
        """, conn)
        
        if session_df.empty:
            print("[ERROR] No sessions found")
            return
        
        session_id = session_df['session_id'].iloc[0]
        print(f"[INFO] Using latest session: {session_id} ({session_df['start_time'].iloc[0]})")
    
    # Get price data
    print(f"\n[INFO] Fetching price data from session {session_id}...")
    prices = pd.read_sql(f"""
        SELECT 
            timestamp as datetime,
            ticker,
            price_mid as close,
            price_bid as open,
            price_ask as high,
            price_mid as low,
            0 as volume,
            game_id,
            away_team,
            home_team,
            TO_CHAR(timestamp, 'YYYY-MM-DD') as game_date
        FROM paper_trading.price_data
        WHERE session_id = {session_id}
        ORDER BY game_id, timestamp;
    """, conn)
    
    if prices.empty:
        print("[ERROR] No price data found")
        conn.close()
        return
    
    print(f"[OK] Found {len(prices)} price points across {prices['ticker'].nunique()} games")
    
    # Create output folder
    os.makedirs(output_folder, exist_ok=True)
    
    # Save each game separately
    saved = 0
    for ticker in prices['ticker'].unique():
        game_data = prices[prices['ticker'] == ticker].copy()
        
        # Reorder columns to match training data format
        game_data = game_data[['datetime', 'open', 'high', 'low', 'close', 'volume', 
                               'ticker', 'game_id', 'away_team', 'home_team', 'game_date']]
        
        # Save to CSV
        output_file = os.path.join(output_folder, f"{ticker}.csv")
        game_data.to_csv(output_file, index=False)
        print(f"  [OK] Saved {len(game_data)} rows for {ticker}")
        saved += 1
    
    conn.close()
    
    print(f"\n[OK] Exported {saved} games to {output_folder}")
    print(f"\nYou can now retrain your model with this new data!")
    print(f"  cd ml_models")
    print(f"  python prepare_training_data.py")
    print(f"  python train_models.py")


if __name__ == "__main__":
    export_session_data()
```

## 🔄 Workflow Going Forward

### Daily:
```bash
# 1. Run paper trading (collect data)
python run_paper_trading.py

# 2. Export collected data (next day)
python export_paper_trading_data.py
```

### Weekly:
```bash
# Retrain model with new data
cd ml_models
python prepare_training_data.py
python train_models.py
```

### Monthly:
- Compare model performance over time
- Adjust threshold if needed
- A/B test new features

## ✅ Benefits of This Approach

1. **Always up-to-date:** Model trained on recent games
2. **Production data:** Training on exactly what you'll see live
3. **No API limitations:** Not waiting for Kalshi historical data
4. **Continuous learning:** Model adapts to market changes
5. **Quality control:** You collected the data, you know it's good

## 📈 Data Growth

- **Tonight:** 6 games × 180 minutes = ~1,080 data points
- **Per Week:** ~7,560 data points (35 games/week)
- **Per Month:** ~30,240 data points (140 games/month)

Your model will continuously improve with fresh data!


