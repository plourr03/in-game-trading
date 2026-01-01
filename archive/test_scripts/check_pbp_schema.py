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
    SELECT column_name, data_type, character_maximum_length, numeric_precision
    FROM information_schema.columns 
    WHERE table_schema='nba' AND table_name='nba_play_by_play'
    ORDER BY ordinal_position
""")

print("PBP Table Schema:")
print(f"{'Column':<20} {'Type':<20} {'Details':<20}")
print("="*60)
for row in cur.fetchall():
    col, dtype, char_len, num_prec = row
    details = f"len={char_len}" if char_len else (f"prec={num_prec}" if num_prec else "")
    print(f"{col:<20} {dtype:<20} {details:<20}")

conn.close()


