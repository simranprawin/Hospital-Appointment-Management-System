from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime

app = Flask(__name__)

app.secret_key = "hospital-appointment-management-secret-key"
DATABASE = "hospital.db"


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_database():

    conn = get_db()
    cursor = conn.cursor()

    # USERS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'patient',
            phone TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # DOCTORS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            qualification TEXT,
            experience INTEGER DEFAULT 0,
            phone TEXT,
            email TEXT,
            available_days TEXT,
            available_time TEXT,
            consultation_fee REAL DEFAULT 0,
            status TEXT DEFAULT 'Active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # APPOINTMENTS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            appointment_date TEXT NOT NULL,
            appointment_time TEXT NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'Pending',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(patient_id) REFERENCES users(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        )
    """)

    # =====================================================
    # CREATE DEFAULT ADMIN
    # =====================================================

    admin = cursor.execute(
        "SELECT id FROM users WHERE email = ?",
        ("admin@hospital.com",)
    ).fetchone()

    if not admin:

        cursor.execute("""
            INSERT INTO users
            (name, email, password, role, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (
            "Hospital Administrator",
            "admin@hospital.com",
            generate_password_hash("admin123"),
            "admin",
            "9876543210"
        ))

    # =====================================================
    # CREATE SAMPLE DOCTORS
    # =====================================================

    doctor_count = cursor.execute(
        "SELECT COUNT(*) FROM doctors"
    ).fetchone()[0]

    if doctor_count == 0:

        doctors = [

            (
                "Dr. Ananya Sharma",
                "Cardiology",
                "MBBS, MD Cardiology",
                12,
                "9876543211",
                "ananya@hospital.com",
                "Monday, Wednesday, Friday",
                "10:00 AM - 2:00 PM",
                800
            ),

            (
                "Dr. Rahul Mehta",
                "Neurology",
                "MBBS, MD Neurology",
                10,
                "9876543212",
                "rahul@hospital.com",
                "Tuesday, Thursday, Saturday",
                "11:00 AM - 3:00 PM",
                900
            ),

            (
                "Dr. Priya Nair",
                "Dermatology",
                "MBBS, MD Dermatology",
                8,
                "9876543213",
                "priya@hospital.com",
                "Monday, Tuesday, Thursday",
                "9:00 AM - 1:00 PM",
                600
            ),

            (
                "Dr. Arjun Patel",
                "Orthopedics",
                "MBBS, MS Orthopedics",
                15,
                "9876543214",
                "arjun@hospital.com",
                "Wednesday, Friday, Saturday",
                "2:00 PM - 6:00 PM",
                750
            ),

            (
                "Dr. Sneha Kapoor",
                "Pediatrics",
                "MBBS, MD Pediatrics",
                9,
                "9876543215",
                "sneha@hospital.com",
                "Monday, Wednesday, Saturday",
                "10:00 AM - 1:00 PM",
                500
            )
        ]

        cursor.executemany("""
            INSERT INTO doctors
            (
                name,
                specialization,
                qualification,
                experience,
                phone,
                email,
                available_days,
                available_time,
                consultation_fee
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, doctors)

    conn.commit()
    conn.close()


# =========================================================
# LOGIN REQUIRED DECORATOR
# =========================================================

def login_required(function):

    @wraps(function)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login to continue.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return function(*args, **kwargs)

    return decorated_function


# =========================================================
# ROLE REQUIRED DECORATOR
# =========================================================

def role_required(role):

    def decorator(function):

        @wraps(function)
        def decorated_function(*args, **kwargs):

            if "user_id" not in session:

                flash(
                    "Please login to continue.",
                    "warning"
                )

                return redirect(
                    url_for("login")
                )

            if session.get("role") != role:

                flash(
                    "You do not have permission to access this page.",
                    "danger"
                )

                return redirect(
                    url_for("index")
                )

            return function(*args, **kwargs)

        return decorated_function

    return decorator


# =========================================================
# HOME
# =========================================================

@app.route("/")
def index():

    conn = get_db()

    doctor_count = conn.execute(
        "SELECT COUNT(*) FROM doctors WHERE status = 'Active'"
    ).fetchone()[0]

    appointment_count = conn.execute(
        "SELECT COUNT(*) FROM appointments"
    ).fetchone()[0]

    patient_count = conn.execute(
        "SELECT COUNT(*) FROM users WHERE role = 'patient'"
    ).fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        doctor_count=doctor_count,
        appointment_count=appointment_count,
        patient_count=patient_count
    )


# =========================================================
# REGISTER
# =========================================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:

            flash(
                "Please fill in all required fields.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return redirect(
                url_for("register")
            )

        conn = get_db()

        existing_user = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if existing_user:

            conn.close()

            flash(
                "An account with this email already exists.",
                "warning"
            )

            return redirect(
                url_for("register")
            )

        conn.execute("""
            INSERT INTO users
            (name, email, password, role, phone)
            VALUES (?, ?, ?, ?, ?)
        """, (
            name,
            email,
            generate_password_hash(password),
            "patient",
            phone
        ))

        conn.commit()
        conn.close()

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "auth/register.html"
    )


# =========================================================
# LOGIN
# =========================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        conn = get_db()

        user = conn.execute("""
            SELECT *
            FROM users
            WHERE email = ?
        """, (email,)).fetchone()

        conn.close()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            flash(
                f"Welcome, {user['name']}!",
                "success"
            )

            if user["role"] == "admin":

                return redirect(
                    url_for("admin_dashboard")
                )

            elif user["role"] == "doctor":

                return redirect(
                    url_for("doctor_dashboard")
                )

            return redirect(
                url_for("patient_dashboard")
            )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "auth/login.html"
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for("index")
    )


# =========================================================
# PATIENT DASHBOARD
# =========================================================

@app.route("/patient/dashboard")
@role_required("patient")
def patient_dashboard():

    patient_id = session["user_id"]

    conn = get_db()

    appointments = conn.execute("""
        SELECT
            appointments.*,
            doctors.name AS doctor_name,
            doctors.specialization,
            doctors.consultation_fee
        FROM appointments

        JOIN doctors
        ON appointments.doctor_id = doctors.id

        WHERE appointments.patient_id = ?

        ORDER BY
            appointments.appointment_date DESC,
            appointments.appointment_time DESC
    """, (patient_id,)).fetchall()

    doctor_count = conn.execute(
        "SELECT COUNT(*) FROM doctors WHERE status = 'Active'"
    ).fetchone()[0]

    upcoming_count = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE patient_id = ?
        AND status IN ('Pending', 'Approved')
        AND appointment_date >= date('now')
    """, (patient_id,)).fetchone()[0]

    conn.close()

    return render_template(
        "patient/dashboard.html",
        appointments=appointments,
        doctor_count=doctor_count,
        upcoming_count=upcoming_count
    )


