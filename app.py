import os
import re
import sqlite3
import uuid
from math import sqrt
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "skill_intelligence.db")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = "ai-workforce-skill-intelligence-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

SKILLS = [
    "Python", "Java", "SQL", "HTML", "CSS", "JavaScript", "React", "Power BI",
    "Data Analysis", "Machine Learning", "Communication", "Git"
]

ROLE_TARGETS = {
    "Software Developer": {"Python": 65, "Java": 60, "SQL": 55, "HTML": 45, "CSS": 45, "JavaScript": 60, "Git": 55, "Communication": 50},
    "Web Developer": {"HTML": 70, "CSS": 65, "JavaScript": 70, "React": 55, "SQL": 45, "Git": 50, "Communication": 50},
    "Data Analyst": {"Python": 60, "SQL": 70, "Power BI": 70, "Data Analysis": 75, "Communication": 60, "Git": 35},
    "AI/ML Engineer": {"Python": 80, "SQL": 50, "Data Analysis": 70, "Machine Learning": 80, "Git": 60, "Communication": 55},
    "Student / Fresher": {"Python": 45, "Java": 45, "SQL": 45, "HTML": 45, "CSS": 40, "JavaScript": 40, "Communication": 55, "Git": 35}
}

TRAINING = {
    "Python": ("Python Programming", "Learn Python fundamentals, functions, OOP and projects."),
    "Java": ("Java Development", "Practice Java syntax, OOP, collections and application development."),
    "SQL": ("SQL & Database Basics", "Learn queries, joins, subqueries, normalization and database design."),
    "HTML": ("Modern HTML", "Build structured, accessible web pages."),
    "CSS": ("CSS & Responsive Design", "Create responsive and attractive interfaces."),
    "JavaScript": ("JavaScript Essentials", "Learn DOM, events, APIs and modern JavaScript."),
    "React": ("React Fundamentals", "Build component-based user interfaces."),
    "Power BI": ("Power BI Analytics", "Create dashboards, reports and data models."),
    "Data Analysis": ("Data Analysis", "Learn data cleaning, visualization and analytical thinking."),
    "Machine Learning": ("Machine Learning Basics", "Understand supervised learning, features and model evaluation."),
    "Communication": ("Professional Communication", "Improve workplace communication, presentations and interviews."),
    "Git": ("Git & GitHub", "Learn version control, branching and collaboration.")
}

DEMAND_HISTORY = {
    "Python": [58, 64, 70, 77, 84],
    "JavaScript": [52, 57, 63, 69, 76],
    "SQL": [61, 65, 69, 73, 78],
    "Data Analysis": [46, 52, 59, 67, 75],
    "Machine Learning": [40, 47, 56, 66, 78],
    "Power BI": [35, 43, 51, 61, 72],
    "Cloud": [44, 51, 59, 68, 79],
    "Cybersecurity": [42, 48, 55, 64, 74],
    "React": [39, 46, 54, 62, 70],
    "Git": [50, 55, 60, 66, 73]
}

KEYWORD_ALIASES = {
    "python": "Python", "java": "Java", "sql": "SQL", "html": "HTML", "html5": "HTML",
    "css": "CSS", "css3": "CSS", "javascript": "JavaScript", "js": "JavaScript", "react": "React",
    "power bi": "Power BI", "powerbi": "Power BI", "data analysis": "Data Analysis",
    "machine learning": "Machine Learning", "ml": "Machine Learning", "communication": "Communication",
    "git": "Git", "github": "Git"
}

