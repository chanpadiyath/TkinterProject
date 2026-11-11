# Smart Attendance & Grade Tracker
A desktop app made with **Python Tkinter + SQLite** for managing students, subjects,
daily attendance, marks, grades and CGPA.

## How to run
```
cd ~/Desktop/APP/TkinterProject
python3 app.py
```
Login: **admin / admin123**

No libraries need to be installed: `tkinter`, `sqlite3`, `csv`, `hashlib` all come with Python.
On the first run the app creates `tracker.db` and fills it with demo data
(12 students, 4 subjects, 24 days of attendance, marks).
**To start fresh, delete `tracker.db`.**

## Features
| Tab | What it does |
|-----|--------------|
| Login | Username/password check; the password is stored as a SHA-256 hash |
| Dashboard | Summary cards (students, subjects, average attendance, students below 75%, topper) and a bar chart of attendance per subject drawn on a `Canvas` |
| Students | Add / Update / Delete / Clear, live search, validation (10-digit phone, email format, semester 1-8, unique roll no) |
| Subjects | Add / Update / Delete subjects with code, name and credits |
| Attendance | Pick a subject and date, load the sheet, double-click to toggle Present/Absent, Mark All, then Save. Future dates are blocked; saved sheets can be reopened and edited |
| Marks | Internal (/40) and External (/60) marks; total and grade are calculated automatically; after saving, it jumps to the next student |
| Reports | Attendance % per student per subject (shortage below 75% highlighted in red, filter option), Results & CGPA ranking, Export to CSV |

## Project structure
```
TkinterProject/
├── app.py        GUI: all windows, tabs and widgets (Tkinter / ttk)
├── database.py   Data layer: every SQL query, grade logic, demo data
├── tracker.db    SQLite database (created automatically)
└── README.md
```

## Database design (5 tables)
- **users**(username PK, password)
- **students**(id PK, roll_no UNIQUE, name, dept, semester, phone, email)
- **subjects**(id PK, code UNIQUE, name, credits)
- **attendance**(student_id FK, subject_id FK, class_date, status 'P'/'A') with PK = (student, subject, date)
- **marks**(student_id FK, subject_id FK, internal, external) with PK = (student, subject)

The foreign keys use `ON DELETE CASCADE`, so deleting a student also deletes their attendance and marks.

## Grading
| Total (/100) | ≥90 | ≥80 | ≥70 | ≥60 | ≥50 | ≥40 | <40 |
|---|---|---|---|---|---|---|---|
| Grade | O | A+ | A | B+ | B | C | F |
| Point | 10 | 9 | 8 | 7 | 6 | 5 | 0 |

**CGPA = Σ(credits × grade point) ÷ Σ(credits)**. One F means the result is Fail.

---

## Viva questions & answers

**1. What is Tkinter?**
Python's standard GUI library. It wraps the Tcl/Tk toolkit. `ttk` (themed Tk) gives better-looking widgets such as `Treeview`, `Notebook` and `Combobox`.

**2. Which widgets did you use?**
`Tk` (main window), `Frame`, `Label`, `Entry`, `Button`, `Combobox`, `Spinbox`, `Checkbutton`,
`Treeview` (tables), `Notebook` (tabs), `LabelFrame`, `Scrollbar`, `Canvas` (chart),
`messagebox` and `filedialog`.

**3. What is `mainloop()`?**
It starts the event loop. The program waits for events (clicks, key presses) and calls the matching handler functions. Without it the window would close immediately.

**4. What geometry managers did you use?**
`pack()` for the overall layout (side by side, top to bottom) and `grid()` for forms (rows and columns). You should not mix both in the same parent container.

**5. What is `StringVar`?**
A Tkinter variable linked to a widget. When the variable changes, the widget updates, and the other way round. I used `trace_add("write", ...)` on the search box to filter the table live while typing.

**6. How does event binding work?**
`widget.bind("<Event>", function)`. For example `<Double-1>` toggles attendance, `<Return>` logs in, `<<TreeviewSelect>>` fills the form when a row is clicked, and `<<NotebookTabChanged>>` refreshes a tab when it is opened.

**7. Why SQLite?**
It is serverless and stores the whole database in one file. It is built into Python (`sqlite3`) and needs no setup, which makes it ideal for a desktop app.

**8. How do you prevent SQL injection?**
I use parameterised queries with `?` placeholders, for example `execute("... WHERE id = ?", (id,))`. I never build SQL by joining strings with user input.

**9. Why are passwords hashed?**
If someone opens the database file they only see a SHA-256 hash, not the real password. At login the typed password is hashed and compared with the stored hash.

**10. Where did you use OOP?**
Every tab is a class that inherits from a base `Tab` class (`build()` + `refresh()`).
`StudentsTab` and `SubjectsTab` both inherit from `CrudTab`, which holds the shared form and table logic, so the code is not repeated (**inheritance and reuse**).
`SubjectPicker` is a mixin used by both the Attendance and Marks tabs. `Database` wraps all the data operations (**encapsulation**).

**11. Why are the GUI and the database in separate files?**
Separation of concerns: `app.py` handles only display and input, and `database.py` handles only data. Either one can be changed without breaking the other.

**12. What does `INSERT OR REPLACE` do?**
If a row with the same primary key already exists, it is replaced. Re-saving attendance for the same date, or marks for the same subject, therefore updates the record instead of creating duplicates.

**13. What is a `LEFT JOIN`, and where did you use it?**
It returns every row from the left table even when there is no match on the right. The attendance sheet uses `students LEFT JOIN attendance`, so every student appears even before attendance has been marked (their status is NULL).

**14. What validation did you add?**
Required fields, a unique roll number and subject code (caught as `sqlite3.IntegrityError`), 10-digit phone, email checked with a regex, semester 1-8, credits 1-6, marks within 0-40 and 0-60, date format YYYY-MM-DD, and no future dates.

**15. How is the chart made without matplotlib?**
On a `Canvas` using `create_rectangle` (bars), `create_line` (grid lines and the dashed 75% line) and `create_text` (labels). Green bars are at or above 75% and red bars are below. It redraws on `<Configure>`, so it resizes with the window.

**16. How does CSV export work?**
`filedialog.asksaveasfilename()` asks where to save, then `csv.writer` writes the table headings and every row in the `Treeview`.

**17. Future improvements?**
Multiple user roles (teacher/admin), automatic SMS or email to students with low attendance, PDF report cards, a semester-wise CGPA history, and face-recognition attendance.
