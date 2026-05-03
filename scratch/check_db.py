import sqlite3

def check_columns():
    conn = sqlite3.connect("call_rating.db")
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(campaigns)")
    columns = cursor.fetchall()
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_columns()
