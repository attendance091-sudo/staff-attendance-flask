import sqlite3
from datetime import date
import sqlite3


conn = sqlite3.connect('staff.db')
cursor = conn.cursor()

# Add missing columns
cursor.execute("ALTER TABLE attendance ADD COLUMN check_in_time TEXT")
cursor.execute("ALTER TABLE attendance ADD COLUMN check_out_time TEXT")

conn.commit()
conn.close()

# Connect to SQLite DB (or create it)
conn = sqlite3.connect('staff_attendance.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    staff_id INTEGER,
    date TEXT,
    status TEXT,
    FOREIGN KEY (staff_id) REFERENCES staff (id)
)
''')
conn.commit()

# Functions
def add_staff(name):
    cursor.execute("INSERT INTO staff (name) VALUES (?)", (name,))
    conn.commit()
    print(f"✅ Staff '{name}' added.")

def mark_attendance():
    today = str(date.today())
    cursor.execute("SELECT * FROM staff")
    staff_list = cursor.fetchall()

    for staff in staff_list:
        print(f"\nMark attendance for {staff[1]} (ID: {staff[0]})")
        status = input("Enter P for Present, A for Absent: ").upper()
        status = "Present" if status == "P" else "Absent"
        cursor.execute("INSERT INTO attendance (staff_id, date, status) VALUES (?, ?, ?)",
                       (staff[0], today, status))
    conn.commit()
    print("✅ Attendance marked for today.")

def view_attendance():
    cursor.execute('''
    SELECT s.name, a.date, a.status
    FROM attendance a
    JOIN staff s ON a.staff_id = s.id
    ORDER BY a.date DESC
    ''')
    records = cursor.fetchall()
    print("\n📋 Attendance Records:")
    for row in records:
        print(f"{row[0]} - {row[1]} - {row[2]}")

# Menu
def menu():
    while True:
        print("\n=== Staff Attendance System ===")
        print("1. Add Staff")
        print("2. Mark Attendance")
        print("3. View Attendance")
        print("4. Exit")
        choice = input("Enter choice: ")

        if choice == '1':
            name = input("Enter staff name: ")
            add_staff(name)
        elif choice == '2':
            mark_attendance()
        elif choice == '3':
            view_attendance()
        elif choice == '4':
            print("👋 Exiting...")
            break
        else:
            print("❌ Invalid choice. Try again.")

menu()
conn.close()
