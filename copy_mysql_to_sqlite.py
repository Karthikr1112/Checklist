"""
Standalone script to copy all tables and data from a MySQL database into a local SQLite database.

Usage:
    python copy_mysql_to_sqlite.py
    python copy_mysql_to_sqlite.py --host 192.168.229.10 --user root --password mypass --db checklist_db
"""

import argparse
import datetime
from decimal import Decimal
import os
from pathlib import Path
import sqlite3
import sys

try:
    import pymysql
    import pymysql.cursors
except ImportError:
    print("Error: 'pymysql' package is required. Install it using:")
    print("    pip install pymysql")
    sys.exit(1)


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_SQLITE_PATH = BASE_DIR / "db.sqlite3"


def map_mysql_type_to_sqlite(data_type: str) -> str:
    """Map common MySQL column types to SQLite column types."""
    dt = data_type.lower()
    if any(k in dt for k in ("int", "bit")):
        return "INTEGER"
    if any(k in dt for k in ("float", "double", "decimal", "numeric")):
        return "REAL"
    if any(k in dt for k in ("blob", "binary")):
        return "BLOB"
    # varchar, char, text, enum, json, datetime, date, timestamp, etc.
    return "TEXT"


def sanitize_val(val):
    """Sanitize Python types to SQLite-friendly values."""
    if val is None:
        return None
    if isinstance(val, (datetime.datetime, datetime.date, datetime.time)):
        return val.isoformat()
    if isinstance(val, datetime.timedelta):
        total_seconds = int(val.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    if isinstance(val, Decimal):
        return str(val)
    if isinstance(val, bytes):
        try:
            return val.decode("utf-8")
        except UnicodeDecodeError:
            return val
    return val


def get_sqlite_tables(sqlite_cur):
    """Retrieve existing table names in SQLite."""
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    return {row[0] for row in sqlite_cur.fetchall()}


def get_sqlite_table_columns(sqlite_cur, table_name: str):
    """Retrieve column names for an existing SQLite table."""
    sqlite_cur.execute(f"PRAGMA table_info(`{table_name}`);")
    return [row[1] for row in sqlite_cur.fetchall()]


def create_sqlite_table_from_mysql(sqlite_cur, mysql_cur, table_name: str):
    """Create a table in SQLite matching MySQL schema if it doesn't already exist."""
    mysql_cur.execute(f"DESCRIBE `{table_name}`;")
    cols_meta = mysql_cur.fetchall()
    
    col_defs = []
    pks = []
    for col in cols_meta:
        field = col[0]
        col_type = col[1]
        null_allowed = col[2]
        key = col[3]
        
        sqlite_type = map_mysql_type_to_sqlite(col_type)
        null_clause = "" if null_allowed == "YES" else " NOT NULL"
        col_defs.append(f"`{field}` {sqlite_type}{null_clause}")
        
        if key == "PRI":
            pks.append(f"`{field}`")
            
    pk_clause = f", PRIMARY KEY ({', '.join(pks)})" if pks else ""
    create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` ({', '.join(col_defs)}{pk_clause});"
    sqlite_cur.execute(create_sql)


def copy_table_data(mysql_cur, sqlite_conn, sqlite_cur, table_name: str, batch_size: int = 1000) -> int:
    """Copy all rows from MySQL table to SQLite table."""
    # Check if table exists in SQLite, if not create it
    sqlite_tables = get_sqlite_tables(sqlite_cur)
    if table_name not in sqlite_tables:
        create_sqlite_table_from_mysql(sqlite_cur, mysql_cur, table_name)
    
    # Get column intersection between MySQL and SQLite
    mysql_cur.execute(f"DESCRIBE `{table_name}`;")
    mysql_cols = [c[0] for c in mysql_cur.fetchall()]
    
    sqlite_cols = get_sqlite_table_columns(sqlite_cur, table_name)
    common_cols = [c for c in mysql_cols if c in sqlite_cols]
    
    if not common_cols:
        print(f"  [!] Skipping {table_name}: No matching columns found.")
        return 0

    cols_str = ", ".join([f"`{c}`" for c in common_cols])
    placeholders = ", ".join(["?"] * len(common_cols))
    insert_sql = f"INSERT OR REPLACE INTO `{table_name}` ({cols_str}) VALUES ({placeholders})"

    # Clear existing data in SQLite for this table
    sqlite_cur.execute(f"DELETE FROM `{table_name}`;")

    # Fetch rows from MySQL
    mysql_cur.execute(f"SELECT {cols_str} FROM `{table_name}`;")
    total_copied = 0

    while True:
        rows = mysql_cur.fetchmany(batch_size)
        if not rows:
            break
        
        sanitized_rows = [
            tuple(sanitize_val(v) for v in row)
            for row in rows
        ]
        sqlite_cur.executemany(insert_sql, sanitized_rows)
        total_copied += len(sanitized_rows)

    sqlite_conn.commit()
    return total_copied


def main():
    parser = argparse.ArgumentParser(description="Copy full data from MySQL database into SQLite.")
    parser.add_argument("--host", default=os.getenv("DB_HOST", "192.168.229"), help="MySQL Host (default: 192.168.229)")
    parser.add_argument("--port", type=int, default=int(os.getenv("DB_PORT", "3306")), help="MySQL Port (default: 3306)")
    parser.add_argument("--user", default=os.getenv("DB_USER", "checklist_user"), help="MySQL User (default: checklist_user)")
    parser.add_argument("--password", default=os.getenv("DB_PASSWORD", ""), help="MySQL Password")
    parser.add_argument("--db", default=os.getenv("DB_NAME", "checklist_db"), help="MySQL Database Name (default: checklist_db)")
    parser.add_argument("--sqlite", default=str(DEFAULT_SQLITE_PATH), help=f"Target SQLite file (default: {DEFAULT_SQLITE_PATH})")
    parser.add_argument("--batch-size", type=int, default=1000, help="Row batch size (default: 1000)")
    parser.add_argument("--tables", default="", help="Optional comma-separated list of tables to copy")

    args = parser.parse_args()

    print("==================================================")
    print("  MySQL to SQLite Database Copy Utility")
    print("==================================================")
    print(f" Source MySQL : {args.user}@{args.host}:{args.port}/{args.db}")
    print(f" Target SQLite: {args.sqlite}")
    print("--------------------------------------------------")

    # 1. Connect to MySQL
    try:
        mysql_conn = pymysql.connect(
            host=args.host,
            port=args.port,
            user=args.user,
            password=args.password,
            database=args.db,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.Cursor,
            connect_timeout=10,
        )
        print(" Connected to MySQL successfully.")
    except Exception as e:
        print(f"\n[ERROR] Failed to connect to MySQL database: {e}")
        print("\nPlease verify:")
        print("  1. The host IP address and port are reachable.")
        print(f"     (Currently: {args.host}:{args.port})")
        print("  2. The username and password are correct.")
        print(f"     (Currently user: '{args.user}')")
        print("  3. The MySQL server is running and accepts remote connections.")
        print("\nYou can pass custom connection values like this:")
        print("    python copy_mysql_to_sqlite.py --host <IP_OR_HOST> --user <USER> --password <PASSWORD> --db <DB_NAME>")
        sys.exit(1)

    # 2. Connect to SQLite
    sqlite_conn = sqlite3.connect(args.sqlite)
    sqlite_cur = sqlite_conn.cursor()

    # Disable SQLite foreign key checks and sync during bulk copy
    sqlite_cur.execute("PRAGMA foreign_keys = OFF;")
    sqlite_cur.execute("PRAGMA synchronous = OFF;")

    try:
        with mysql_conn.cursor() as mysql_cur:
            # 3. Get tables
            mysql_cur.execute("SHOW TABLES;")
            all_tables = [row[0] for row in mysql_cur.fetchall()]

            if args.tables:
                selected_tables = [t.strip() for t in args.tables.split(",") if t.strip()]
                tables_to_copy = [t for t in all_tables if t in selected_tables]
            else:
                tables_to_copy = all_tables

            print(f" Found {len(tables_to_copy)} table(s) to copy.")
            print("--------------------------------------------------")

            total_rows_copied = 0
            for i, table in enumerate(tables_to_copy, 1):
                try:
                    count = copy_table_data(mysql_cur, sqlite_conn, sqlite_cur, table, batch_size=args.batch_size)
                    print(f" [{i:02d}/{len(tables_to_copy):02d}] {table:<35} : {count:>6} rows copied")
                    total_rows_copied += count
                except Exception as table_err:
                    print(f" [{i:02d}/{len(tables_to_copy):02d}] {table:<35} : ERROR ({table_err})")

            # Re-enable foreign key constraints
            sqlite_cur.execute("PRAGMA foreign_keys = ON;")
            sqlite_cur.execute("PRAGMA synchronous = NORMAL;")
            sqlite_conn.commit()

            print("==================================================")
            print(f" SUCCESS: Copied {total_rows_copied} rows across {len(tables_to_copy)} tables into SQLite!")
            print(f" SQLite file saved at: {args.sqlite}")
            print("==================================================")

    finally:
        mysql_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
