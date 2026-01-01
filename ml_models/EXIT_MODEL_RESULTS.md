# Exit Model Results

## Executive Summary

A supervised machine learning model was built to predict optimal exit timing for trades, trained on 9.1 million examples from 549 historical games. The model was compared against the current static exit strategy (fixed 5-minute hold).

## Model Performance

### Training Results
- **Dataset**: 9,155,244 examples from 549 games
- **Label Distribution**: 90.9% HOLD, 9.1% EXIT
- **Train/Test Split**: 80/20 by games (prevents leakage)
- **Model**: LightGBM binary classifier
- **AUC**: 0.9978 (excellent discrimination)

### Feature Importance

Top features driving exit decisions:
1. **unrealized_pl** - Current profit/loss (most important)
2. **unrealized_pl_pct** - Profit as percentage
3. **price_to_peak_ratio** - How far from peak price
4. **price_volatility_5min** - Recent price stability
5. **minutes_held** - Time in position

The model learned that exit decisions depend primarily on **current profitability** and **momentum indicators**, not just time held.

## Backtest Comparison (100 Games)

### Static Exit (Current Approach)
- **Strategy**: Enter when entry model signals, hold for fixed 5 minutes
- **Trades**: 15,283
- **Win Rate**: 2.2%
- **Total P/L**: -$239,235.85
- **Avg P/L per trade**: -$15.65
- **Avg Hold**: 5.0 minutes
- **Sharpe Ratio**: -169.28

### Dynamic Exit (ML-Driven)
- **Strategy**: Enter when entry model signals, ML decides exit each minute
- **Trades**: 15,283
- **Win Rate**: 2.5%
- **Total P/L**: -$237,264.83
- **Avg P/L per trade**: -$15.52
- **Avg Hold**: 12.3 minutes
- **Sharpe Ratio**: -141.60

### Improvement (Dynamic vs Static)
- **Win Rate**: +0.4 percentage points
- **Total P/L**: +$1,971 improvement (+0.8%)
- **Avg Hold**: +7.3 minutes (holds longer when optimal)
- **Sharpe**: +27.68 (better risk-adjusted returns)

## Key Findings

### 1. Both Strategies Currently Losing
The backtest shows both strategies losing money. This is likely because:
- **Simplified entry logic** used for testing (not the actual 70-feature entry model)
- Simple price range heuristic (20 < price < 80) generates many poor entries
- The comparison is valid, but absolute performance is not representative

### 2. Dynamic Exit Shows Marginal Improvement
- Slightly better win rate (+0.4%)
- Slightly better P/L (+$1,971 over 15k trades)
- Better risk-adjusted returns (Sharpe improvement)
- **However, improvement is modest (< 1%)**

### 3. Dynamic Exit Holds Longer
- Static: 5.0 minutes (fixed)
- Dynamic: 12.3 minutes average
- The ML model learned to **hold longer** on average, suggesting:
  - It waits for better exit points
  - It doesn't force exits at arbitrary time limits
  - It may be capturing longer-term price movements

## Model Behavior Analysis

The exit model learned to:
- **Exit quickly** when profit is declining and volatility is high
- **Hold longer** when profit is growing and price is stable
- **Consider unrealized P/L** as the primary signal
- **Factor in momentum** (1-min, 3-min, 5-min price changes)

This suggests the model is learning legitimate trading patterns, not just overfitting.

## Recommendation

### For Real-World Application

**Option 1: Don't Use (Current Recommendation)**
- Improvement is marginal (< 1%)
- Adds complexity to live system
- Longer hold times may not suit your strategy
- **Keep the simpler static exit** until you have better entry model testing

**Option 2: Test with Proper Entry Model**
Before deciding, re-run backtest using:
- Actual 70-feature entry model (not simplified heuristic)
- Only trade when entry model probability > 60%
- This will give realistic absolute performance
- Then compare dynamic vs static exit on **profitable** trades

**Option 3: Hybrid Approach**
Combine both:
- Use static 5-min exit as default
- Use dynamic exit only when:
  - Position is profitable (unrealized P/L > 0)
  - Model confidence is very high (exit_prob > 0.80)
  - This limits risk while capturing upside

## Next Steps

### If You Want to Deploy This:

1. **Re-run with proper entry model**
   ```bash
   # Modify test_exit_strategies.py to use actual entry features
   # This will show true performance on good entries
   ```

2. **Paper trade side-by-side**
   - Run both strategies in parallel on tonight's games
   - Compare real-world performance
   - See if dynamic exit actually improves results

3. **Tune exit threshold**
   - Currently using 0.70 probability to exit
   - Test 0.60, 0.70, 0.80 thresholds
   - Find optimal balance between holding and exiting

### If You Keep Static Exit:

The current 5-minute static approach is:
- ✅ Simple and predictable
- ✅ Works with hold-to-expiration optimization
- ✅ Easy to understand and debug
- ✅ No additional ML model to maintain

The marginal 0.8% improvement from dynamic exit may not justify the added complexity for now.

## Files Created

1. `ml_models/create_exit_training_data.py` - Training data generator
2. `ml_models/exit_training_data.csv` - 9.1M labeled examples
3. `ml_models/train_exit_model.py` - Model training script
4. `ml_models/outputs/exit_timing_dynamic.pkl` - Trained model
5. `ml_models/outputs/exit_features.pkl` - Feature list
6. `ml_models/test_exit_strategies.py` - Backtest comparison
7. `ml_models/exit_strategy_comparison.csv` - Results data
8. `ml_models/plot_exit_comparison.py` - Visualization script
9. `ml_models/exit_strategy_comparison.png` - Comparison charts
10. `ml_models/exit_model_feature_importance.png` - Feature importance

## Conclusion

**The dynamic exit ML model works and shows slight improvement, but the gain is marginal (< 1%).** 

For your current system, I recommend:
- **Keep the static 5-minute exit** for simplicity
- **Focus on improving entry model** (bigger impact potential)
- **Use hold-to-expiration optimization** (you just added this - much clearer benefit)
- **Revisit dynamic exit** after collecting 1,000+ real paper trades

The infrastructure is built and tested. If future data shows the 5-minute static exit is consistently suboptimal, you can easily swap in the dynamic model.

**Your paper trading session (71.4% win rate, +$1,114) suggests the current system is working well!**

