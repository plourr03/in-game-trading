# Project Structure - Clean & Organized

## 🎯 Essential Files (Root Directory)

### Main Scripts
- **`run_paper_trading.py`** - Main paper trading system (START HERE)
- **`view_paper_trading.py`** - View trading results from database
- **`live_dashboard.py`** - Real-time monitoring dashboard
- **`plot_paper_trading_pl.py`** - Generate P/L visualization charts

### Configuration
- **`config.yaml`** - Database configuration
- **`keys.md`** - Kalshi API credentials
- **`requirements.txt`** - Python dependencies

### Documentation
- **`README.md`** - Main project documentation
- **`HOW_TO_MONITOR_LIVE.md`** - Guide for live monitoring
- **`HOLD_TO_EXPIRATION.md`** - Exit optimization strategy

---

## 📂 Core Directories

### `src/` - Core Application Code

```
src/
├── data/              # Data fetching and processing
│   ├── kalshi_api.py      # Kalshi API client
│   ├── realtime_pbp.py    # NBA play-by-play fetcher
│   └── loader.py          # Data loading utilities
│
├── backtesting/       # Backtesting framework
│   ├── fees.py            # Kalshi fee calculations
│   ├── framework.py       # Backtest engine
│   └── rules.py           # Trading rules
│
├── paper_trading/     # Paper trading infrastructure
│   └── database_logger.py # PostgreSQL logging
│
├── trading_engine/    # Live trading components
│   ├── signals/           # Signal generators
│   ├── execution/         # Position management
│   └── visualization/     # Trade visualizations
│
├── features/          # Feature engineering
│   ├── basic.py           # Basic price features
│   ├── momentum.py        # Momentum indicators
│   └── game_state.py      # Game state features
│
└── analysis/          # Analysis modules
    ├── edge_cases.py      # Edge detection
    ├── volatility.py      # Volatility analysis
    └── momentum_runs.py   # Momentum analysis
```

### `ml_models/` - Machine Learning Models

```
ml_models/
├── outputs/                          # Trained models
│   ├── advanced_model.pkl           # Entry model (MAIN)
│   ├── advanced_features.pkl        # Feature list
│   ├── exit_timing_model.pkl        # Static exit model
│   └── exit_timing_dynamic.pkl      # Dynamic exit model
│
├── train_advanced_features_model.py # Train entry model
├── create_advanced_features.py      # Feature engineering
├── train_exit_model.py              # Train exit model
│
├── EXIT_MODEL_RESULTS.md            # Exit model analysis
└── DYNAMIC_EXIT_SUMMARY.md          # Dynamic exit summary
```

### `kalshi_data/` - Historical Market Data

```
kalshi_data/
└── jan_dec_2025_games/              # 578 games
    ├── 0022500001_PHX_at_LAL_2024-10-22_candles.csv
    ├── 0022500002_LAC_at_GSW_2024-10-23_candles.csv
    └── ...
```

### `archive/` - Old/Test Files

```
archive/
├── test_scripts/        # 53 test/debug scripts
│   ├── test_*.py
│   ├── check_*.py
│   ├── debug_*.py
│   └── ...
│
└── old_docs/           # Old documentation
    ├── *SUMMARY*.md
    ├── *REPORT*.md
    └── ...
```

---

## 🚀 Quick Navigation

### Want to...

**Run paper trading?**
→ `run_paper_trading.py`

**View results?**
→ `view_paper_trading.py`

**Monitor live?**
→ `live_dashboard.py`

**Retrain models?**
→ `ml_models/train_advanced_features_model.py`

**Understand exit strategy?**
→ `ml_models/EXIT_MODEL_RESULTS.md`

**Check configuration?**
→ `config.yaml` (database) or `keys.md` (API)

---

## 📊 File Count Summary

| Category | Location | Files |
|----------|----------|-------|
| Main Scripts | Root | 4 |
| Configuration | Root | 3 |
| Documentation | Root | 3 |
| Core Code | `src/` | ~30 |
| ML Models | `ml_models/` | ~20 active |
| Historical Data | `kalshi_data/` | 578 games |
| **Archived** | `archive/` | **~150 old files** |

---

## 🧹 What Was Archived?

### Test Scripts (53 files)
- `test_*.py`, `check_*.py`, `debug_*.py`
- `fetch_*.py`, `verify_*.py`, `diagnose_*.py`
- Old simulators and validators

### Old Documentation (~100 files)
- Progress reports and summaries
- Experiment logs
- Analysis outputs
- Old charts and CSVs

### Why Archive?
- **Cleaner project structure**
- **Easier to navigate**
- **Focus on production code**
- **Nothing was deleted** - all in `archive/` if needed

---

## 💡 Best Practices

### Adding New Files
- **Scripts**: Add to root only if essential, otherwise `archive/test_scripts/`
- **Docs**: Update `README.md` or create in root if important
- **Models**: Put in `ml_models/outputs/`
- **Data**: Goes in `kalshi_data/`

### Before Committing
1. Check if file is production-ready
2. If it's a test/experiment → `archive/test_scripts/`
3. If it's a draft/log → `archive/old_docs/`
4. Keep root directory clean!

---

**Last Cleaned**: January 1, 2026
**Status**: ✅ Clean and Organized

