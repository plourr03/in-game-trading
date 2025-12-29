import psycopg2
import yaml
import pandas as pd

config = yaml.safe_load(open('config.yaml'))
db = config['database']
conn = psycopg2.connect(
    host=db['host'],
    port=db['port'],
    database=db['database'],
    user=db['user'],
    password=db['password']
)

# Check for games from Dec 22-28
query = """
    SELECT DISTINCT game_id
    FROM nba.nba_play_by_play
    WHERE game_id >= '0022500400'
    ORDER BY game_id DESC
    LIMIT 20
"""

df = pd.read_sql(query, conn)
print(f"Most recent games in database:")
print(df)

# Get date range
query2 = """
    SELECT 
        MIN(game_id) as oldest,
        MAX(game_id) as newest,
        COUNT(DISTINCT game_id) as total
    FROM nba.nba_play_by_play
"""

df2 = pd.read_sql(query2, conn)
print(f"\nDatabase stats:")
print(df2)

conn.close()