# =========================================================
# VIEW DOCTORS
# =========================================================

@app.route("/patient/doctors")
@login_required
def doctors():

    specialization = request.args.get(
        "specialization",
        ""
    ).strip()

    search = request.args.get(
        "search",
        ""
    ).strip()

    conn = get_db()

    query = """
        SELECT *
        FROM doctors
        WHERE status = 'Active'
    """

    params = []

    if specialization:

        query += """
            AND specialization = ?
        """

        params.append(
            specialization
        )

    if search:

        query += """
            AND (
                name LIKE ?
                OR specialization LIKE ?
            )
        """

        search_value = f"%{search}%"

        params.extend([
            search_value,
            search_value
        ])

    query += """
        ORDER BY name
    """

    doctors_list = conn.execute(
        query,
        params
    ).fetchall()

    specializations = conn.execute("""
        SELECT DISTINCT specialization
        FROM doctors
        WHERE status = 'Active'
        ORDER BY specialization
    """).fetchall()

    conn.close()

    return render_template(
        "patient/doctors.html",
        doctors=doctors_list,
        specializations=specializations,
        selected_specialization=specialization,
        search=search
    )


# =========================================================
# BOOK APPOINTMENT
# =========================================================

@app.route(
    "/patient/book/<int:doctor_id>",
    methods=["GET", "POST"]
)
@role_required("patient")
def book_appointment(doctor_id):

    conn = get_db()

    doctor = conn.execute("""
        SELECT *
        FROM doctors
        WHERE id = ?
        AND status = 'Active'
    """, (doctor_id,)).fetchone()

    conn.close()

    if not doctor:

        flash(
            "Doctor not found.",
            "danger"
        )

        return redirect(
            url_for("doctors")
        )

    if request.method == "POST":

        appointment_date = request.form.get(
            "appointment_date",
            ""
        )

        appointment_time = request.form.get(
            "appointment_time",
            ""
        )

        reason = request.form.get(
            "reason",
            ""
        ).strip()

        if not appointment_date or not appointment_time:

            flash(
                "Please select an appointment date and time.",
                "danger"
            )

            return redirect(
                url_for(
                    "book_appointment",
                    doctor_id=doctor_id
                )
            )

        try:

            selected_date = datetime.strptime(
                appointment_date,
                "%Y-%m-%d"
            ).date()

            today = datetime.now().date()

            if selected_date < today:

                flash(
                    "Appointment date cannot be in the past.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "book_appointment",
                        doctor_id=doctor_id
                    )
                )

        except ValueError:

            flash(
                "Invalid appointment date.",
                "danger"
            )

            return redirect(
                url_for(
                    "book_appointment",
                    doctor_id=doctor_id
                )
            )

        conn = get_db()

        existing = conn.execute("""
            SELECT id
            FROM appointments
            WHERE doctor_id = ?
            AND appointment_date = ?
            AND appointment_time = ?
            AND status IN ('Pending', 'Approved')
        """, (
            doctor_id,
            appointment_date,
            appointment_time
        )).fetchone()

        if existing:

            conn.close()

            flash(
                "This appointment slot is already booked.",
                "warning"
            )

            return redirect(
                url_for(
                    "book_appointment",
                    doctor_id=doctor_id
                )
            )

        conn.execute("""
            INSERT INTO appointments
            (
                patient_id,
                doctor_id,
                appointment_date,
                appointment_time,
                reason,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            doctor_id,
            appointment_date,
            appointment_time,
            reason,
            "Pending"
        ))

        conn.commit()
        conn.close()

        flash(
            "Appointment booked successfully.",
            "success"
        )

        return redirect(
            url_for("patient_appointments")
        )

    return render_template(
        "patient/book_appointment.html",
        doctor=doctor
    )


# =========================================================
# PATIENT APPOINTMENTS
# =========================================================

@app.route("/patient/appointments")
@role_required("patient")
def patient_appointments():

    conn = get_db()

    appointments = conn.execute("""
        SELECT
            appointments.*,
            doctors.name AS doctor_name,
            doctors.specialization,
            doctors.consultation_fee
        FROM appointments

        JOIN doctors
        ON appointments.doctor_id = doctors.id

        WHERE appointments.patient_id = ?

        ORDER BY
            appointments.appointment_date DESC,
            appointments.appointment_time DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "patient/appointments.html",
        appointments=appointments
    )


