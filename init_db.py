import sqlite3
from flask_bcrypt import generate_password_hash

def init_db():
    conn = sqlite3.connect('staff.db')
    cursor = conn.cursor()

    # Create users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'staff'))
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            check_in_time TEXT,
            check_out_time TEXT,
            status TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    # Insert an admin user (password: admin123)
    try:
        hashed_pw = generate_password_hash('admin123').decode('utf-8')
        cursor.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                       ('admin', hashed_pw, 'admin'))
    except sqlite3.IntegrityError:
        pass  # User exists already

    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Database initialized.")
