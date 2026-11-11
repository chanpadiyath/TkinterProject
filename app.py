"""
Smart Attendance & Grade Tracker
--------------------------------
A Tkinter + SQLite desktop application to manage students and subjects,
mark daily attendance, enter marks, and generate attendance-shortage and
CGPA reports.

Run:    python3 app.py
Login:  admin / admin123
"""
import csv
import re
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, messagebox, ttk

from database import GRADE_TABLE, MIN_ATTENDANCE, Database, grade_for

# ---------------------------------------------------------------- theme
PRIMARY = "#2b5797"
BG = "#f4f6fa"
CARD = "#ffffff"
DANGER = "#d9534f"
SUCCESS = "#2e8b57"
TEXT = "#222222"
MUTED = "#6b7280"
FONT = "Helvetica"
DEPARTMENTS = ["NWC", "CSE", "IT", "ECE", "EEE", "MECH", "CIVIL"]


# ---------------------------------------------------------------- helpers
def make_table(parent, columns):
    """Create a Treeview (table) with a scrollbar.
    columns is a list of (key, heading, width). Returns (frame, tree)."""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings",
                        selectmode="browse")
    for key, heading, width in columns:
        tree.heading(key, text=heading)
        tree.column(key, width=width, anchor="w" if width >= 150 else "center")
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    tree.pack(side="left", fill="both", expand=True)
    scroll.pack(side="right", fill="y")
    tree.tag_configure("low", background="#fde2e1")
    tree.tag_configure("present", foreground=SUCCESS)
    tree.tag_configure("absent", foreground=DANGER)
    return frame, tree


def clear_table(tree):
    tree.delete(*tree.get_children())


