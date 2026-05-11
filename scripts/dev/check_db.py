import sqlite3
try:
    conn = sqlite3.connect('call_rating.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(live_sessions);")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()
except Exception as e:
    print(f"Error: {e}")