# =========================================================
# CANCEL APPOINTMENT
# =========================================================

@app.route(
    "/patient/appointments/<int:appointment_id>/cancel",
    methods=["POST"]
)
@role_required("patient")
def cancel_appointment(appointment_id):

    conn = get_db()

    appointment = conn.execute("""
        SELECT *
        FROM appointments
        WHERE id = ?
        AND patient_id = ?
    """, (
        appointment_id,
        session["user_id"]
    )).fetchone()

    if not appointment:

        conn.close()

        flash(
            "Appointment not found.",
            "danger"
        )

        return redirect(
            url_for("patient_appointments")
        )

    if appointment["status"] not in [
        "Pending",
        "Approved"
    ]:

        conn.close()

        flash(
            "This appointment cannot be cancelled.",
            "warning"
        )

        return redirect(
            url_for("patient_appointments")
        )

    conn.execute("""
        UPDATE appointments
        SET status = 'Cancelled'
        WHERE id = ?
    """, (appointment_id,))

    conn.commit()
    conn.close()

    flash(
        "Appointment cancelled successfully.",
        "success"
    )

    return redirect(
        url_for("patient_appointments")
    )


# =========================================================
# PATIENT HISTORY
# =========================================================

@app.route("/patient/history")
@role_required("patient")
def patient_history():

    conn = get_db()

    appointments = conn.execute("""
        SELECT
            appointments.*,
            doctors.name AS doctor_name,
            doctors.specialization
        FROM appointments

        JOIN doctors
        ON appointments.doctor_id = doctors.id

        WHERE appointments.patient_id = ?

        ORDER BY appointments.created_at DESC
    """, (
        session["user_id"],
    )).fetchall()

    conn.close()

    return render_template(
        "patient/history.html",
        appointments=appointments
    )


# =========================================================
# DOCTOR DASHBOARD
# =========================================================

@app.route("/doctor/dashboard")
@role_required("doctor")
def doctor_dashboard():

    doctor_id = session["user_id"]

    conn = get_db()

    # Doctor accounts can be linked to doctors through email
    doctor = conn.execute("""
        SELECT *
        FROM doctors
        WHERE email = (
            SELECT email
            FROM users
            WHERE id = ?
        )
    """, (doctor_id,)).fetchone()

    appointments = []

    if doctor:

        appointments = conn.execute("""
            SELECT
                appointments.*,
                users.name AS patient_name,
                users.phone AS patient_phone,
                users.email AS patient_email
            FROM appointments

            JOIN users
            ON appointments.patient_id = users.id

            WHERE appointments.doctor_id = ?

            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time DESC
        """, (
            doctor["id"],
        )).fetchall()

    conn.close()

    return render_template(
        "doctor/dashboard.html",
        doctor=doctor,
        appointments=appointments
    )