def export_csv(tree, filename):
    """Save whatever is currently shown in a table to a CSV file."""
    rows = tree.get_children()
    if not rows:
        messagebox.showwarning("Nothing to export", "The table is empty.")
        return
    path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"{filename}.csv",
                                        filetypes=[("CSV files", "*.csv")])
    if not path:
        return
    cols = tree["columns"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([tree.heading(c)["text"] for c in cols])
        for item in rows:
            writer.writerow([tree.set(item, c) for c in cols])
    messagebox.showinfo("Exported", f"Saved {len(rows)} rows to:\n{path}")


def labeled(parent, row, text, widget):
    """Place a label and a widget side by side in a grid row."""
    ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", pady=4)
    widget.grid(row=row, column=1, sticky="ew", pady=4, padx=(8, 0))
    return widget


def fmt(value):
    """Show 32.0 as 32 and 32.5 as 32.5."""
    return f"{value:g}"


# ---------------------------------------------------------------- main window
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title("Smart Attendance & Grade Tracker")
        self.configure(bg=BG)
        self.setup_styles()
        self.show_login()

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=TEXT, font=(FONT, 11))
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG)
        style.configure("TCheckbutton", background=BG)
        style.configure("Card.TFrame", background=CARD, relief="solid", borderwidth=1)
        style.configure("Title.TLabel", font=(FONT, 20, "bold"), foreground=PRIMARY)
        style.configure("Heading.TLabel", font=(FONT, 13, "bold"))
        style.configure("Muted.TLabel", foreground=MUTED)
        style.configure("CardValue.TLabel", background=CARD, foreground=PRIMARY,
                        font=(FONT, 22, "bold"))
        style.configure("CardSmall.TLabel", background=CARD, foreground=PRIMARY,
                        font=(FONT, 15, "bold"))
        style.configure("CardName.TLabel", background=CARD, foreground=MUTED)
        style.configure("Accent.TButton", background=PRIMARY, foreground="white",
                        font=(FONT, 11, "bold"))
        style.map("Accent.TButton", background=[("active", "#1e3f6f")])
        style.configure("Danger.TButton", background=DANGER, foreground="white")
        style.map("Danger.TButton", background=[("active", "#b52b27")])
        style.configure("Treeview", rowheight=26, font=(FONT, 11))
        style.configure("Treeview.Heading", font=(FONT, 11, "bold"), background="#dde4f0")
        style.configure("TNotebook.Tab", padding=(14, 6), font=(FONT, 11, "bold"))
        style.configure("TLabelframe", background=BG)
        style.configure("TLabelframe.Label", background=BG, foreground=PRIMARY,
                        font=(FONT, 11, "bold"))

    # ----- login screen
    def show_login(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.geometry("420x380")
        self.minsize(420, 380)
        self.resizable(False, False)

        frame = ttk.Frame(self, padding=30)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Smart Attendance\n& Grade Tracker", style="Title.TLabel",
                  justify="center").pack(pady=(0, 20))

        ttk.Label(frame, text="Username").pack(anchor="w")
        self.user_var = tk.StringVar()
        user_entry = ttk.Entry(frame, textvariable=self.user_var)
        user_entry.pack(fill="x", pady=(2, 10))

        ttk.Label(frame, text="Password").pack(anchor="w")
        self.pass_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.pass_var, show="•").pack(fill="x", pady=(2, 16))

        ttk.Button(frame, text="Login", style="Accent.TButton",
                   command=self.do_login).pack(fill="x", ipady=4)
        ttk.Label(frame, text="Default login: admin / admin123",
                  style="Muted.TLabel").pack(pady=(12, 0))

        self.bind("<Return>", lambda _: self.do_login())
        user_entry.focus_set()

    def do_login(self):
        if self.db.check_login(self.user_var.get().strip(), self.pass_var.get()):
            self.unbind("<Return>")
            self.show_main()
        else:
            messagebox.showerror("Login failed", "Incorrect username or password.")
            self.pass_var.set("")

    # ----- main screen
    def show_main(self):
        for widget in self.winfo_children():
            widget.destroy()
        self.resizable(True, True)
        self.minsize(980, 620)
        self.geometry("1120x700")

        header = tk.Frame(self, bg=PRIMARY)
        header.pack(fill="x")
        tk.Label(header, text="Smart Attendance & Grade Tracker", bg=PRIMARY, fg="white",
                 font=(FONT, 16, "bold")).pack(side="left", padx=16, pady=10)
        ttk.Button(header, text="Logout", command=self.show_login).pack(side="right", padx=16)
        tk.Label(header, text=f"Logged in as {self.user_var.get().strip()}  •  "
                              f"{date.today():%d %b %Y}",
                 bg=PRIMARY, fg="#dbe4f3", font=(FONT, 11)).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabs = [tab_class(self.notebook, self.db) for tab_class in
                     (DashboardTab, StudentsTab, SubjectsTab, AttendanceTab, MarksTab, ReportsTab)]
        for tab in self.tabs:
            self.notebook.add(tab, text=tab.title)
        # Refresh a tab whenever it is opened so it always shows the latest data.
        self.notebook.bind("<<NotebookTabChanged>>",
                           lambda _: self.tabs[self.notebook.index("current")].refresh())


# ---------------------------------------------------------------- tabs
class Tab(ttk.Frame):
    """Base class for every tab: subclasses build their widgets in build()
    and reload data from the database in refresh()."""
    title = ""

    def __init__(self, parent, db):
        super().__init__(parent, padding=12)
        self.db = db
        self.build()
        self.refresh()

    def build(self):
        pass

    def refresh(self):
        pass


