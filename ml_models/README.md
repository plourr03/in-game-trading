# ML Models for NBA In-Game Trading

This folder contains machine learning models to predict trading entry points and optimize hold durations.

## 🎯 Goal

Build ML models that learn from historical data to:
1. **Entry Prediction**: Decide when to enter trades (avoid losing conditions)
2. **Hold Duration Optimization**: Dynamically adjust hold periods (3, 5, 7, 12, or 15 minutes)

## 📁 Structure

```
ml_models/
├── prepare_training_data.py    # Create training dataset from historical data
├── train_models.py              # Train entry + hold duration models
├── backtest_comparison.py       # Compare ML vs rules-based strategies
├── run_complete_pipeline.py     # Master script to run everything
├── outputs/                     # Model artifacts and results
│   ├── training_data.csv
│   ├── entry_model.pkl
│   ├── entry_scaler.pkl
│   ├── entry_features.pkl
│   ├── hold_duration_model.pkl
│   ├── hold_duration_scaler.pkl
│   ├── hold_duration_features.pkl
│   ├── feature_importance_entry.png
│   ├── feature_importance_hold.png
│   ├── ml_backtest_trades.csv
│   └── rules_backtest_trades.csv
└── README.md                    # This file
```

## 🚀 Quick Start

Run the complete pipeline:

```bash
python ml_models/run_complete_pipeline.py
```

This will:
1. Prepare training data (~680k samples)
2. Train entry prediction model
3. Train hold duration optimizer
4. Backtest ML vs best rules-based strategy
5. Save all results to `outputs/`

## 📊 Models

### 1. Entry Prediction Model

**Purpose**: Predict if ANY hold period will be profitable

**Features** (19 total):
- Price features: current_price, price_move_1min, price_move_3min, price_move_5min, volatility_5min
- Market: spread, volume_spike
- Game state: score_diff, score_diff_abs, time_remaining, period
- Price regime: is_extreme_low, is_extreme_high, is_extreme_price, is_mid_price
- Context: is_close_game, is_late_game, is_very_late
- Momentum: large_move, huge_move

**Target**: Binary (1 = profitable, 0 = not profitable)

**Algorithm**: Tests Logistic Regression, Random Forest, Gradient Boosting (picks best)

### 2. Hold Duration Optimizer

**Purpose**: Predict optimal hold period for profitable trades

**Features** (15 total):
- Subset of entry features (most predictive)

**Target**: Multi-class (3, 5, 7, 12, or 15 minutes)

**Algorithm**: Random Forest Classifier

## 💡 Why ML Over Rules?

**Problem with Rules-Based Strategies**:
- Fixed criteria miss nuanced patterns
- Same strategy performs differently in different games
- Demo showed 37% win rate, -$332 P/L on 962 trades
- Best game: 54% win rate vs Worst: 17% win rate

**ML Advantages**:
1. **Adaptive**: Learns when markets are tradeable vs untradeable
2. **Multi-factor**: Combines price, game state, momentum in complex ways
3. **Dynamic**: Adjusts hold periods based on conditions
4. **Selective**: Filters out low-probability setups

**Expected Improvements**:
- Target 50-55% win rate (vs 37%)
- Reduce number of trades (more selective)
- Higher avg P/L per trade
- Better game selection (avoid 17% win rate games)

## 📈 Evaluation Metrics

**Entry Model**:
- AUC (Area Under ROC Curve)
- Precision/Recall
- Confusion Matrix

**Hold Duration Model**:
- Accuracy
- Per-class precision

**Backtest**:
- Total trades
- Win rate
- Avg P/L per trade
- Total P/L
- Sharpe ratio
- Avg fees

## 🔬 Training Process

### Data Preparation

1. Load Kalshi candlestick data (502 games)
2. Load play-by-play data
3. Merge and align by game minute
4. Engineer 19+ features
5. Calculate profitability for each hold period (3, 5, 7, 12, 15 min)
6. Save ~680k training samples

### Model Training

1. **Train/Test Split**: 80/20 time-based (last 20% for testing)
2. **Scaling**: StandardScaler on features
3. **Class Weights**: Balanced to handle class imbalance
4. **Cross-validation**: Optional for hyperparameter tuning
5. **Model Selection**: Pick best based on AUC/accuracy

### Backtesting

1. Select 20 test games (out-of-sample)
2. Run ML strategy: Entry model filters, hold model optimizes
3. Run best rules strategy: 1-5¢, >20% move, 3min hold
4. Compare: trades, win rate, P/L, Sharpe ratio

## 🎓 Feature Importance

After training, check:
- `feature_importance_entry.png` - Which features matter most for entry?
- `feature_importance_hold.png` - Which features determine hold duration?

Common top features:
- `price_move_1min` - Recent momentum
- `is_extreme_price` - Low fees at 1-10¢ or 90-99¢
- `volatility_5min` - Market volatility
- `time_remaining` - Game stage
- `huge_move` - Large price swings

## 📝 Results Interpretation

### If ML Wins:
```
✓ SUCCESS! ML Strategy outperforms by $X.XX
  (+XX% improvement)
```
→ Integrate into `trading_engine/` for live use

### If Rules Win:
```
⚠ Rules strategy still better by $X.XX
  ML needs more training or different features
```
→ Try:
- Add more features (play-by-play events, momentum indicators)
- Different ML algorithms (XGBoost, Neural Networks)
- Hyperparameter tuning
- More training data

## 🔄 Retraining

To retrain on new data:

```bash
# 1. Prepare new data
python ml_models/prepare_training_data.py

# 2. Train models
python ml_models/train_models.py

# 3. Evaluate
python ml_models/backtest_comparison.py
```

## 🚀 Next Steps

1. **Run pipeline** → Get baseline ML performance
2. **Analyze feature importance** → Understand what drives predictions
3. **Tune hyperparameters** → Optimize if needed
4. **A/B test** → If ML wins, integrate into trading_engine
5. **Monitor** → Track real performance vs backtest

## 📊 Expected Output

```
====================================================================================================
BACKTEST RESULTS
====================================================================================================

Metric               ML Strategy        Rules Strategy          Difference
----------------------------------------------------------------------------------------------------
Total Trades                 XXX                   XXX                  +/-XX
Win Rate               XX.X%                 XX.X%               +/-X.X%
Avg P/L per Trade    $X.XX                 $X.XX               +/-$X.XX
Total P/L           $X.XX                 $X.XX               +/-$X.XX
Sharpe Ratio            X.XX                  X.XX                 +/-X.XX
Avg Fees            $X.XX                 $X.XX               +/-$X.XX

====================================================================================================
VERDICT
====================================================================================================

✓ SUCCESS! ML Strategy outperforms by $X.XX (+XX% improvement)
```

---

**Built with**: scikit-learn, pandas, numpy, matplotlib, seaborn

**Author**: AI Trading System

**Last Updated**: Dec 28, 2025





