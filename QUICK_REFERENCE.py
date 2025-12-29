"""Generate a quick reference card for printing/quick access"""

print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    KALSHI NBA TRADING: QUICK REFERENCE                       ║
║                         195 Profitable Edges Found                           ║
╚══════════════════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────────────────────┐
│ TOP 5 STRATEGIES - MEMORIZE THESE                                           │
└──────────────────────────────────────────────────────────────────────────────┘

1. HIGHEST PROFIT
   Price: 95-99¢  |  Move: >25%  |  Hold: 12min  |  P/L: +12.93%
   
2. HIGH PROFIT  
   Price: 1-5¢    |  Move: >25%  |  Hold: 5min   |  P/L: +6.34%
   
3. HIGH FREQUENCY
   Price: 1-20¢   |  Move: >12%  |  Hold: 3min   |  P/L: +0.21%
   136 opportunities per 502 games = Most reliable
   
4. BALANCED
   Price: 1-5¢    |  Move: >15%  |  Hold: 3min   |  P/L: +2.66%
   
5. PATIENT
   Price: 90-99¢  |  Move: >20%  |  Hold: 12min  |  P/L: +4.61%

┌──────────────────────────────────────────────────────────────────────────────┐
│ THE CORE INSIGHT                                                             │
└──────────────────────────────────────────────────────────────────────────────┘

WHY THIS WORKS:
  • Kalshi Fee = 7% × P × (1-P)
  • At 50¢: 3.5% round-trip (EXPENSIVE)
  • At 5¢ or 95¢: 0.66% round-trip (CHEAP) ← 5x LOWER!
  • Mean reversion (60-100% win rate) + Low fees = PROFIT

PATTERN:
  • Extreme prices (1-20¢ or 80-99¢)
  • Large moves (>12-25%)
  • Fade the move (bet on reversal)
  • Hold 2-15 minutes (optimal: 12 minutes)

┌──────────────────────────────────────────────────────────────────────────────┐
│ EXECUTION CHECKLIST                                                          │
└──────────────────────────────────────────────────────────────────────────────┘

BEFORE EVERY TRADE:
  ☐ Price in target range (1-20¢ or 80-99¢)
  ☐ Move exceeds threshold (>12-25%)
  ☐ Available capital (not at max positions)
  ☐ Below daily loss limit
  ☐ Can execute within 30 seconds
  ☐ Market has liquidity (volume > 0)

ENTRY:
  1. Detect signal (price + move)
  2. Validate entry criteria
  3. Try limit order (60 sec wait)
  4. If not filled, use market order
  5. Set exit timer
  
EXIT:
  • Time-based: Close after hold period
  • Profit target: Exit if reverses >8-15%
  • Stop loss: Exit if continues another 5%

┌──────────────────────────────────────────────────────────────────────────────┐
│ POSITION SIZING                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

Conservative: 0.5-1% per trade, max 3 positions
Moderate:     1-2% per trade, max 5 positions  
Aggressive:   2-5% per trade, max 10 positions

Example ($10,000 bankroll, Moderate):
  • Per trade: $100-200
  • Max risk: $1,000 (5 positions × $200)
  • 20% of bankroll max at risk

┌──────────────────────────────────────────────────────────────────────────────┐
│ RISK MANAGEMENT                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

STOP LOSSES (MANDATORY):
  • Position: Exit if move continues +5%
  • Time: Exit if no reversal by 2x hold period
  • Liquidity: Exit if bid-ask spread >3%

DAILY LIMITS:
  • Max trades: 10-20
  • Max loss: 5% of bankroll
  • Stop trading after 5 losses in a row

DRAWDOWN RULES:
  • -20% bankroll: Cut position size 50%
  • -30% bankroll: STOP TRADING, reassess
  • +50% bankroll: Scale positions up proportionally

┌──────────────────────────────────────────────────────────────────────────────┐
│ EXPECTED RETURNS                                                             │
└──────────────────────────────────────────────────────────────────────────────┘

