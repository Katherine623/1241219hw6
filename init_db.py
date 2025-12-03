import sqlite3

DB_PATH = "data.db"

def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        # Assignment schema: weather
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS weather (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT,
                min_temp REAL,
                max_temp REAL,
                description TEXT
            );
            """
        )
        # Legacy/compat table used by app
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS forecasts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT,
                date TEXT,
                weather TEXT,
                max_temp REAL
            );
            """
        )
        conn.commit()
        print(f"Initialized schema in {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
