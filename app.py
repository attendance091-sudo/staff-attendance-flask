from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
import sqlite3
from datetime import date, datetime
import qrcode
from io import BytesIO
from math import radians, cos, sin, asin, sqrt
from flask import Flask, request, jsonify, render_template


def haversine(lat1, lon1, lat2, lon2):
    # Calculate distance between two lat/lng points in meters
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    r = 6371000  # Earth radius in meters
    return c * r

OFFICE_LAT = 40.7128   # Replace with your office latitude
OFFICE_LNG = -74.0060  # Replace with your office longitude
MAX_DISTANCE_METERS = 100  # Maximum allowed distance in meters

app = Flask(__name__)  # <-- THIS LINE MUST BE HERE BEFORE ROUTES

@app.route('/check_in', methods=['POST'])
def check_in():
    data = request.get_json()
    qr_data = data.get('qr_data')
    lat = data.get('lat')
    lng = data.get('lng')

    if qr_data is None or lat is None or lng is None:
        return jsonify({"message": "Missing QR data or GPS coordinates."}), 400

    # Validate distance
    distance = haversine(float(lat), float(lng), OFFICE_LAT, OFFICE_LNG)
    if distance > MAX_DISTANCE_METERS:
        return jsonify({"message": "You are too far from the office to check in."}), 400

    # TODO: Your actual attendance marking logic here

    return jsonify({"message": f"Check-in successful for {qr_data}!"})


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Replace with a real secret key

DATABASE = 'staff.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def get_db():
    return get_db_connection()

def alter_staff_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE staff ADD COLUMN start_time TEXT")
    except sqlite3.OperationalError:
        print("start_time column already exists.")
    try:
        cursor.execute("ALTER TABLE staff ADD COLUMN end_time TEXT")
    except sqlite3.OperationalError:
        print("end_time column already exists.")
    conn.commit()
    conn.close()

def migrate_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='attendance'")
    if not cursor.fetchone():
        print("Table 'attendance' does not exist. Please create it first.")
        conn.close()
        return

    cursor.execute("PRAGMA table_info(attendance)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'late' not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN late TEXT DEFAULT NULL")
        print("Added 'late' column to attendance table.")

    if 'overtime' not in columns:
        cursor.execute("ALTER TABLE attendance ADD COLUMN overtime TEXT DEFAULT NULL")
        print("Added 'overtime' column to attendance table.")

    conn.commit()
    conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Create staff table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            active INTEGER DEFAULT 1
        )
    ''')

    # Create attendance table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date TEXT,
            status TEXT,
            check_in_time TEXT,
            check_out_time TEXT,
            late TEXT,
            overtime TEXT,
            FOREIGN KEY (user_id) REFERENCES staff(id)
        )
    ''')

    conn.commit()
    conn.close()
    print("✅ Database initialized.")

