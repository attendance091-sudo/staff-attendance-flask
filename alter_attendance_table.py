import sqlite3


conn = sqlite3.connect('staff.db')
cursor = conn.cursor()

# Check if columns already exist
try:
    cursor.execute("ALTER TABLE attendance ADD COLUMN check_in_time TEXT")
except sqlite3.OperationalError as e:
    print("check_in_time column might already exist:", e)

try:
    cursor.execute("ALTER TABLE attendance ADD COLUMN check_out_time TEXT")
except sqlite3.OperationalError as e:
    print("check_out_time column might already exist:", e)

conn.commit()
conn.close()
print("Columns updated if missing.")
