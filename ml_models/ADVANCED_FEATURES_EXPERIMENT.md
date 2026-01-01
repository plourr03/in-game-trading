# 🔬 Testing Advanced PBP Features for Higher Trade Frequency

## Goal
Find a model that generates MORE trading opportunities while maintaining high win rate.

## Problem with Current Models
- Optimized LightGBM: **76.5% win rate** but only **17 trades from 502 games** (3.4% entry rate)
- Baseline LightGBM: **72.4% win rate** but only **29 trades** (5.8% entry rate)
- At lower thresholds: Win rate drops below 50%, loses money

**Conclusion: Models are TOO selective!**

---

## New Approach: Comprehensive Play-by-Play Features

### Added 50+ new features:

#### Price Features (Extended)
- price_move_2min, price_move_10min
- volatility_3min, volatility_10min  
- price_range_5min
- price_reversing, price_trending_up/down
- price_accelerating

#### Volume Features
- volume_ma3, volume_ma10
- volume_trend
- volume_spike (refined)

#### Score Features
- score_total
- score_diff_1min, score_diff_3min, score_diff_5min
- scoring_rate_1min, scoring_rate_3min, scoring_rate_5min

#### Momentum Features
- home_momentum_3min, home_momentum_5min
- away_momentum_3min, away_momentum_5min
- lead_change_recent
- comeback_attempt

#### Game State Features
- minutes_into_period
- is_period_1, is_period_2, is_period_3, is_period_4
- is_early_period, is_late_period
- is_very_close, is_blowout
- is_crunch_time (late + close)

#### Pattern Features
- consecutive_scores
- scoring_drought
- high_scoring
- price_score_alignment/misalignment

#### Context Features
- score_vs_expectation
- pace (points per minute)

---

## Hypothesis

**More granular PBP features will help the model:**
1. Identify more subtle trading opportunities
2. Better understand game momentum and flow
3. Recognize patterns that lead to profitable trades
4. Maintain high win rate while increasing trade frequency

---

## Target

- **50-100 trades per 502 games** (10-20% entry rate)
- **65-70% win rate** (profitable at 500 contracts)
- Total P/L: **+$500-1000** on full dataset

---

## Status

✅ Feature creation: **IN PROGRESS** (running in background)
⏳ Model training: PENDING
⏳ Backtesting: PENDING

---

## Next Steps

1. Train LightGBM, XGBoost, CatBoost with new features
2. Test at thresholds 0.5, 0.6, 0.7, 0.8
3. Find optimal balance: trades × win_rate × avg_pl
4. If successful: Deploy with 500-1000 contracts

---

**This is the best shot at finding more opportunities without sacrificing too much win rate!**





