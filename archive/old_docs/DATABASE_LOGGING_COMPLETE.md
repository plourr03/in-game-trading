# Database Logging - COMPLETE ✅

## What Was Added

### 1. Database Schema ✅
**File:** `setup_paper_trading_db.py`

Created 5 tables in `paper_trading` schema:

#### `paper_trading.sessions`
Tracks each trading session
- session_id, start_time, end_time
- games_monitored, total_signals, total_trades
- total_pl, win_rate, notes

#### `paper_trading.price_data`
All price and score data collected
- timestamp, game_id, ticker
- price_mid, price_bid, price_ask
- score_home, score_away, score_diff
- period, game_minute

#### `paper_trading.signals`
Every ML signal generated
- signal_id, timestamp, game_id
- action, entry_price, contracts
- probability, hold_minutes
- score_home, score_away, period

#### `paper_trading.trades`
All completed trades with P/L
- trade_id, signal_id, game_id
- entry/exit prices, timestamps, scores
- gross_profit_cents, buy_fee, sell_fee
- net_profit, won, probability

#### `paper_trading.signal_features`
Feature values for each signal (for analysis)
- signal_id, feature_name, feature_value

---

### 2. Database Logger ✅
**File:** `src/paper_trading/database_logger.py`

Python class to log all activity:
- `start_session()` - Begin trading session
- `end_session()` - Complete session with summary stats
- `log_price_data()` - Log price/score every poll
- `log_signal()` - Log each ML signal
- `log_trade()` - Log completed trades with P/L
- `log_features()` - Log feature values (optional)

---

### 3. Query/Viewer Script ✅
**File:** `view_paper_trading.py`

View results from database:
- **Session Summary** - Overall performance
- **Trade Details** - Every trade with P/L
- **Per-Game Performance** - Which games were profitable
- **Recent Signals** - Latest signals generated
- **Price Data** - Price/score time series
- **Live Stats** - Real-time stats during trading

---

### 4. Updated Paper Trading System ✅
**File:** `run_paper_trading.py`

Now logs everything to database:
- Every price/score poll → `price_data` table
- Every ML signal → `signals` table
- Every completed trade → `trades` table
- Session start/end → `sessions` table

---

## How to Use

### Setup (One Time):
```bash
python setup_paper_trading_db.py
```
This creates all database tables.

### Run Paper Trading:
```bash
python run_paper_trading.py
```
Now logs everything to database automatically.

### View Results (During or After):
```bash
python view_paper_trading.py
```

---

## Example Queries You Can Run

### Get Latest Session Summary:
```python
python view_paper_trading.py
```

### Query Database Directly:
```sql
-- All trades from latest session
SELECT * FROM paper_trading.trades 
WHERE session_id = (SELECT MAX(session_id) FROM paper_trading.sessions)
ORDER BY entry_timestamp;

-- Win rate by game
SELECT game_id, 
       COUNT(*) as trades,
       AVG(CASE WHEN won THEN 1.0 ELSE 0.0 END) as win_rate,
       SUM(net_profit) as total_pl
FROM paper_trading.trades
GROUP BY game_id;

-- Signals that weren't executed
SELECT * FROM paper_trading.signals 
WHERE executed = FALSE;

-- Price movements before signals
SELECT pd.timestamp, pd.price_mid, pd.score_diff, s.signal_id
FROM paper_trading.price_data pd
JOIN paper_trading.signals s ON pd.game_id = s.game_id
WHERE pd.timestamp BETWEEN s.timestamp - INTERVAL '5 minutes' AND s.timestamp;
```

---

## Benefits

### 1. Real-Time Monitoring
- Query database while paper trading is running
- See live P/L, win rate, signals

### 2. Historical Analysis
- Compare sessions over time
- Identify which games/situations work best
- Track model performance degradation

### 3. Advanced Analytics
- Join signals with features for analysis
- Time-series analysis of prices/scores
- Correlation between features and outcomes

### 4. No More CSV Parsing
- Clean, structured data
- Fast queries with indexes
- Easy to export for reports

---

## What Gets Logged

### Every 60 Seconds:
- Current price (bid/ask/mid) for each game
- Current score for each game
- Period and game time

### When Signal Generated:
- All signal details (price, probability, hold time)
- Current game state (score, period, minute)
- Can optionally log all 70 feature values

### When Trade Completes:
- Entry and exit details
- Full P/L breakdown (gross, fees, net)
- Actual hold duration vs predicted
- Whether trade won or lost

### At Session End:
- Summary statistics
- Total P/L, win rate
- Number of signals/trades

---

## Database Size Estimate

For tonight (6 games, 3 hours):
- **Price Data:** ~6 games × 180 polls = ~1,080 rows
- **Signals:** Estimate 6-12 signals total
- **Trades:** Same as signals (6-12 rows)
- **Features:** If logged, 70 × signals = 420-840 rows

**Total:** <2,000 rows per session (very small)

---

## ✅ READY FOR TONIGHT!

Everything is set up. When you run `python run_paper_trading.py`:

1. Creates new session in database
2. Logs every price/score poll
3. Logs every signal generated
4. Logs every trade with P/L
5. Updates session summary at end

Then run `python view_paper_trading.py` to see results!

---

## Example Output

```
================================================================================
SESSION SUMMARY
================================================================================

Session ID: 1
Start Time: 2025-12-29 18:00:00
End Time: 2025-12-29 21:00:00
Games Monitored: 6
Total Signals: 8
Total Trades: 8
Total P/L: $145.32
Win Rate: 62.5%

================================================================================
TRADE DETAILS
================================================================================

8 trades executed:
  [WIN] 0022500445: $48c -> $53c = $+18.45 (prob=65.2%)
  [LOSS] 0022500446: $52c -> $49c = $-22.15 (prob=61.3%)
  [WIN] 0022500441: $45c -> $51c = $+24.80 (prob=68.1%)
  ...

================================================================================
PER-GAME PERFORMANCE
================================================================================

  0022500445: 2 trades, 50.0% win rate, $12.30 P/L
  0022500446: 1 trades, 0.0% win rate, $-22.15 P/L
  0022500441: 3 trades, 66.7% win rate, $48.20 P/L
  ...
```

Perfect for analyzing what worked and what didn't!



