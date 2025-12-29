import psycopg2
import yaml

config = yaml.safe_load(open('config.yaml'))
db = config['database']
conn = psycopg2.connect(
    host=db['host'],
    port=db['port'],
    database=db['database'],
    user=db['user'],
    password=db['password']
)

cur = conn.cursor()
cur.execute("""
    SELECT column_name 
    FROM information_schema.columns 
    WHERE table_schema='nba' AND table_name='nba_play_by_play' 
    ORDER BY ordinal_position
    LIMIT 30
""")

print("PBP Table Columns:")
for row in cur.fetchall():
    print(f"  - {row[0]}")

conn.close()

