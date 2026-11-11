"""
database.py - All SQLite logic for the Smart Attendance & Grade Tracker.

The GUI (app.py) never writes SQL itself; it only calls the methods of the
Database class below. Keeping the data layer separate from the UI layer makes
both easier to read, test and change.
"""
import hashlib
import os
import random
import sqlite3
from datetime import date, timedelta

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tracker.db")
MIN_ATTENDANCE = 75  # percent a student needs to be eligible for exams

# (minimum total out of 100, grade letter, grade point) on a 10-point scale
GRADE_TABLE = [(90, "O", 10), (80, "A+", 9), (70, "A", 8), (60, "B+", 7),
               (50, "B", 6), (40, "C", 5), (0, "F", 0)]


def hash_password(password):
    """Passwords are stored as SHA-256 hashes, never as plain text."""
    return hashlib.sha256(password.encode()).hexdigest()


def grade_for(total):
    """Return (grade letter, grade point) for a total mark out of 100."""
    for cutoff, letter, point in GRADE_TABLE:
        if total >= cutoff:
            return letter, point
    return "F", 0


def percent(part, whole):
    return round(100 * part / whole, 1) if whole else None


class Database:
    def __init__(self, path=DB_FILE):
        first_run = not os.path.exists(path)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row          # rows behave like dicts
        self.conn.execute("PRAGMA foreign_keys = ON")  # enables ON DELETE CASCADE
        self.create_tables()
        if first_run:
            self.seed_demo_data()

    # ------------------------------------------------------------------ setup
    def create_tables(self):
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS students (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_no  TEXT UNIQUE NOT NULL,
            name     TEXT NOT NULL,
            dept     TEXT,
            semester INTEGER,
            phone    TEXT,
            email    TEXT
        );
        CREATE TABLE IF NOT EXISTS subjects (
            id      INTEGER PRIMARY KEY AUTOINCREMENT,
            code    TEXT UNIQUE NOT NULL,
            name    TEXT NOT NULL,
            credits INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS attendance (
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
            class_date TEXT NOT NULL,
            status     TEXT CHECK (status IN ('P', 'A')),
            PRIMARY KEY (student_id, subject_id, class_date)
        );
        CREATE TABLE IF NOT EXISTS marks (
            student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
            subject_id INTEGER REFERENCES subjects(id) ON DELETE CASCADE,
            internal   REAL NOT NULL,
            external   REAL NOT NULL,
            PRIMARY KEY (student_id, subject_id)
        );
        """)
        self.conn.execute("INSERT OR IGNORE INTO users VALUES (?, ?)",
                          ("admin", hash_password("admin123")))
        self.conn.commit()

    # ------------------------------------------------------------------ login
    def check_login(self, username, password):
        row = self.conn.execute("SELECT password FROM users WHERE username = ?",
                                (username,)).fetchone()
        return row is not None and row["password"] == hash_password(password)

    # --------------------------------------------------------------- students
    def get_students(self, search=""):
        like = f"%{search}%"
        return self.conn.execute(
            "SELECT * FROM students WHERE roll_no LIKE ? OR name LIKE ? OR dept LIKE ? "
            "ORDER BY roll_no", (like, like, like)).fetchall()

    def add_student(self, roll_no, name, dept, semester, phone, email):
        with self.conn:
            self.conn.execute(
                "INSERT INTO students (roll_no, name, dept, semester, phone, email) "
                "VALUES (?, ?, ?, ?, ?, ?)", (roll_no, name, dept, semester, phone, email))

    def update_student(self, student_id, roll_no, name, dept, semester, phone, email):
        with self.conn:
            self.conn.execute(
                "UPDATE students SET roll_no = ?, name = ?, dept = ?, semester = ?, "
                "phone = ?, email = ? WHERE id = ?",
                (roll_no, name, dept, semester, phone, email, student_id))

    def delete_student(self, student_id):
        with self.conn:
            self.conn.execute("DELETE FROM students WHERE id = ?", (student_id,))

    # --------------------------------------------------------------- subjects
    def get_subjects(self, search=""):
        like = f"%{search}%"
        return self.conn.execute(
            "SELECT * FROM subjects WHERE code LIKE ? OR name LIKE ? ORDER BY code",
            (like, like)).fetchall()

    def add_subject(self, code, name, credits):
        with self.conn:
            self.conn.execute("INSERT INTO subjects (code, name, credits) VALUES (?, ?, ?)",
                              (code, name, credits))

    def update_subject(self, subject_id, code, name, credits):
        with self.conn:
            self.conn.execute("UPDATE subjects SET code = ?, name = ?, credits = ? WHERE id = ?",
                              (code, name, credits, subject_id))

    def delete_subject(self, subject_id):
        with self.conn:
            self.conn.execute("DELETE FROM subjects WHERE id = ?", (subject_id,))

    # ------------------------------------------------------------- attendance
    def get_attendance_sheet(self, subject_id, class_date):
        """Every student with their status for one class (None if not marked yet)."""
        return self.conn.execute("""
            SELECT s.id, s.roll_no, s.name, a.status
            FROM students s
            LEFT JOIN attendance a
                   ON a.student_id = s.id AND a.subject_id = ? AND a.class_date = ?
            ORDER BY s.roll_no""", (subject_id, class_date)).fetchall()

    def save_attendance(self, subject_id, class_date, statuses):
        """statuses is {student_id: 'P' or 'A'}. Re-saving a date overwrites it."""
        with self.conn:
            self.conn.executemany(
                "INSERT OR REPLACE INTO attendance VALUES (?, ?, ?, ?)",
                [(sid, subject_id, class_date, st) for sid, st in statuses.items()])

    def attendance_report(self):
        """Attendance % for every student in every subject."""
        rows = self.conn.execute("""
            SELECT s.roll_no, s.name, sub.code AS subject,
                   COUNT(*) AS total, SUM(a.status = 'P') AS present
            FROM attendance a
            JOIN students s   ON s.id = a.student_id
            JOIN subjects sub ON sub.id = a.subject_id
            GROUP BY s.id, sub.id
            ORDER BY s.roll_no, sub.code""").fetchall()
        return [dict(r, percent=percent(r["present"], r["total"])) for r in rows]

    def student_attendance(self):
        """Overall attendance % per student across all subjects."""
        rows = self.conn.execute("""
            SELECT s.id, s.roll_no, s.name,
                   COUNT(a.status) AS total, COALESCE(SUM(a.status = 'P'), 0) AS present
            FROM students s
            LEFT JOIN attendance a ON a.student_id = s.id
            GROUP BY s.id""").fetchall()
        return [dict(r, percent=percent(r["present"], r["total"])) for r in rows]

    def subject_attendance(self):
        """Average attendance % per subject (used for the dashboard chart)."""
        rows = self.conn.execute("""
            SELECT sub.code, COUNT(a.status) AS total,
                   COALESCE(SUM(a.status = 'P'), 0) AS present
            FROM subjects sub
            LEFT JOIN attendance a ON a.subject_id = sub.id
            GROUP BY sub.id
            ORDER BY sub.code""").fetchall()
        return [dict(r, percent=percent(r["present"], r["total"])) for r in rows if r["total"]]

    # ------------------------------------------------------------------ marks
    def get_marks_sheet(self, subject_id):
        return self.conn.execute("""
            SELECT s.id, s.roll_no, s.name, m.internal, m.external
            FROM students s
            LEFT JOIN marks m ON m.student_id = s.id AND m.subject_id = ?
            ORDER BY s.roll_no""", (subject_id,)).fetchall()

    def save_marks(self, student_id, subject_id, internal, external):
        with self.conn:
            self.conn.execute("INSERT OR REPLACE INTO marks VALUES (?, ?, ?, ?)",
                              (student_id, subject_id, internal, external))

    def result_report(self):
        """CGPA per student = sum(credits x grade point) / sum(credits).
        Sorted best first; students without any marks come last."""
        summary = {s["id"]: {"roll_no": s["roll_no"], "name": s["name"], "subjects": 0,
                             "credits": 0, "points": 0, "failed": False}
                   for s in self.get_students()}
        rows = self.conn.execute("""
            SELECT m.student_id, sub.credits, m.internal + m.external AS total
            FROM marks m JOIN subjects sub ON sub.id = m.subject_id""").fetchall()
        for r in rows:
            st = summary[r["student_id"]]
            letter, point = grade_for(r["total"])
            st["subjects"] += 1
            st["credits"] += r["credits"]
            st["points"] += r["credits"] * point
            st["failed"] = st["failed"] or letter == "F"

        report = list(summary.values())
        for st in report:
            st["cgpa"] = round(st["points"] / st["credits"], 2) if st["credits"] else None
            if st["cgpa"] is None:
                st["result"] = "No marks"
            else:
                st["result"] = "Fail" if st["failed"] else "Pass"
        report.sort(key=lambda s: -1 if s["cgpa"] is None else s["cgpa"], reverse=True)
        return report

    # -------------------------------------------------------------- dashboard
    def dashboard_stats(self):
        attended = [s for s in self.student_attendance() if s["percent"] is not None]
        results = self.result_report()
        return {
            "students": self.conn.execute("SELECT COUNT(*) FROM students").fetchone()[0],
            "subjects": self.conn.execute("SELECT COUNT(*) FROM subjects").fetchone()[0],
            "avg_attendance": round(sum(s["percent"] for s in attended) / len(attended), 1)
                              if attended else None,
            "defaulters": sum(1 for s in attended if s["percent"] < MIN_ATTENDANCE),
            "topper": results[0] if results and results[0]["cgpa"] is not None else None,
        }

    # -------------------------------------------------------------- demo data
    def seed_demo_data(self):
        """Fill a brand-new database with sample data so the app can be demoed."""
        rng = random.Random(7)
        subjects = [("CS301", "Python Programming", 4), ("CS302", "Data Structures", 4),
                    ("CS303", "Database Systems", 3)]
        # (roll no, name, dept, semester, how regularly they attend)
        students = [("133", "Chan", "NWC", 3, 0.95),
                    ("134", "Rahul", "NWC", 3, 0.70)]

        class_days = []
        day = date.today()
        while len(class_days) < 8:  # the last 8 weekdays
            day -= timedelta(days=1)
            if day.weekday() < 5:
                class_days.append(day.isoformat())

        with self.conn:
            self.conn.executemany("INSERT INTO subjects (code, name, credits) VALUES (?, ?, ?)",
                                  subjects)
            subject_ids = [r[0] for r in self.conn.execute("SELECT id FROM subjects")]
            for roll_no, name, dept, semester, regularity in students:
                sid = self.conn.execute(
                    "INSERT INTO students (roll_no, name, dept, semester) VALUES (?, ?, ?, ?)",
                    (roll_no, name, dept, semester)).lastrowid
                for sub in subject_ids:
                    for d in class_days:
                        status = "P" if rng.random() < regularity else "A"
                        self.conn.execute("INSERT INTO attendance VALUES (?, ?, ?, ?)",
                                          (sid, sub, d, status))
                    internal = round(min(40, 40 * regularity * rng.uniform(0.75, 1.05)))
                    external = round(min(60, 60 * regularity * rng.uniform(0.7, 1.05)))
                    self.conn.execute("INSERT INTO marks VALUES (?, ?, ?, ?)",
                                      (sid, sub, internal, external))