# =========================================================
# DOCTOR APPOINTMENTS
# =========================================================

@app.route("/doctor/appointments")
@role_required("doctor")
def doctor_appointments():

    doctor_id = session["user_id"]

    conn = get_db()

    doctor = conn.execute("""
        SELECT *
        FROM doctors
        WHERE email = (
            SELECT email
            FROM users
            WHERE id = ?
        )
    """, (doctor_id,)).fetchone()

    appointments = []

    if doctor:

        appointments = conn.execute("""
            SELECT
                appointments.*,
                users.name AS patient_name,
                users.phone AS patient_phone,
                users.email AS patient_email
            FROM appointments

            JOIN users
            ON appointments.patient_id = users.id

            WHERE appointments.doctor_id = ?

            ORDER BY
                appointments.appointment_date DESC,
                appointments.appointment_time DESC
        """, (
            doctor["id"],
        )).fetchall()

    conn.close()

    return render_template(
        "doctor/appointments.html",
        doctor=doctor,
        appointments=appointments
    )


# =========================================================
# DOCTOR UPDATE APPOINTMENT STATUS
# =========================================================

@app.route(
    "/doctor/appointments/<int:appointment_id>/<status>",
    methods=["POST"]
)
@role_required("doctor")
def update_appointment_status(
    appointment_id,
    status
):

    allowed_statuses = [
        "Approved",
        "Rejected",
        "Completed"
    ]

    if status not in allowed_statuses:

        flash(
            "Invalid appointment status.",
            "danger"
        )

        return redirect(
            url_for("doctor_appointments")
        )

    doctor_user_id = session["user_id"]

    conn = get_db()

    doctor = conn.execute("""
        SELECT *
        FROM doctors
        WHERE email = (
            SELECT email
            FROM users
            WHERE id = ?
        )
    """, (
        doctor_user_id,
    )).fetchone()

    if not doctor:

        conn.close()

        flash(
            "Doctor profile not found.",
            "danger"
        )

        return redirect(
            url_for("doctor_dashboard")
        )

    conn.execute("""
        UPDATE appointments
        SET status = ?
        WHERE id = ?
        AND doctor_id = ?
    """, (
        status,
        appointment_id,
        doctor["id"]
    ))

    conn.commit()
    conn.close()

    flash(
        f"Appointment marked as {status}.",
        "success"
    )

    return redirect(
        url_for("doctor_appointments")
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():

    conn = get_db()

    total_patients = conn.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'patient'
    """).fetchone()[0]

    total_doctors = conn.execute("""
        SELECT COUNT(*)
        FROM doctors
    """).fetchone()[0]

    total_appointments = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
    """).fetchone()[0]

    pending_appointments = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'Pending'
    """).fetchone()[0]

    approved_appointments = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'Approved'
    """).fetchone()[0]

    completed_appointments = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE status = 'Completed'
    """).fetchone()[0]

    recent_appointments = conn.execute("""
        SELECT
            appointments.*,
            users.name AS patient_name,
            doctors.name AS doctor_name,
            doctors.specialization
        FROM appointments

        JOIN users
        ON appointments.patient_id = users.id

        JOIN doctors
        ON appointments.doctor_id = doctors.id

        ORDER BY appointments.created_at DESC

        LIMIT 10
    """).fetchall()

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_appointments=total_appointments,
        pending_appointments=pending_appointments,
        approved_appointments=approved_appointments,
        completed_appointments=completed_appointments,
        recent_appointments=recent_appointments
    )


# =========================================================
# ADMIN DOCTORS
# =========================================================

@app.route("/admin/doctors")
@role_required("admin")
def admin_doctors():

    conn = get_db()

    doctors_list = conn.execute("""
        SELECT *
        FROM doctors
        ORDER BY name
    """).fetchall()

    conn.close()

    return render_template(
        "admin/doctors.html",
        doctors=doctors_list
    )


# =========================================================
# ADD DOCTOR
# =========================================================

@app.route(
    "/admin/doctors/add",
    methods=["GET", "POST"]
)
@role_required("admin")
def add_doctor():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        specialization = request.form.get(
            "specialization",
            ""
        ).strip()

        qualification = request.form.get(
            "qualification",
            ""
        ).strip()

        experience = request.form.get(
            "experience",
            0
        )

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        available_days = request.form.get(
            "available_days",
            ""
        ).strip()

        available_time = request.form.get(
            "available_time",
            ""
        ).strip()

        consultation_fee = request.form.get(
            "consultation_fee",
            0
        )

        if not name or not specialization:

            flash(
                "Doctor name and specialization are required.",
                "danger"
            )

            return redirect(
                url_for("add_doctor")
            )

        try:

            experience = int(experience)
            consultation_fee = float(
                consultation_fee
            )

        except ValueError:

            flash(
                "Experience and consultation fee must be valid numbers.",
                "danger"
            )

            return redirect(
                url_for("add_doctor")
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO doctors
            (
                name,
                specialization,
                qualification,
                experience,
                phone,
                email,
                available_days,
                available_time,
                consultation_fee
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name,
            specialization,
            qualification,
            experience,
            phone,
            email,
            available_days,
            available_time,
            consultation_fee
        ))

        conn.commit()
        conn.close()

        flash(
            "Doctor added successfully.",
            "success"
        )

        return redirect(
            url_for("admin_doctors")
        )

    return render_template(
        "admin/add_doctor.html"
    )


# =========================================================
# EDIT DOCTOR
# =========================================================

@app.route(
    "/admin/doctors/<int:doctor_id>/edit",
    methods=["GET", "POST"]
)
@role_required("admin")
def edit_doctor(doctor_id):

    conn = get_db()

    doctor = conn.execute("""
        SELECT *
        FROM doctors
        WHERE id = ?
    """, (doctor_id,)).fetchone()

    if not doctor:

        conn.close()

        flash(
            "Doctor not found.",
            "danger"
        )

        return redirect(
            url_for("admin_doctors")
        )

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        specialization = request.form.get(
            "specialization",
            ""
        ).strip()

        qualification = request.form.get(
            "qualification",
            ""
        ).strip()

        experience = request.form.get(
            "experience",
            0
        )

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        available_days = request.form.get(
            "available_days",
            ""
        ).strip()

        available_time = request.form.get(
            "available_time",
            ""
        ).strip()

        consultation_fee = request.form.get(
            "consultation_fee",
            0
        )

        status = request.form.get(
            "status",
            "Active"
        )

        try:

            experience = int(experience)
            consultation_fee = float(
                consultation_fee
            )

        except ValueError:

            conn.close()

            flash(
                "Invalid experience or consultation fee.",
                "danger"
            )

            return redirect(
                url_for(
                    "edit_doctor",
                    doctor_id=doctor_id
                )
            )

        conn.execute("""
            UPDATE doctors

            SET
                name = ?,
                specialization = ?,
                qualification = ?,
                experience = ?,
                phone = ?,
                email = ?,
                available_days = ?,
                available_time = ?,
                consultation_fee = ?,
                status = ?

            WHERE id = ?
        """, (
            name,
            specialization,
            qualification,
            experience,
            phone,
            email,
            available_days,
            available_time,
            consultation_fee,
            status,
            doctor_id
        ))

        conn.commit()
        conn.close()

        flash(
            "Doctor information updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin_doctors")
        )

    conn.close()

    return render_template(
        "admin/edit_doctor.html",
        doctor=doctor
    )


# =========================================================
# DELETE DOCTOR
# =========================================================

@app.route(
    "/admin/doctors/<int:doctor_id>/delete",
    methods=["POST"]
)
@role_required("admin")
def delete_doctor(doctor_id):

    conn = get_db()

    appointment_count = conn.execute("""
        SELECT COUNT(*)
        FROM appointments
        WHERE doctor_id = ?
    """, (
        doctor_id,
    )).fetchone()[0]

    if appointment_count > 0:

        conn.execute("""
            UPDATE doctors
            SET status = 'Inactive'
            WHERE id = ?
        """, (
            doctor_id,
        ))

        message = (
            "Doctor has appointment records, "
            "so the profile was marked inactive."
        )

    else:

        conn.execute("""
            DELETE FROM doctors
            WHERE id = ?
        """, (
            doctor_id,
        ))

        message = "Doctor deleted successfully."

    conn.commit()
    conn.close()

    flash(
        message,
        "success"
    )

    return redirect(
        url_for("admin_doctors")
    )


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "index.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    return """
    <h1>Internal Server Error</h1>
    <p>Something went wrong. Please try again.</p>
    """, 500


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":

    init_database()

    app.run(
        debug=True
    )