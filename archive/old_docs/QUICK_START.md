# 🚀 QUICK START - Tonight's Paper Trading

## Before 6 PM (Pre-Flight):

```bash
python preflight_check.py
```

Expected output: "ALL SYSTEMS GO!"

---

## At 6 PM (Launch):

```bash
python run_paper_trading.py
```

**Let it run for 3+ hours** (or until Ctrl+C to stop)

---

## What You'll See:

```
[Iteration 1] 18:00:15
--------------------------------------------------------------------------------
  DET@LAC: Q1 | 2-5 (diff:-3) | $48c | 12 pts
  SAC@LAL: Q1 | 8-6 (diff:+2) | $52c | 15 pts
    [SIGNAL] BUY $52c (prob=65.2%, hold=7min)
  GSW@TOR: Q2 | 35-42 (diff:-7) | $38c | 25 pts
  PHI@OKC: Q2 | 48-51 (diff:-3) | $47c | 28 pts
    [SIGNAL] BUY $47c (prob=62.1%, hold=5min)
    [WIN] Exit at $53c -> P/L: $+18.45
  ...
```

---

## After Session:

Check these files:
- `paper_signals_*.csv` - All signals
- `paper_trades_*.csv` - All completed trades with P/L
- `paper_prices_*.csv` - All data collected

---

## Key Metrics to Check:

1. **Win Rate:** Should be close to 62.5% (backtest result)
2. **Total P/L:** Should be positive if model works
3. **Number of Trades:** Should be ~1-2 per game (6-12 total if all games traded)
4. **Average Probability:** Signals should average 60-70%

---

## ✅ YOU'RE READY!

Just run the script at 6 PM and let it do its thing. No interaction needed.
