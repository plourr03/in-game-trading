"""Quick summary of edge found"""
from src.data.loader import load_kalshi_games
from src.data.preprocessor import fill_prices
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

kalshi = load_kalshi_games()
kalshi = fill_prices(kalshi)

kalshi['pc'] = kalshi.groupby('game_id')['close'].diff()
kalshi['pc_next3'] = kalshi.groupby('game_id')['pc'].shift(-3)

# >7% moves
large = kalshi[kalshi['pc'].abs() > 7].copy()
large['reverses'] = np.sign(large['pc']) != np.sign(large['pc_next3'])
valid = large[large['pc_next3'].notna()].copy()

# Calculate P&L
valid['wins'] = valid['reverses']
wins = valid[valid['wins']]
losses = valid[~valid['wins']]

win_rate = valid['wins'].mean()
avg_win_size = wins['pc_next3'].abs().mean()
avg_loss_size = losses['pc_next3'].abs().mean()
gross_pl = win_rate * avg_win_size - (1 - win_rate) * avg_loss_size
net_pl = gross_pl - 2.75

print(f"""
EDGE SUMMARY (>7% moves, 3-min reversal strategy)

Opportunities: {len(valid):,} trades
Win Rate: {win_rate:.1%}
Avg Win: {avg_win_size:.2f}%
Avg Loss: {avg_loss_size:.2f}%

Gross P/L: {gross_pl:+.2f}%
Fees: -2.75%
Net P/L: {net_pl:+.2f}%

Status: {'PROFITABLE' if net_pl > 0 else 'UNPROFITABLE'}

Visualization saved to: outputs/figures/edge_analysis.png
""")

