AI-POWERED WORKFORCE SKILL INTELLIGENCE AND FUTURE SKILL DEMAND PREDICTION SYSTEM

FRESH WORKING VERSION

1. Open PowerShell in this folder.
2. Activate your existing venv, or create one:
   python -m venv venv
   .\venv\Scripts\Activate.ps1
3. Install packages:
   pip install -r requirements.txt
4. Start the server:
   python app.py
5. Open Chrome:
   http://127.0.0.1:5000/

IMPORTANT:
- Do NOT open HTML files directly using file:///.
- All pages are served by Flask, so navigation works through one server.
- Database is SQLite (skill_intelligence.db), created automatically.
- Each registered user has separate profile/skill data.
- Resume upload supports TXT and PDF. PDF skill extraction uses pypdf.
- Future skill prediction uses a simple linear trend calculation over built-in demand history.

MAIN FLOW:
Home -> Register -> Dashboard -> Profile -> Resume -> Skill Analysis -> Future Demand -> Recommendations -> Employee Matching

The app contains no fixed employee profile; registered users create their own data.