ALLOWED_EXTENSIONS = {"txt", "pdf"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS employee_profiles (
        user_id INTEGER PRIMARY KEY,
        role TEXT DEFAULT 'Student / Fresher',
        department TEXT DEFAULT 'Computer Applications',
        experience REAL DEFAULT 0,
        resume_filename TEXT DEFAULT '',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS user_skills (
        user_id INTEGER NOT NULL,
        skill TEXT NOT NULL,
        level INTEGER DEFAULT 0 CHECK(level >= 0 AND level <= 100),
        source TEXT DEFAULT 'profile',
        PRIMARY KEY(user_id, skill),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        readiness REAL DEFAULT 0,
        gap_count INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS training_resources (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        skill TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS future_skill_demand (
        skill TEXT PRIMARY KEY,
        y2022 INTEGER, y2023 INTEGER, y2024 INTEGER, y2025 INTEGER, y2026 INTEGER
    );
    """)

    count = conn.execute("SELECT COUNT(*) AS c FROM training_resources").fetchone()["c"]
    if count == 0:
        for skill, (title, desc) in TRAINING.items():
            conn.execute("INSERT INTO training_resources(skill,title,description) VALUES(?,?,?)", (skill, title, desc))

    for skill, values in DEMAND_HISTORY.items():
        conn.execute("INSERT OR IGNORE INTO future_skill_demand(skill,y2022,y2023,y2024,y2025,y2026) VALUES(?,?,?,?,?,?)", (skill, *values))
    conn.commit()
    conn.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    conn.close()
    return user


def profile_data(user_id):
    conn = get_db()
    profile = conn.execute("SELECT * FROM employee_profiles WHERE user_id=?", (user_id,)).fetchone()
    rows = conn.execute("SELECT skill, level FROM user_skills WHERE user_id=?", (user_id,)).fetchall()
    skills = {r["skill"]: r["level"] for r in rows}
    conn.close()
    return profile, skills


def get_targets(role):
    return ROLE_TARGETS.get(role, ROLE_TARGETS["Student / Fresher"])


def linear_predict(values):
    n = len(values)
    xs = list(range(1, n + 1))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    den = sum((x - mean_x) ** 2 for x in xs) or 1
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values)) / den
    intercept = mean_y - slope * mean_x
    return max(0, min(100, round(intercept + slope * (n + 1))))


def parse_resume_text(text):
    found = set()
    lowered = text.lower()
    for alias, canonical in sorted(KEYWORD_ALIASES.items(), key=lambda item: -len(item[0])):
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", lowered):
            found.add(canonical)
    return sorted(found)


def extract_pdf_text(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def get_user_skill_levels(user_id):
    _, skills = profile_data(user_id)
    return {skill: int(skills.get(skill, 0)) for skill in SKILLS}


def compute_analysis(user_id):
    profile, skills = profile_data(user_id)
    role = profile["role"] if profile else "Student / Fresher"
    targets = get_targets(role)
    gaps = []
    matched = []
    for skill, target in targets.items():
        current = int(skills.get(skill, 0))
        diff = max(0, target - current)
        item = {"skill": skill, "current": current, "required": target, "gap": diff}
        (gaps if diff > 0 else matched).append(item)
    total_required = sum(targets.values()) or 1
    total_current = sum(min(int(skills.get(s, 0)), t) for s, t in targets.items())
    readiness = round((total_current / total_required) * 100)
    gaps.sort(key=lambda x: x["gap"], reverse=True)
    return profile, readiness, gaps, matched


def latest_assessment(user_id, readiness, gaps):
    conn = get_db()
    conn.execute("INSERT INTO assessments(user_id,readiness,gap_count) VALUES(?,?,?)", (user_id, readiness, len(gaps)))
    conn.commit()
    conn.close()


@app.context_processor
def inject_user():
    return {"logged_user": current_user()}


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if not name or not email or not password:
            flash("Please fill all required fields.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must contain at least 6 characters.", "error")
            return render_template("register.html")
        conn = get_db()
        try:
            cur = conn.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)", (name, email, generate_password_hash(password)))
            user_id = cur.lastrowid
            conn.execute("INSERT INTO employee_profiles(user_id) VALUES(?)", (user_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            flash("Email already registered. Please login.", "error")
            return render_template("register.html")
        conn.close()
        session["user_id"] = user_id
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    profile, skills = profile_data(user["id"])
    _, readiness, gaps, matched = compute_analysis(user["id"])
    top_skills = sorted(((k, int(v)) for k, v in skills.items()), key=lambda x: x[1], reverse=True)[:5]
    return render_template("dashboard.html", profile=profile, readiness=readiness, gaps=gaps[:5], matched=matched, top_skills=top_skills)


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        role = request.form.get("role", "Student / Fresher")
        department = request.form.get("department", "Computer Applications").strip()
        try:
            experience = max(0, float(request.form.get("experience", 0)))
        except ValueError:
            experience = 0
        conn = get_db()
        conn.execute("UPDATE users SET name=? WHERE id=?", (name or user["name"], user["id"]))
        conn.execute("UPDATE employee_profiles SET role=?,department=?,experience=? WHERE user_id=?", (role, department, experience, user["id"]))
        for skill in SKILLS:
            try:
                level = int(request.form.get("skill_" + re.sub(r"[^a-zA-Z0-9]", "_", skill), 0))
            except ValueError:
                level = 0
            level = max(0, min(100, level))
            conn.execute("INSERT INTO user_skills(user_id,skill,level,source) VALUES(?,?,?,?) ON CONFLICT(user_id,skill) DO UPDATE SET level=excluded.level,source=excluded.source", (user["id"], skill, level, "profile"))
        conn.commit()
        conn.close()
        flash("Profile and skill details saved.", "success")
        return redirect(url_for("profile"))
    profile_row, skills = profile_data(user["id"])
    return render_template("profile.html", profile=profile_row, skills=skills, skill_list=SKILLS, roles=list(ROLE_TARGETS.keys()))


@app.route("/resume", methods=["GET", "POST"])
@login_required
def resume():
    user = current_user()
    extracted = []
    if request.method == "POST":
        file = request.files.get("resume")
        if not file or not file.filename:
            flash("Select a TXT or PDF resume.", "error")
            return redirect(url_for("resume"))
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            flash("Only TXT and PDF files are supported in this version.", "error")
            return redirect(url_for("resume"))
        safe_name = secure_filename(file.filename)
        unique_name = f"{uuid.uuid4().hex}_{safe_name}"
        path = os.path.join(UPLOAD_DIR, unique_name)
        file.save(path)
        if ext == "txt":
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        else:
            text = extract_pdf_text(path)
        extracted = parse_resume_text(text)
        conn = get_db()
        conn.execute("UPDATE employee_profiles SET resume_filename=? WHERE user_id=?", (safe_name, user["id"]))
        for skill in extracted:
            conn.execute("INSERT INTO user_skills(user_id,skill,level,source) VALUES(?,?,?,?) ON CONFLICT(user_id,skill) DO UPDATE SET source='resume'", (user["id"], skill, 60, "resume"))
        conn.commit()
        conn.close()
        if extracted:
            flash("Resume processed and skills were added to your profile.", "success")
        else:
            flash("Resume uploaded, but no supported skill keywords were detected. Add skills manually in Profile.", "error")
    profile_row, skills = profile_data(user["id"])
    return render_template("resume.html", profile=profile_row, extracted=extracted, skills=skills)


@app.route("/analysis")
@login_required
def analysis():
    user = current_user()
    profile, readiness, gaps, matched = compute_analysis(user["id"])
    latest_assessment(user["id"], readiness, gaps)
    return render_template("analysis.html", profile=profile, readiness=readiness, gaps=gaps, matched=matched)


@app.route("/future")
@login_required
def future():
    conn = get_db()
    rows = conn.execute("SELECT * FROM future_skill_demand").fetchall()
    conn.close()
    predictions = []
    for row in rows:
        values = [row[f"y{year}"] for year in range(2022, 2027)]
        predictions.append({"skill": row["skill"], "history": values, "prediction": linear_predict(values), "growth": round(linear_predict(values) - values[-1])})
    predictions.sort(key=lambda x: x["prediction"], reverse=True)
    return render_template("future.html", predictions=predictions)


@app.route("/recommendations")
@login_required
def recommendations():
    user = current_user()
    profile, readiness, gaps, _ = compute_analysis(user["id"])
    gap_skills = {item["skill"] for item in gaps}
    conn = get_db()
    resources = conn.execute("SELECT * FROM training_resources").fetchall()
    conn.close()
    result = [r for r in resources if r["skill"] in gap_skills]
    return render_template("recommendations.html", profile=profile, readiness=readiness, gaps=gaps, resources=result)


@app.route("/matching")
@login_required
def matching():
    user = current_user()
    conn = get_db()
    others = conn.execute("SELECT u.id,u.name,u.email,p.role,p.department FROM users u JOIN employee_profiles p ON p.user_id=u.id WHERE u.id<>? ORDER BY u.name", (user["id"],)).fetchall()
    all_skills = {uid: get_user_skill_levels(uid) for uid in [r["id"] for r in others]}
    mine = get_user_skill_levels(user["id"])
    matches = []
    def similarity(a, b):
        keys = SKILLS
        dot = sum(a[k] * b[k] for k in keys)
        na = sqrt(sum(a[k] ** 2 for k in keys))
        nb = sqrt(sum(b[k] ** 2 for k in keys))
        return 0 if na == 0 or nb == 0 else round((dot / (na * nb)) * 100)
    for row in others:
        matches.append({"name": row["name"], "email": row["email"], "role": row["role"], "department": row["department"], "compatibility": similarity(mine, all_skills[row["id"]])})
    matches.sort(key=lambda x: x["compatibility"], reverse=True)
    return render_template("matching.html", matches=matches, total=len(others))


@app.errorhandler(413)
def too_large(_):
    flash("File is too large. Maximum size is 5 MB.", "error")
    return redirect(url_for("resume"))


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "app": "AI Workforce Skill Intelligence"})


if __name__ == "__main__":
    init_db()
    app.run(debug=True, host="127.0.0.1", port=5000)
