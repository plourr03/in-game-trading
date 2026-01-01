# NBA In-Game Trading System

A machine learning-powered trading system for Kalshi NBA markets that trades in real-time during games.

## 🚀 Quick Start

### Run Paper Trading (Recommended)
```bash
python run_paper_trading.py
```
Monitors all today's games, generates ML signals, simulates trades, logs to database.

### View Results
```bash
python view_paper_trading.py
```
Shows trading performance from database.

### Live Dashboard
```bash
python live_dashboard.py
```
Real-time monitoring of paper trading session with auto-refresh.

## 📁 Project Structure

```
in-game-trading/
├── run_paper_trading.py          # Main paper trading system
├── view_paper_trading.py          # View trading results
├── live_dashboard.py              # Live monitoring dashboard
├── plot_paper_trading_pl.py       # Visualize P/L over time
│
├── ml_models/                     # Machine learning models
│   ├── outputs/
│   │   ├── advanced_model.pkl     # Entry model (70 features, 99.7% AUC)
│   │   ├── exit_timing_model.pkl  # Static exit model
│   │   └── exit_timing_dynamic.pkl # Dynamic exit model (optional)
│   │
│   ├── train_advanced_features_model.py  # Train entry model
│   ├── create_advanced_features.py       # Feature engineering
│   └── EXIT_MODEL_RESULTS.md             # Exit model analysis
│
├── src/                           # Core modules
│   ├── data/
│   │   ├── kalshi_api.py         # Kalshi API client
│   │   ├── realtime_pbp.py       # NBA play-by-play fetcher
│   │   └── loader.py             # Data loading utilities
│   │
│   ├── backtesting/
│   │   └── fees.py               # Kalshi fee calculations
│   │
│   ├── paper_trading/
│   │   └── database_logger.py    # PostgreSQL logging
│   │
│   └── trading_engine/
│       ├── signals/              # Signal generators
│       ├── execution/            # Position management
│       └── visualization/        # Trade visualizations
│
├── kalshi_data/                   # Historical market data
│   └── jan_dec_2025_games/       # 578 games (Dec 2024 - Dec 2025)
│
├── keys.md                        # API keys (Kalshi)
├── config.yaml                    # Database configuration
│
└── archive/                       # Old/test files
    ├── test_scripts/             # Debug and test scripts
    └── old_docs/                 # Old documentation
```

## 🎯 Core Features

### 1. **Entry Model**
- **Type**: LightGBM classifier
- **Features**: 70 engineered features from price/score data
- **Performance**: 99.7% AUC
- **Threshold**: 60% probability to enter
- **Latest Results**: 71.4% win rate, +$1,114 profit (Session 5)

### 2. **Exit Strategy**
- **Static Exit**: Hold for 5 minutes (current default)
- **Hold-to-Expiration**: If price ≥ $95, Q4 ≤ 6min, score diff ≥ 11 points
  - Saves exit fees by holding to $1.00 payout
- **Dynamic Exit (Optional)**: ML-driven exit timing
  - Marginal improvement (<1%) over static
  - Available but not currently deployed

### 3. **Position Sizing**
- Default: 500 contracts per trade
- Dynamic sizing based on model confidence (future enhancement)

### 4. **Data Sources**
- **Kalshi API**: Real-time market prices
- **NBA API**: Live play-by-play data
- **PostgreSQL**: Trade logging and analysis

## 📊 Performance (Latest Session)

**Session 5 - Dec 30, 2025:**
- Duration: 3 hours
- Trades: 7 (6 on DET@LAL, 1 on SAC@LAC)
- Win Rate: 71.4% (5 wins, 2 losses)
- Total P/L: +$1,114.60
- Average P/L: +$159.23 per trade

**Key Insight**: Model captured major price movement ($50→$99) in DET@LAL game during Q4 blowout.

## 🔧 Configuration

### Database (PostgreSQL)
Edit `config.yaml`:
```yaml
database:
  host: localhost
  port: 5432
  database: nba_data
  user: nba_user
  password: your_password
```

### Kalshi API
Add to `keys.md`:
```
API_KEY
-----BEGIN RSA PRIVATE KEY-----
...
-----END RSA PRIVATE KEY-----
```

## 📈 Usage

### Paper Trading
```bash
# Start paper trading (runs for 6 hours or until all games end)
python run_paper_trading.py

# In another terminal, watch live
python live_dashboard.py
```

### After Trading
```bash
# View results
python view_paper_trading.py

# Generate P/L charts
python plot_paper_trading_pl.py
```

## 🧪 Model Training

### Retrain Entry Model
```bash
cd ml_models
python train_advanced_features_model.py
```

### Test Exit Strategies
```bash
cd ml_models
python test_exit_strategies.py
```

## 📝 Key Files to Know

- **`run_paper_trading.py`** - Main system, start here
- **`ml_models/EXIT_MODEL_RESULTS.md`** - Exit strategy analysis
- **`HOLD_TO_EXPIRATION.md`** - Hold-to-expiration optimization
- **`HOW_TO_MONITOR_LIVE.md`** - Live monitoring guide

## 🎓 System Design

### Trade Flow
1. **Monitor** games every 60 seconds
2. **Calculate** 70 features from live data
3. **Predict** entry probability with ML model
4. **Enter** if probability > 60%
5. **Hold** for 5 minutes (or to expiration if conditions met)
6. **Exit** and calculate P/L with Kalshi fees

### Smart Features
- **Auto-detects finished games** (status = 3)
- **Countdown for upcoming games** ("Starts in X minutes")
- **Overtime detection** (continues monitoring through OT)
- **Auto-finish** when all games end
- **Database logging** for all signals and trades

## 🔮 Future Enhancements

1. **Dynamic position sizing** based on model confidence
2. **Ensemble models** for improved robustness
3. **Real-time feature importance** tracking
4. **Advanced exit timing** (dynamic ML model available)
5. **Multi-market support** (over/under, player props)

## 📚 Documentation

- **Setup**: `HOW_TO_MONITOR_LIVE.md`
- **Exit Strategy**: `ml_models/EXIT_MODEL_RESULTS.md`
- **Optimization**: `HOLD_TO_EXPIRATION.md`

## ⚠️ Important Notes

- This is **paper trading only** - no real money
- Kalshi fees are included in P/L calculations
- ML model needs 15 minutes of data before trading
- Session logs stored in PostgreSQL database

## 🏆 Status

**✅ System is production-ready for paper trading**
- Successfully tested on multiple live sessions
- 71.4% win rate demonstrated
- Robust error handling and logging
- Auto-finish and overtime support

---

**Last Updated**: January 1, 2026
**Version**: 2.0 (Cleaned and Organized)
