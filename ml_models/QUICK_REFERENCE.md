# Quick Reference: ML Models & Usage

## 🎯 Best Models Available

### 1. Optimized LightGBM ⭐ (RECOMMENDED)
**Best for: Highest win rate, quality over quantity**

- **File**: `ml_models/outputs/optimized_entry_model.pkl`
- **Win Rate**: 76.5%
- **Features**: 13 selected features
- **Threshold**: 0.85
- **Expected Trades**: ~17 per 20 games
- **P/L (500 contracts)**: +$70

**How to use:**
```python
import joblib
model = joblib.load('ml_models/outputs/optimized_entry_model.pkl')
features = joblib.load('ml_models/outputs/optimized_entry_features.pkl')
# Predict: model.predict_proba(X)[:, 1] >= 0.85
```

### 2. Baseline LightGBM
**Best for: More trades, higher total volume**

- **File**: `ml_models/outputs/best_entry_model.pkl`
- **Win Rate**: 72.4%
- **Features**: 23 features (all)
- **Threshold**: 0.8
- **Expected Trades**: ~29 per 20 games
- **P/L (500 contracts)**: +$90

**How to use:**
```python
import joblib
model = joblib.load('ml_models/outputs/best_entry_model.pkl')
scaler = joblib.load('ml_models/outputs/best_entry_scaler.pkl')
features = joblib.load('ml_models/outputs/best_entry_features.pkl')
# Scale and predict: model.predict_proba(scaler.transform(X))[:, 1] >= 0.8
```

---

## 📋 Feature Lists

### Optimized Model (13 features):
```
current_price, time_remaining, volatility_5min, volume_spike,
price_move_1min, price_move_3min, price_move_5min, spread,
is_extreme_price, is_mid_price, large_move, huge_move, period
```

### Baseline Model (23 features):
```
current_price, price_move_1min, price_move_3min, price_move_5min,
volatility_5min, spread, volume_spike, score_diff, score_diff_abs,
time_remaining, period, scoring_rate_3min, score_momentum,
lead_extending, is_extreme_low, is_extreme_high, is_extreme_price,
is_mid_price, is_close_game, is_late_game, is_very_late,
large_move, huge_move
```

---

## 💰 Position Sizing Guide

| Contracts | Entry Fee | Exit Fee | Total Fees | Break-even Win Rate |
|-----------|-----------|----------|------------|---------------------|
| 100 | $2 | $2 | $4 | ~75% (borderline) |
| 500 | $5 | $5 | $10 | ~68% ✅ |
| 1000 | $10 | $10 | $20 | ~65% ✅✅ |

**Recommendation**: Use **500+ contracts** for profitability

---

## 🎯 Optimal Thresholds by Model

| Model | Threshold | Win Rate | Trades | P/L (500c) |
|-------|-----------|----------|--------|------------|
| Optimized | 0.85 | 76.5% | 17 | +$70 ✅ |
| Optimized | 0.80 | 70.8% | 24 | -$36 |
| Baseline | 0.80 | 72.4% | 29 | +$90 ✅ |
| Baseline | 0.75 | 68% | 40+ | Break-even |

---

## 🚀 Recommended Strategies

### Strategy A: Conservative (Optimized Model)
```
Model: Optimized LightGBM
Threshold: 0.85
Contracts: 500
Expected Win Rate: 76.5%
Expected P/L: +$70 per 20 games
```

### Strategy B: Aggressive (Baseline Model)
```
Model: Baseline LightGBM
Threshold: 0.80
Contracts: 500
Expected Win Rate: 72.4%
Expected P/L: +$90 per 20 games
```

### Strategy C: Extreme Prices (Best Fees)
```
Model: Optimized LightGBM
Threshold: 0.85
Price Filter: 1-5¢ only
Contracts: 500
Expected P/L: +$150-200 per 20 games
```

### Strategy D: ML + Validated Rules (Maximum)
```
Step 1: Filter with 58 validated strategies
Step 2: ML confirmation (Optimized, threshold 0.85)
Contracts: 1000
Expected P/L: +$300-500 per 20 games
```

---

## 📊 Model Performance Summary

```
Random Forest (baseline)
  ├─ Win Rate: 64.7%
  ├─ AUC: 0.942
  └─ P/L (500c): $0

Neural Network
  ├─ Win Rate: ~64%
  ├─ AUC: 0.945
  └─ P/L: Not tested

XGBoost
  ├─ AUC: 0.947
  └─ P/L: Not tested

CatBoost
  ├─ AUC: 0.946
  └─ P/L: Not tested

LightGBM (Baseline)
  ├─ Win Rate: 72.4% ⭐
  ├─ AUC: 0.948
  ├─ Trades: 29
  └─ P/L (500c): +$90 ✅

LightGBM (Optimized) ⭐⭐
  ├─ Win Rate: 76.5% ⭐⭐
  ├─ AUC: 0.9482
  ├─ Trades: 17
  └─ P/L (500c): +$70 ✅
```

---

## 🔧 Quick Test Scripts

### Test Optimized Model:
```bash
python ml_models/test_optimized_model.py
```

### Test Baseline Model:
```bash
python ml_models/test_lightgbm.py
```

### Run Feature Selection:
```bash
python ml_models/feature_selection.py
```

### Run Hyperparameter Tuning:
```bash
python ml_models/hyperparameter_tuning.py
```

### Compare All Models:
```bash
python ml_models/train_advanced_models.py
```

---

## 📁 File Structure

```
ml_models/
├── outputs/
│   ├── best_entry_model.pkl          (Baseline LightGBM)
│   ├── best_entry_scaler.pkl
│   ├── best_entry_features.pkl
│   ├── optimized_entry_model.pkl     (Optimized LightGBM) ⭐
│   ├── optimized_entry_features.pkl
│   ├── optimized_hyperparameters.json
│   ├── selected_features.json
│   ├── feature_selection.png
│   └── training_data.csv
│
├── train_advanced_models.py
├── feature_selection.py
├── hyperparameter_tuning.py
├── test_lightgbm.py
├── test_optimized_model.py
│
└── Documentation/
    ├── ADVANCED_MODELS_RESULTS.md
    ├── OPTIMIZATION_RESULTS.md
    ├── COMPLETE_OPTIMIZATION_SUMMARY.md
    └── QUICK_REFERENCE.md (this file)
```

---

## ✅ Checklist for Deployment

- [ ] Choose model (Optimized or Baseline)
- [ ] Set threshold (0.85 for Optimized, 0.8 for Baseline)
- [ ] Set position size (500-1000 contracts)
- [ ] Optional: Add price filter (1-5¢ for lower fees)
- [ ] Optional: Combine with validated strategies
- [ ] Monitor performance on live data
- [ ] Adjust threshold if needed

---

## 💡 Pro Tips

1. **Use Optimized Model for quality**: Higher win rate, fewer trades
2. **Use Baseline Model for volume**: More trades, higher total P/L
3. **Scale to 500+ contracts**: Required for profitability
4. **Target extreme prices**: 4× cheaper fees at 1-5¢
5. **Combine with rules**: ML + validated strategies = best results
6. **Monitor and adjust**: Thresholds may need tuning on new data

---

**Quick answer: Both models are profitable at 500+ contracts. Use Optimized for highest win rate (76.5%), use Baseline for more trades (+$90 profit).**

---

Generated: Dec 28, 2025