REALISTIC SCENARIO (500 games/year):
  
  Bankroll    Position    Annual Return
  ────────────────────────────────────────
  $1,000      $10-20      +$12 to +$64
  $5,000      $50-100     +$59 to +$318
  $10,000     $100-200    +$118 to +$637
  $25,000     $250-500    +$295 to +$1,591
  $50,000     $500-1,000  +$590 to +$3,183

ROI: 1-6% on deployed capital (Conservative to Optimistic)
Sharpe Ratio: ~1.2-1.8 (Good risk-adjusted returns)

┌──────────────────────────────────────────────────────────────────────────────┐
│ KEY WARNINGS                                                                 │
└──────────────────────────────────────────────────────────────────────────────┘

⚠ Sample Size: Many strategies have small samples (3-25 trades)
  → Expect 100% win rates to regress to 70-85%
  
⚠ Execution: Extreme prices occur in blowouts, liquidity may be thin
  → Accept 1-2% slippage, skip if spread >3%
  
⚠ Market Adaptation: Edge may erode if others discover it
  → Monitor win rates, be ready to stop if edge disappears
  
⚠ Fee Dependency: Entire edge relies on P×(1-P) formula
  → If Kalshi changes fees, re-evaluate immediately
  
⚠ Timing: Can't catch all opportunities if not monitoring
  → Set automated alerts, accept 30-50% miss rate

┌──────────────────────────────────────────────────────────────────────────────┐
│ QUICK STATS                                                                  │
└──────────────────────────────────────────────────────────────────────────────┘

Total Profitable Strategies:     195
Total Opportunities:             4,637 trades (502 games)
Per Game:                        9.24 trades
Average Net P/L:                 +1.63%
Median Net P/L:                  +1.03%
Best Net P/L:                    +12.93%
Median Win Rate:                 81.8%
Average Fee Paid:                1.14% (vs 2.75% at 50¢)

Best Price Ranges:               1-5¢, 90-99¢ (lowest fees)
Best Move Thresholds:            >20-25% (strongest reversals)
Best Hold Period:                12 minutes (optimal)

┌──────────────────────────────────────────────────────────────────────────────┐
│ FILES & RESOURCES                                                            │
└──────────────────────────────────────────────────────────────────────────────┘

Main Documentation:    COMPLETE_EDGE_CATALOG.md (this document)
All Strategies CSV:    outputs/metrics/all_profitable_edges.csv
Quick Summary:         python FINAL_EDGE_SUMMARY.py
Source Code:           src/analysis/*.py

┌──────────────────────────────────────────────────────────────────────────────┐
│ IMPLEMENTATION STEPS                                                         │
└──────────────────────────────────────────────────────────────────────────────┘

Phase 1: VALIDATION (20-50 games)
  ☐ Paper trade Strategy 1 (high frequency)
  ☐ Log all trades and results
  ☐ Compare actual vs expected win rate
  ☐ Measure execution quality and slippage

Phase 2: SMALL SCALE (50-100 games)  
  ☐ Start with $50-100 positions
  ☐ Deploy Strategies 1-3
  ☐ Build confidence and experience
  ☐ Refine execution process

Phase 3: SCALE UP (100+ games)
  ☐ Increase to target position sizes
  ☐ Deploy full portfolio (5 strategies)
  ☐ Optimize execution and monitoring
  ☐ Track and adjust continuously

╔══════════════════════════════════════════════════════════════════════════════╗
║                           READY TO IMPLEMENT!                                ║
║                                                                              ║
║  START HERE: Price 1-20¢, >12% moves, fade for 3 minutes                   ║
║  Expected: 63% win rate, +0.21% per trade, 0.27 trades/game                ║
║                                                                              ║
║  Scale up once validated!                                                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

Generated: December 28, 2025
Data: 502 games, 680,017 observations
Version: 1.0
""")