class DashboardTab(Tab):
    title = "Dashboard"
    card_names = ["Students", "Subjects", "Avg Attendance",
                  f"Students below {MIN_ATTENDANCE}%", "Class Topper"]

    def build(self):
        ttk.Label(self, text="Overview", style="Heading.TLabel").pack(anchor="w")
        cards = ttk.Frame(self)
        cards.pack(fill="x", pady=10)
        self.card_vars = {}
        for i, name in enumerate(self.card_names):
            card = ttk.Frame(cards, style="Card.TFrame", padding=14)
            card.grid(row=0, column=i, sticky="nsew", padx=6)
            cards.columnconfigure(i, weight=1, uniform="cards")
            var = tk.StringVar(value="-")
            style = "CardSmall.TLabel" if name == "Class Topper" else "CardValue.TLabel"
            ttk.Label(card, textvariable=var, style=style).pack(anchor="w")
            ttk.Label(card, text=name, style="CardName.TLabel").pack(anchor="w")
            self.card_vars[name] = var

        ttk.Label(self, text="Attendance by Subject", style="Heading.TLabel").pack(
            anchor="w", pady=(10, 0))
        self.canvas = tk.Canvas(self, bg=CARD, highlightthickness=1,
                                highlightbackground="#d0d7e2", height=300)
        self.canvas.pack(fill="both", expand=True, pady=8)
        self.canvas.bind("<Configure>", lambda _: self.draw_chart())
        self.chart_data = []

    def refresh(self):
        s = self.db.dashboard_stats()
        self.card_vars["Students"].set(s["students"])
        self.card_vars["Subjects"].set(s["subjects"])
        self.card_vars["Avg Attendance"].set(
            "-" if s["avg_attendance"] is None else f"{s['avg_attendance']}%")
        self.card_vars[f"Students below {MIN_ATTENDANCE}%"].set(s["defaulters"])
        top = s["topper"]
        self.card_vars["Class Topper"].set(
            "-" if top is None else f"{top['name'].split()[0]} ({top['cgpa']})")
        self.chart_data = self.db.subject_attendance()
        self.draw_chart()

    def draw_chart(self):
        """A bar chart drawn by hand on a Canvas (no extra libraries needed)."""
        c = self.canvas
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w < 100 or h < 100:
            return
        if not self.chart_data:
            c.create_text(w / 2, h / 2, text="No attendance recorded yet.", fill=MUTED,
                          font=(FONT, 12))
            return

        left, right, top, bottom = 55, 90, 25, 40
        base_y = h - bottom
        plot_h = base_y - top

        def y_for(pct):
            return base_y - plot_h * pct / 100

        for pct in range(0, 101, 25):  # horizontal grid lines
            c.create_line(left, y_for(pct), w - right, y_for(pct), fill="#eceff4")
            c.create_text(left - 8, y_for(pct), text=f"{pct}%", anchor="e", fill=MUTED)

        slot = (w - left - right) / len(self.chart_data)
        bar_w = min(80, slot * 0.5)
        for i, row in enumerate(self.chart_data):
            x0 = left + slot * i + (slot - bar_w) / 2
            colour = SUCCESS if row["percent"] >= MIN_ATTENDANCE else DANGER
            c.create_rectangle(x0, y_for(row["percent"]), x0 + bar_w, base_y,
                               fill=colour, outline="")
            c.create_text(x0 + bar_w / 2, y_for(row["percent"]) - 10,
                          text=f"{row['percent']}%", font=(FONT, 10, "bold"))
            c.create_text(x0 + bar_w / 2, base_y + 16, text=row["code"],
                          font=(FONT, 11, "bold"))

        line_y = y_for(MIN_ATTENDANCE)  # the minimum-attendance threshold
        c.create_line(left, line_y, w - right, line_y, fill=DANGER, dash=(6, 4), width=2)
        c.create_text(w - right + 6, line_y, text=f"Min {MIN_ATTENDANCE}%", anchor="w",
                      fill=DANGER, font=(FONT, 10, "bold"))


