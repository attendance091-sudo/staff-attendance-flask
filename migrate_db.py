import sqlite3

DATABASE = 'staff.db'

def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns

def migrate():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if attendance table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
    if not cursor.fetchone():
        print("Table 'attendance' does not exist. Please create it first.")
        conn.close()
        return

    # Add 'late' column if missing
    if not column_exists(cursor, 'attendance', 'late'):
        cursor.execute("ALTER TABLE attendance ADD COLUMN late INTEGER DEFAULT 0")
        print("Added 'late' column to attendance table.")

    # Add 'overtime' column if missing
    if not column_exists(cursor, 'attendance', 'overtime'):
        cursor.execute("ALTER TABLE attendance ADD COLUMN overtime INTEGER DEFAULT 0")
        print("Added 'overtime' column to attendance table.")

    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
