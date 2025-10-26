import sqlite3

conn = sqlite3.connect('/app/data/portfolio.db')
cursor = conn.cursor()

# Get all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()

print("Tables in database:")
for table in tables:
    table_name = table[0]
    print(f"  {table_name}")
    
    # Get columns for each table
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for col in columns:
        col_name, col_type = col[1], col[2]
        print(f"    - {col_name}: {col_type}")

# Get migration history
cursor.execute("SELECT * FROM alembic_version")
versions = cursor.fetchall()
print("\nAlembic migrations applied:")
for v in versions:
    print(f"  - {v[0]}")

conn.close()