# Alter staff table on startup
alter_staff_table()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add_staff', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        name = request.form.get('name')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')

        if not name:
            flash('Staff name is required.', 'danger')
            return redirect(url_for('add_staff'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO staff (name, start_time, end_time) VALUES (?, ?, ?)", (name, start_time, end_time))
        conn.commit()
        conn.close()

        flash(f"Staff '{name}' added successfully.", 'success')
        return redirect(url_for('add_staff'))

    return render_template('add_staff.html')

@app.route('/attendance')
def attendance():
    today = date.today().strftime("%Y-%m-%d")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM staff ORDER BY name")
    staff = cursor.fetchall()

    staff_status = {}
    for s in staff:
        cursor.execute('''
            SELECT check_in_time, check_out_time
            FROM attendance
            WHERE user_id = ? AND date = ?
            ORDER BY id DESC LIMIT 1
        ''', (s['id'], today))
        row = cursor.fetchone()
        if row:
            staff_status[s['id']] = (row['check_in_time'], row['check_out_time'])
        else:
            staff_status[s['id']] = (None, None)

    conn.close()
    return render_template('attendance.html', staff=staff, staff_status=staff_status, today=today)

@app.route('/check/<int:user_id>/<string:action>', methods=['POST'])
def check(user_id, action):
    if action not in ['in', 'out']:
        flash("Invalid action.", "danger")
        return redirect(url_for('attendance'))

    today = date.today().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (user_id, today))
    record = cursor.fetchone()

    if action == 'in':
        cursor.execute("SELECT start_time FROM staff WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        late_duration = None
        if result and result['start_time']:
            scheduled_start = datetime.strptime(result['start_time'], "%H:%M")
            actual_in = datetime.strptime(now, "%H:%M:%S")
            if actual_in > scheduled_start:
                late_duration = str(actual_in - scheduled_start)

        if record and record['check_in_time']:
            flash("Already checked in today.", "warning")
        else:
            if record:
                cursor.execute(
                    "UPDATE attendance SET check_in_time = ?, late = ?, status = 'Present' WHERE id = ?",
                    (now, late_duration, record['id'])
                )
            else:
                cursor.execute(
                    "INSERT INTO attendance (user_id, date, check_in_time, status, late) VALUES (?, ?, ?, 'Present', ?)",
                    (user_id, today, now, late_duration)
                )
            conn.commit()
            flash("Checked in successfully.", "success")

    elif action == 'out':
        if not record or not record['check_in_time']:
            flash("You must check in first before checking out.", "warning")
        elif record['check_out_time']:
            flash("Already checked out today.", "warning")
        else:
            cursor.execute("SELECT end_time FROM staff WHERE id = ?", (user_id,))
            result = cursor.fetchone()
            overtime_duration = None
            if result and result['end_time']:
                scheduled_end = datetime.strptime(result['end_time'], "%H:%M")
                actual_out = datetime.strptime(now, "%H:%M:%S")
                if actual_out > scheduled_end:
                    overtime_duration = str(actual_out - scheduled_end)

            cursor.execute(
                "UPDATE attendance SET check_out_time = ?, overtime = ? WHERE id = ?",
                (now, overtime_duration, record['id'])
            )
            conn.commit()
            flash("Checked out successfully.", "success")

    conn.close()
    return redirect(url_for('attendance'))

@app.route('/view_attendance')
def view_attendance():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.name, a.date, a.status, a.check_in_time, a.check_out_time, a.late, a.overtime
        FROM attendance a
        JOIN staff u ON a.user_id = u.id
        ORDER BY a.date DESC, u.name
    ''')
    records = cursor.fetchall()
    conn.close()
    return render_template('view_attendance.html', records=records)

@app.route('/mark_attendance', methods=['GET', 'POST'])
def mark_attendance():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name FROM staff ORDER BY name")
    staff = cursor.fetchall()

    if request.method == 'POST':
        today = date.today().strftime("%Y-%m-%d")
        for s in staff:
            status = request.form.get(str(s['id']))
            if status:
                cursor.execute("SELECT id FROM attendance WHERE user_id = ? AND date = ?", (s['id'], today))
                record = cursor.fetchone()
                if record:
                    cursor.execute("UPDATE attendance SET status = ? WHERE id = ?", (status, record['id']))
                else:
                    cursor.execute("INSERT INTO attendance (user_id, date, status) VALUES (?, ?, ?)", (s['id'], today, status))
        conn.commit()
        flash("Attendance marked successfully.", "success")
        return redirect(url_for('mark_attendance'))

    return render_template('mark_attendance.html', staff=staff)

@app.route('/qr_check/<int:staff_id>/<string:action>', methods=['GET'])
def qr_check(staff_id, action):
    if action not in ['in', 'out']:
        flash("Invalid QR code action.", "danger")
        return redirect(url_for('attendance'))

    today = date.today().strftime("%Y-%m-%d")
    now = datetime.now().strftime("%H:%M:%S")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance WHERE user_id = ? AND date = ?", (staff_id, today))
    record = cursor.fetchone()

    if action == 'in':
        if record and record['check_in_time']:
            flash("Already checked in today.", "warning")
        else:
            if record:
                cursor.execute("UPDATE attendance SET check_in_time = ?, status = 'Present' WHERE id = ?", (now, record['id']))
            else:
                cursor.execute("INSERT INTO attendance (user_id, date, check_in_time, status) VALUES (?, ?, ?, 'Present')",
                               (staff_id, today, now))
            conn.commit()
            flash("Checked in successfully via QR code.", "success")

    elif action == 'out':
        if not record or not record['check_in_time']:
            flash("You must check in first before checking out.", "warning")
        elif record['check_out_time']:
            flash("Already checked out today.", "warning")
        else:
            cursor.execute("UPDATE attendance SET check_out_time = ? WHERE id = ?", (now, record['id']))
            conn.commit()
            flash("Checked out successfully via QR code.", "success")

    conn.close()
    return redirect(url_for('attendance'))

@app.route('/generate_qr/<int:staff_id>/<string:action>')
def generate_qr(staff_id, action):
    if action not in ['in', 'out']:
        return "Invalid action", 400
    url = url_for('qr_check', staff_id=staff_id, action=action, _external=True)
    qr_img = qrcode.make(url)
    img_io = BytesIO()
    qr_img.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/staff_qr')
def staff_qr():  
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM staff WHERE active = 1 ORDER BY name")  # Use WHERE active=1 if needed
    staff_list = cursor.fetchall()
    conn.close()

    return render_template('staff_qr.html', staff_list=staff_list)

def migrate_staff_table():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if 'active' column already exists
    cursor.execute("PRAGMA table_info(staff)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'active' not in columns:
        cursor.execute("ALTER TABLE staff ADD COLUMN active INTEGER DEFAULT 1")
        print("✅ Added 'active' column to staff table.")
    else:
        print("ℹ️ 'active' column already exists in staff table.")

    conn.commit()
    conn.close()

@app.route('/manage_staff')
def manage_staff():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, active FROM staff ORDER BY name")
    staff_list = cursor.fetchall()
    conn.close()
    return render_template('manage_staff.html', staff_list=staff_list)



@app.route('/manage_staff_filtered')
def manage_staff_filtered():
    ...
    filter_status = request.args.get('status', 'all')

    conn = sqlite3.connect('your_database.db')  # Update this path if needed
    cursor = conn.cursor()

    if filter_status == 'active':
        cursor.execute("SELECT id, name, active FROM staff WHERE active = 1 ORDER BY name")
    elif filter_status == 'inactive':
        cursor.execute("SELECT id, name, active FROM staff WHERE active = 0 ORDER BY name")
    else:
        cursor.execute("SELECT id, name, active FROM staff ORDER BY name")

    staff_list = [
        {"id": row[0], "name": row[1], "active": row[2]}
        for row in cursor.fetchall()
    ]
    conn.close()

    return render_template('manage_staff.html', staff_list=staff_list, filter_status=filter_status)



@app.route('/toggle_staff/<int:staff_id>', methods=['POST'])
def toggle_staff(staff_id):
    conn = get_db()
    cursor = conn.cursor()

    # Get current status
    cursor.execute("SELECT active FROM staff WHERE id = ?", (staff_id,))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row['active'] else 1
        cursor.execute("UPDATE staff SET active = ? WHERE id = ?", (new_status, staff_id))
        conn.commit()
        flash("Staff status updated.", "success")
    conn.close()
    return redirect(url_for('manage_staff'))

# ❌ Removed the duplicate conflicting route below
# @app.route("/check/<staff_id>/<action>", methods=["POST"])
# def check(staff_id, action):
#     ...
# It was causing a Flask AssertionError due to overwriting the existing `check` route.

if __name__ == "__main__":
    init_db()                  # Initialize DB
    migrate_db()               # Add late/overtime columns if missing
    migrate_staff_table()      # Add active column if missing
    app.run(debug=True)


@app.route("/check/<staff_id>/<action>", methods=["POST"])
def check(staff_id, action):
    # Your logic here
    return "Checked!"

    
app = Flask(__name__)

# Existing routes here
@app.route('/attendance')
def attendance():
    # Your code
    return render_template('attendance.html')

# Your new check_in route
@app.route('/check_in', methods=['POST'])
def check_in():
    data = request.get_json()
    qr_code = data.get('qr_code')
    # TODO: Validate and update attendance here
    return jsonify({'message': f'Checked in user with QR: {qr_code}'})

# Your new check_out route
@app.route('/check_out', methods=['POST'])
def check_out():
    data = request.get_json()
    qr_code = data.get('qr_code')
    # TODO: Validate and update attendance here
    return jsonify({'message': f'Checked out user with QR: {qr_code}'})





if __name__ == "__main__":
    init_db()        # If you use this
    migrate_db()     # Your existing attendance migration
    migrate_staff_table()  # ✅ Add this line
    app.run(debug=True)