class CrudTab(Tab):
    """Shared layout for the Students and Subjects tabs: a form on the left and a
    searchable table on the right, with Add / Update / Delete / Clear buttons.
    Subclasses only describe their fields and which database methods to call."""
    form_title = ""
    record_name = ""
    fields = []   # (key, label, kind, options) - kind is "entry", "combo" or "spin"
    columns = []  # (key, heading, width)

    def build(self):
        self.selected_id = None
        self.rows = {}

        form = ttk.LabelFrame(self, text=self.form_title, padding=12)
        form.pack(side="left", fill="y", padx=(0, 12))
        self.vars = {}
        for i, (key, label, kind, options) in enumerate(self.fields):
            var = tk.StringVar()
            self.vars[key] = var
            if kind == "combo":
                widget = ttk.Combobox(form, textvariable=var, values=options, width=22)
            elif kind == "spin":
                widget = ttk.Spinbox(form, textvariable=var, from_=options[0], to=options[1],
                                     width=22)
            else:
                widget = ttk.Entry(form, textvariable=var, width=24)
            labeled(form, i, label, widget)

        buttons = ttk.Frame(form)
        buttons.grid(row=len(self.fields), column=0, columnspan=2, sticky="ew", pady=(14, 0))
        ttk.Button(buttons, text="Add", style="Accent.TButton",
                   command=self.add_record).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Update", command=self.update_record).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Delete", style="Danger.TButton",
                   command=self.delete_record).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Clear", command=self.clear_form).pack(fill="x", pady=2)
        ttk.Label(form, text="* required", style="Muted.TLabel").grid(
            row=len(self.fields) + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))

        right = ttk.Frame(self)
        right.pack(side="left", fill="both", expand=True)
        bar = ttk.Frame(right)
        bar.pack(fill="x")
        ttk.Label(bar, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(bar, textvariable=self.search_var, width=30).pack(side="left", padx=6)
        self.count_var = tk.StringVar()
        ttk.Label(bar, textvariable=self.count_var, style="Muted.TLabel").pack(side="right")

        table_frame, self.tree = make_table(right, self.columns)
        table_frame.pack(fill="both", expand=True, pady=(8, 0))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        # Live search: re-filter the table on every keystroke.
        self.search_var.trace_add("write", lambda *_: self.refresh())

    def refresh(self):
        clear_table(self.tree)
        self.rows = {}
        for row in self.db_fetch(self.search_var.get().strip()):
            self.rows[row["id"]] = row
            self.tree.insert("", "end", iid=row["id"],
                             values=["" if row[key] is None else row[key]
                                     for key, _, _ in self.columns])
        self.count_var.set(f"{len(self.rows)} {self.record_name}s")

    def on_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        row = self.rows[self.selected_id]
        for key, var in self.vars.items():
            var.set("" if row[key] is None else row[key])

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.selected_id = None
        self.tree.selection_remove(self.tree.selection())

    def add_record(self):
        data = self.validate()
        if data is None:
            return
        try:
            self.db_add(data)
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", self.duplicate_message)
            return
        self.clear_form()
        self.refresh()
        messagebox.showinfo("Added", f"{self.record_name.capitalize()} added successfully.")

    def update_record(self):
        if self.selected_id is None:
            messagebox.showwarning("Nothing selected",
                                   f"Select a {self.record_name} from the table first.")
            return
        data = self.validate()
        if data is None:
            return
        try:
            self.db_update(self.selected_id, data)
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate", self.duplicate_message)
            return
        self.clear_form()
        self.refresh()
        messagebox.showinfo("Updated", f"{self.record_name.capitalize()} updated successfully.")

    def delete_record(self):
        if self.selected_id is None:
            messagebox.showwarning("Nothing selected",
                                   f"Select a {self.record_name} from the table first.")
            return
        row = self.rows[self.selected_id]
        if messagebox.askyesno("Confirm delete",
                               f"Delete {self.describe(row)}?\n\nAll attendance and marks "
                               f"linked to this {self.record_name} will also be deleted."):
            self.db_delete(self.selected_id)
            self.clear_form()
            self.refresh()


class StudentsTab(CrudTab):
    title = "Students"
    form_title = "Student Details"
    record_name = "student"
    duplicate_message = "A student with this roll number already exists."
    fields = [("roll_no", "Roll No *", "entry", None),
              ("name", "Full Name *", "entry", None),
              ("dept", "Department", "combo", DEPARTMENTS),
              ("semester", "Semester", "spin", (1, 8)),
              ("phone", "Phone", "entry", None),
              ("email", "Email", "entry", None)]
    columns = [("roll_no", "Roll No", 90), ("name", "Name", 170), ("dept", "Dept", 70),
               ("semester", "Sem", 50), ("phone", "Phone", 110), ("email", "Email", 220)]

    def db_fetch(self, search):
        return self.db.get_students(search)

    def db_add(self, data):
        self.db.add_student(**data)

    def db_update(self, record_id, data):
        self.db.update_student(record_id, **data)

    def db_delete(self, record_id):
        self.db.delete_student(record_id)

    def describe(self, row):
        return f"{row['roll_no']} - {row['name']}"

    def validate(self):
        d = {key: var.get().strip() for key, var in self.vars.items()}
        if not d["roll_no"] or not d["name"]:
            messagebox.showerror("Missing data", "Roll No and Name are required.")
            return None
        if d["semester"] and not (d["semester"].isdigit() and 1 <= int(d["semester"]) <= 8):
            messagebox.showerror("Invalid semester", "Semester must be a number from 1 to 8.")
            return None
        if d["phone"] and not (d["phone"].isdigit() and len(d["phone"]) == 10):
            messagebox.showerror("Invalid phone", "Phone number must be exactly 10 digits.")
            return None
        if d["email"] and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", d["email"]):
            messagebox.showerror("Invalid email", "Please enter a valid email address.")
            return None
        d["roll_no"] = d["roll_no"].upper()
        d["semester"] = int(d["semester"]) if d["semester"] else None
        for key in ("dept", "phone", "email"):
            d[key] = d[key] or None
        return d


class SubjectsTab(CrudTab):
    title = "Subjects"
    form_title = "Subject Details"
    record_name = "subject"
    duplicate_message = "A subject with this code already exists."
    fields = [("code", "Subject Code *", "entry", None),
              ("name", "Subject Name *", "entry", None),
              ("credits", "Credits *", "spin", (1, 6))]
    columns = [("code", "Code", 100), ("name", "Subject Name", 300), ("credits", "Credits", 80)]

    def db_fetch(self, search):
        return self.db.get_subjects(search)

    def db_add(self, data):
        self.db.add_subject(**data)

    def db_update(self, record_id, data):
        self.db.update_subject(record_id, **data)

    def db_delete(self, record_id):
        self.db.delete_subject(record_id)

    def describe(self, row):
        return f"{row['code']} - {row['name']}"

    def validate(self):
        d = {key: var.get().strip() for key, var in self.vars.items()}
        if not d["code"] or not d["name"]:
            messagebox.showerror("Missing data", "Subject code and name are required.")
            return None
        if not (d["credits"].isdigit() and 1 <= int(d["credits"]) <= 6):
            messagebox.showerror("Invalid credits", "Credits must be a number from 1 to 6.")
            return None
        d["code"] = d["code"].upper()
        d["credits"] = int(d["credits"])
        return d


class SubjectPicker:
    """Mixin for tabs that start with a 'Subject' dropdown."""

    def build_subject_picker(self, parent):
        ttk.Label(parent, text="Subject:").pack(side="left")
        self.subject_var = tk.StringVar()
        self.subject_box = ttk.Combobox(parent, textvariable=self.subject_var,
                                        state="readonly", width=32)
        self.subject_box.pack(side="left", padx=6)

    def reload_subjects(self):
        self.subjects = {f"{s['code']} - {s['name']}": s["id"] for s in self.db.get_subjects()}
        self.subject_box["values"] = list(self.subjects)
        if self.subject_var.get() not in self.subjects:
            self.subject_var.set(next(iter(self.subjects), ""))

    def current_subject(self):
        subject_id = self.subjects.get(self.subject_var.get())
        if subject_id is None:
            messagebox.showwarning("No subject", "Add a subject in the Subjects tab first.")
        return subject_id


class AttendanceTab(SubjectPicker, Tab):
    title = "Attendance"

    def build(self):
        self.statuses = {}  # {student_id: 'P' or 'A'} for the sheet on screen
        self.loaded = None  # (subject_id, date, label) of the sheet on screen

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        self.build_subject_picker(bar)
        ttk.Label(bar, text="Date (YYYY-MM-DD):").pack(side="left", padx=(16, 4))
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(bar, textvariable=self.date_var, width=12).pack(side="left")
        ttk.Button(bar, text="Load Sheet", style="Accent.TButton",
                   command=self.load).pack(side="left", padx=10)

        ttk.Label(self, text="Double-click a student (or select and press Space) to toggle "
                             "Present / Absent. New sheets start with everyone Present.",
                  style="Muted.TLabel").pack(anchor="w", pady=(10, 4))

        table_frame, self.tree = make_table(
            self, [("roll_no", "Roll No", 110), ("name", "Name", 300), ("status", "Status", 120)])
        table_frame.pack(fill="both", expand=True)
        self.tree.configure(selectmode="extended")
        self.tree.bind("<Double-1>", self.toggle)
        self.tree.bind("<space>", self.toggle)

        bottom = ttk.Frame(self)
        bottom.pack(fill="x", pady=(8, 0))
        self.summary_var = tk.StringVar(value="Pick a subject and date, then click Load Sheet.")
        ttk.Label(bottom, textvariable=self.summary_var).pack(side="left")
        ttk.Button(bottom, text="Save Attendance", style="Accent.TButton",
                   command=self.save).pack(side="right")
        ttk.Button(bottom, text="Mark All Absent",
                   command=lambda: self.mark_all("A")).pack(side="right", padx=6)
        ttk.Button(bottom, text="Mark All Present",
                   command=lambda: self.mark_all("P")).pack(side="right")

    def refresh(self):
        self.reload_subjects()

    def parse_date(self):
        try:
            day = datetime.strptime(self.date_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the date as YYYY-MM-DD, e.g. 2026-10-27.")
            return None
        if day > date.today():
            messagebox.showerror("Invalid date", "You cannot mark attendance for a future date.")
            return None
        return day.isoformat()

    def load(self):
        subject_id = self.current_subject()
        class_date = self.parse_date()
        if subject_id is None or class_date is None:
            return
        rows = self.db.get_attendance_sheet(subject_id, class_date)
        if not rows:
            messagebox.showwarning("No students", "Add students in the Students tab first.")
            return
        clear_table(self.tree)
        self.statuses = {r["id"]: r["status"] or "P" for r in rows}
        for r in rows:
            self.tree.insert("", "end", iid=r["id"], values=(r["roll_no"], r["name"], ""))
        self.loaded = (subject_id, class_date, self.subject_var.get().split(" - ")[0])
        self.render()

    def render(self):
        for sid, status in self.statuses.items():
            self.tree.set(sid, "status", "Present" if status == "P" else "Absent")
            self.tree.item(sid, tags=("present" if status == "P" else "absent",))
        present = sum(1 for s in self.statuses.values() if s == "P")
        _, class_date, code = self.loaded
        self.summary_var.set(f"{code} on {class_date}   |   Present: {present}   "
                             f"Absent: {len(self.statuses) - present}   "
                             f"Total: {len(self.statuses)}")

    def toggle(self, _event=None):
        for iid in self.tree.selection():
            sid = int(iid)
            self.statuses[sid] = "A" if self.statuses[sid] == "P" else "P"
        if self.statuses:
            self.render()
        return "break"

    def mark_all(self, status):
        if not self.statuses:
            return
        self.statuses = {sid: status for sid in self.statuses}
        self.render()

    def save(self):
        if not self.loaded:
            messagebox.showwarning("Nothing loaded", "Load an attendance sheet first.")
            return
        subject_id, class_date, code = self.loaded
        self.db.save_attendance(subject_id, class_date, self.statuses)
        messagebox.showinfo("Saved", f"Attendance saved for {code} on {class_date}.")


class MarksTab(SubjectPicker, Tab):
    title = "Marks"

    def build(self):
        self.rows = {}
        self.selected_id = None

        bar = ttk.Frame(self)
        bar.pack(fill="x")
        self.build_subject_picker(bar)
        self.subject_box.bind("<<ComboboxSelected>>", lambda _: self.load())
        ttk.Label(bar, text="Internal: out of 40   •   External: out of 60   •   "
                            "Pass mark: 40 / 100", style="Muted.TLabel").pack(side="right")

        table_frame, self.tree = make_table(
            self, [("roll_no", "Roll No", 100), ("name", "Name", 240),
                   ("internal", "Internal", 90), ("external", "External", 90),
                   ("total", "Total", 90), ("grade", "Grade", 80)])
        table_frame.pack(fill="both", expand=True, pady=(10, 0))
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        editor = ttk.LabelFrame(self, text="Enter Marks", padding=10)
        editor.pack(fill="x", pady=(10, 0))
        self.student_var = tk.StringVar(value="Select a student in the table above.")
        ttk.Label(editor, textvariable=self.student_var, width=34).pack(side="left")
        ttk.Label(editor, text="Internal (/40):").pack(side="left", padx=(10, 4))
        self.internal_var = tk.StringVar()
        self.internal_entry = ttk.Entry(editor, textvariable=self.internal_var, width=8)
        self.internal_entry.pack(side="left")
        ttk.Label(editor, text="External (/60):").pack(side="left", padx=(16, 4))
        self.external_var = tk.StringVar()
        external_entry = ttk.Entry(editor, textvariable=self.external_var, width=8)
        external_entry.pack(side="left")
        ttk.Button(editor, text="Save Marks", style="Accent.TButton",
                   command=self.save).pack(side="left", padx=16)
        for entry in (self.internal_entry, external_entry):
            entry.bind("<Return>", lambda _: self.save())

    def refresh(self):
        self.reload_subjects()
        self.load()

    def load(self):
        clear_table(self.tree)
        subject_id = self.subjects.get(self.subject_var.get())
        if subject_id is None:
            return
        self.rows = {r["id"]: r for r in self.db.get_marks_sheet(subject_id)}
        for r in self.rows.values():
            if r["internal"] is None:
                values, tags = (r["roll_no"], r["name"], "-", "-", "-", "-"), ()
            else:
                total = r["internal"] + r["external"]
                grade, _ = grade_for(total)
                values = (r["roll_no"], r["name"], fmt(r["internal"]), fmt(r["external"]),
                          fmt(total), grade)
                tags = ("low",) if grade == "F" else ()
            self.tree.insert("", "end", iid=r["id"], values=values, tags=tags)

    def on_select(self, _event):
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = int(selection[0])
        r = self.rows[self.selected_id]
        self.student_var.set(f"{r['roll_no']} - {r['name']}")
        self.internal_var.set("" if r["internal"] is None else fmt(r["internal"]))
        self.external_var.set("" if r["external"] is None else fmt(r["external"]))
        self.internal_entry.focus_set()

    def save(self):
        subject_id = self.current_subject()
        if subject_id is None:
            return
        if self.selected_id is None:
            messagebox.showwarning("No student", "Select a student in the table first.")
            return
        try:
            internal = float(self.internal_var.get())
            external = float(self.external_var.get())
        except ValueError:
            messagebox.showerror("Invalid marks", "Marks must be numbers.")
            return
        if not (0 <= internal <= 40 and 0 <= external <= 60):
            messagebox.showerror("Invalid marks",
                                 "Internal must be 0-40 and External must be 0-60.")
            return
        self.db.save_marks(self.selected_id, subject_id, internal, external)

        # Reload, then jump to the next student so marks can be entered quickly.
        saved_id = str(self.selected_id)
        self.load()
        items = self.tree.get_children()
        next_index = items.index(saved_id) + 1
        target = items[next_index] if next_index < len(items) else saved_id
        self.tree.selection_set(target)
        self.tree.see(target)


class ReportsTab(Tab):
    title = "Reports"

    def build(self):
        inner = ttk.Notebook(self)
        inner.pack(fill="both", expand=True)

        # --- attendance report
        att = ttk.Frame(inner, padding=8)
        inner.add(att, text="Attendance Report")
        bar = ttk.Frame(att)
        bar.pack(fill="x")
        self.only_low = tk.BooleanVar()
        ttk.Checkbutton(bar, text=f"Show only shortage (below {MIN_ATTENDANCE}%)",
                        variable=self.only_low, command=self.refresh).pack(side="left")
        ttk.Button(bar, text="Export CSV",
                   command=lambda: export_csv(self.att_tree, "attendance_report")
                   ).pack(side="right")
        self.att_count = tk.StringVar()
        ttk.Label(bar, textvariable=self.att_count, style="Muted.TLabel").pack(
            side="right", padx=10)
        frame, self.att_tree = make_table(
            att, [("roll_no", "Roll No", 90), ("name", "Name", 180), ("subject", "Subject", 90),
                  ("total", "Classes", 80), ("present", "Attended", 80),
                  ("percent", "Attendance %", 110), ("status", "Status", 110)])
        frame.pack(fill="both", expand=True, pady=(8, 0))

        # --- results report
        res = ttk.Frame(inner, padding=8)
        inner.add(res, text="Results & CGPA")
        bar = ttk.Frame(res)
        bar.pack(fill="x")
        scale = "   ".join(f"{letter}≥{cutoff}" for cutoff, letter, _ in GRADE_TABLE[:-1])
        ttk.Label(bar, text=f"CGPA = Σ(credits × grade point) ÷ Σ credits      "
                            f"Grades: {scale}   F<40",
                  style="Muted.TLabel").pack(side="left")
        ttk.Button(bar, text="Export CSV",
                   command=lambda: export_csv(self.res_tree, "results_report")
                   ).pack(side="right")
        frame, self.res_tree = make_table(
            res, [("rank", "Rank", 60), ("roll_no", "Roll No", 90), ("name", "Name", 200),
                  ("subjects", "Subjects", 80), ("credits", "Credits", 80),
                  ("cgpa", "CGPA", 80), ("result", "Result", 100)])
        frame.pack(fill="both", expand=True, pady=(8, 0))

    def refresh(self):
        clear_table(self.att_tree)
        shown = 0
        for r in self.db.attendance_report():
            low = r["percent"] < MIN_ATTENDANCE
            if self.only_low.get() and not low:
                continue
            self.att_tree.insert("", "end", values=(
                r["roll_no"], r["name"], r["subject"], r["total"], r["present"],
                f"{r['percent']}%", "Shortage" if low else "Eligible"),
                tags=("low",) if low else ())
            shown += 1
        self.att_count.set(f"{shown} rows")

        clear_table(self.res_tree)
        for rank, r in enumerate(self.db.result_report(), start=1):
            has_marks = r["cgpa"] is not None
            self.res_tree.insert("", "end", values=(
                rank if has_marks else "-", r["roll_no"], r["name"], r["subjects"],
                r["credits"], r["cgpa"] if has_marks else "-", r["result"]),
                tags=("low",) if r["result"] == "Fail" else ())


if __name__ == "__main__":
    App().mainloop()
