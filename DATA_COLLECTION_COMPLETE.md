# 📊 Data Collection & Model Retraining - Complete Guide

## ✅ Current Situation

**Kalshi Historical Data:**
- ❌ Not available for games from last 1-3 days
- ❌ Candlesticks endpoint returns 404
- ❌ History endpoint returns empty
- ⏰ Data becomes available 3-7 days after game

**Solution:**
- ✅ Use tonight's paper trading as data collection
- ✅ Export collected data tomorrow
- ✅ Retrain model with fresh data weekly

---

## 🔄 Complete Workflow

### Tonight (Dec 29): Collect Data
```bash
# Run paper trading (6 PM - 9:30 PM Central)
python run_paper_trading.py
```

**What happens:**
- Monitors 6 games
- Polls Kalshi + NBA every 60 seconds
- Logs ~1,080 price/score data points
- Saves to database + CSV

### Tomorrow (Dec 30): Export Data
```bash
# Export tonight's data to training format
python export_paper_trading_data.py
```

**What happens:**
- Reads data from `paper_trading.price_data` table
- Converts to Kalshi CSV format
- Saves 6 new CSV files to `kalshi_data/jan_dec_2025_games/`
- Ready for model retraining

### Weekly: Retrain Model
```bash
cd ml_models
python prepare_training_data.py
python train_models.py
```

**What happens:**
- Loads all CSV files (502 existing + 6 new = 508 games)
- Engineers 70 features
- Trains CatBoost + LightGBM models
- Saves updated models to `ml_models/outputs/`

---

## 📁 Files Created

### Data Collection:
- `fetch_missing_kalshi_data.py` - Tries to fetch from Kalshi API (doesn't work for recent games)
- `export_paper_trading_data.py` - Exports paper trading data to training format ✅

### Documentation:
- `DATA_COLLECTION_STRATEGY.md` - Complete strategy guide

---

## 📊 Data Format

### Paper Trading Database:
```sql
paper_trading.price_data:
  - timestamp, game_id, ticker
  - price_mid, price_bid, price_ask
  - score_home, score_away
  - period, game_minute
```

### Training Data CSV:
```
datetime, open, high, low, close, volume
ticker, game_id, away_team, home_team, game_date
```

**Mapping:**
- `datetime` = `timestamp`
- `close` = `price_mid`
- `open` = `price_bid`
- `high` = `price_ask`
- `low` = `price_mid`
- `volume` = 0 (not available)

---

## 🎯 Benefits

### Using Paper Trading as Data Collection:

**Advantages:**
1. ✅ Real-time, accurate data
2. ✅ No API availability delays
3. ✅ Exactly what model sees in production
4. ✅ High frequency (every 60 seconds)
5. ✅ Continuous data stream
6. ✅ Quality controlled (you collected it)

**Disadvantages:**
1. ⚠️ Only games you monitored
2. ⚠️ Requires running paper trading

### Data Growth:
- **Per Session:** ~6-12 games
- **Per Week:** ~35-50 games (if running daily)
- **Per Month:** ~140-200 games

Your 502 existing games will grow to **700+ games in 2 months!**

---

## 📈 Model Improvement Strategy

### Week 1 (Tonight - Jan 5):
- Collect data nightly
- Paper trade every night's games
- Export data daily
- Don't retrain yet (collecting baseline)

### Week 2 (Jan 6-12):
- **Retrain** model with 50+ new games
- Test updated model
- Compare performance vs old model
- If better, use new model

### Monthly (Feb 1):
- **Retrain** with 200+ new games
- Analyze which features improved
- Consider adding new features
- A/B test thresholds

### Quarterly (Apr 1):
- **Full reanalysis** with 600+ games
- Check for concept drift
- Update feature engineering
- Consider new ML architectures

---

## 🔧 Commands Reference

### Run Paper Trading (Collect Data):
```bash
python run_paper_trading.py
```

### Export Data (Next Day):
```bash
python export_paper_trading_data.py
```

### Retrain Model (Weekly):
```bash
cd ml_models
python prepare_training_data.py    # Create training data
python train_models.py              # Train models
```

### Test Model (After Retraining):
```bash
python test_optimized_model.py --threshold 0.60
```

### View Results (Anytime):
```bash
python view_paper_trading.py
```

---

## 🎯 Success Metrics

### Data Collection Quality:
- ✅ All 6 games monitored
- ✅ 150+ data points per game
- ✅ No missing timestamps
- ✅ Scores change over time

### Model Retraining:
- ✅ Training completes without errors
- ✅ Model metrics comparable or better
- ✅ Backtest win rate maintains 55%+
- ✅ Live performance improves

---

## ✅ READY TO GO

You have everything you need:

1. **Tonight:** `python run_paper_trading.py` - Collect data
2. **Tomorrow:** `python export_paper_trading_data.py` - Export data
3. **Weekly:** Retrain model with fresh data

**The ML model will continuously improve as you collect more recent game data!** 🚀


