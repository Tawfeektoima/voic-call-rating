"""
VoiceQA System Health Sync — Database Migration
=================================================
Adds missing columns to the SQLite database that were defined
in models.py but never applied via ALTER TABLE.

Run: python migrate_db.py
"""
import sqlite3
import os

db_path = 'call_rating.db'

if not os.path.exists(db_path):
    print(f"Database {db_path} not found. SQLAlchemy will create it on first run.")
    exit(0)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def get_columns(table):
    cursor.execute(f"PRAGMA table_info({table});")
    return [col[1] for col in cursor.fetchall()]

def table_exists(table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?;", (table,))
    return cursor.fetchone() is not None

def add_column(table, col_name, col_type, default=None):
    cols = get_columns(table)
    if col_name not in cols:
        default_clause = f" DEFAULT {default}" if default is not None else ""
        sql = f"ALTER TABLE {table} ADD COLUMN {col_name} {col_type}{default_clause};"
        cursor.execute(sql)
        print(f"  + {table}.{col_name} ({col_type})")
        return True
    return False

changes = 0
print("=" * 50)
print("  VoiceQA Database Migration")
print("=" * 50)

# ── Table: calls ──
if table_exists("calls"):
    print("\n[calls]")
    changes += add_column("calls", "source",                "VARCHAR(50)",    "'uploaded'")
    changes += add_column("calls", "overridden_score",      "FLOAT",          None)
    changes += add_column("calls", "reviewer_notes",        "TEXT",           None)
    changes += add_column("calls", "reviewed_at",           "DATETIME",       None)
    changes += add_column("calls", "call_datetime",         "DATETIME",       None)
    changes += add_column("calls", "call_hour",             "INTEGER",        None)
    changes += add_column("calls", "call_day_of_week",      "VARCHAR(20)",    None)
    changes += add_column("calls", "calls_before_this",     "INTEGER",        None)
    changes += add_column("calls", "filler_words_count",    "INTEGER",        "0")
    changes += add_column("calls", "interruptions_count",   "INTEGER",        "0")
    changes += add_column("calls", "avg_response_time_sec", "FLOAT",          None)
    changes += add_column("calls", "opening_ok",            "BOOLEAN",        "0")
    changes += add_column("calls", "closing_ok",            "BOOLEAN",        "0")
    changes += add_column("calls", "dob_verified",          "BOOLEAN",        "0")
    changes += add_column("calls", "de_escalation_success", "BOOLEAN",        "0")
    changes += add_column("calls", "sales_eval_data",       "JSON",           None)
else:
    print("\n[calls] Table does not exist yet (will be created by SQLAlchemy).")

# ── Table: live_sessions ──
if table_exists("live_sessions"):
    print("\n[live_sessions]")
    changes += add_column("live_sessions", "gpu_id",           "INTEGER",      "0")
    changes += add_column("live_sessions", "agent_audio_path", "VARCHAR(500)", None)
else:
    print("\n[live_sessions] Table does not exist yet (will be created by SQLAlchemy).")

# ── Table: golden_pair_candidates ──
if table_exists("golden_pair_candidates"):
    print("\n[golden_pair_candidates] Already exists.")
else:
    print("\n[golden_pair_candidates] Table does not exist yet (will be created by SQLAlchemy).")

# ── Table: employees ──
if table_exists("employees"):
    print("\n[employees]")
    changes += add_column("employees", "tier",               "VARCHAR(20)",    "'bronze'")
    changes += add_column("employees", "skills",             "JSON",           None)
    changes += add_column("employees", "phone_number",       "VARCHAR(50)",    None)
    changes += add_column("employees", "emotion_history",    "JSON",           None)
    changes += add_column("employees", "agent_tenure_days",  "INTEGER",        None)

conn.commit()
conn.close()

print(f"\n{'=' * 50}")
if changes:
    print(f"  Done. {changes} column(s) added.")
else:
    print("  Database is already up to date.")
print(f"{'=' * 50}")
