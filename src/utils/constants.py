"""Constants for Kalshi NBA trading analysis"""

# Kalshi fee structure
KALSHI_TAKER_FEE_RATE = 0.07  # 7% of max risk
KALSHI_MAKER_FEE_RATE = 0.0175  # 1.75% of max risk for NBA markets

# NBA game constants
MINUTES_PER_PERIOD = 12
PERIODS_IN_REGULATION = 4
TOTAL_REGULATION_MINUTES = MINUTES_PER_PERIOD * PERIODS_IN_REGULATION

# Overtime
OVERTIME_MINUTES = 5

# Data quality thresholds
MIN_VOLUME_COVERAGE = 0.3  # At least 30% of minutes should have volume
MAX_MISSING_PRICE_PCT = 0.5  # No more than 50% missing prices

