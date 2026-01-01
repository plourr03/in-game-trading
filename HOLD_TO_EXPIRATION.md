# Hold-to-Expiration Optimization

## Problem
When a position has a very high probability of winning (price ≥ $95) in late game scenarios, it's more profitable to hold the contract until game end rather than selling early.

**Why?**
- Selling at $99 requires paying **exit fees** (~$3.50 per 500 contracts)
- Holding to expiration means the contract pays out at $1.00 automatically
- Kalshi does **not charge exit fees** for contracts that expire

## Example from Session 5

**What happened (sold at $99):**
- Entry: $50 → Exit: $99
- Gross: $245
- Entry fee: $3.50
- **Exit fee: $3.50**
- Net: $238.00

**What should happen (hold to $1.00):**
- Entry: $50 → Expiration: $100
- Gross: $250
- Entry fee: $3.50
- **Exit fee: $0** (no fee at expiration!)
- Net: $246.50
- **Extra profit: $8.50 per trade**

## New Rule Implemented

**Hold to expiration if ALL these conditions are true:**

1. **Q4 with ≤ 6 minutes remaining** (or ≤ 3 minutes total game time)
2. **Price ≥ $95** (outcome nearly certain)
3. **Score differential ≥ 11 points** (big lead)

## What You'll See

**When holding:**
```
[HOLD] Holding to expiration (Q4, price=$99c, diff=23)
```

**When game ends:**
```
[GAME ENDED] - Settling 3 position(s) at expiration
[EXPIRATION] Settled at $1.00 -> P/L: $+246.50 (saved exit fees!)
```

**In final summary:**
```
Hold-to-Expiration:
  Positions held: 5
  Exit fees saved: ~$17.50
```

## Expected Impact

Based on Session 5:
- **5 trades** could have been held to expiration (trades 3-7)
- **Extra profit: ~$40-50** per session
- **Win rate unchanged** (already winning trades)
- **Reduces risk** (no need to time the exit perfectly)

## When It Activates

This optimization kicks in when:
- Late Q4 blowouts (team up 11+)
- Price already at $95+
- Your model already predicted correctly

**It's a pure optimization - you're already winning, just maximizing the profit!** 🚀

