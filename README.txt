LOCAL SKILL DEVELOPMENT AND EMPLOYMENT INFORMATION PORTAL
=========================================================

FEATURES
- Separate Student/Job Seeker and Company/Training Provider registration.
- Secure password hashing and login sessions.
- Browse and search Job, Internship and Training opportunities.
- Filter opportunities by C, C++, Java, Python, JavaScript, HTML, CSS, SQL and other skill categories.
- Company posting form includes a main skill selector and optional additional skills.
- Students and companies use the same login page; the system recognises the account type automatically.
- Company dashboard to publish opportunities.
- Student dashboard to view submitted applications.
- Company dashboard to view applicants.
- SQLite database is created automatically (no MySQL or XAMPP required).

REQUIREMENTS
- Python 3.10 or newer
- VS Code (recommended)

RUN ON WINDOWS
1. Extract this ZIP file.
2. Open the extracted LocalSkillPortal folder in VS Code.
3. Open Terminal > New Terminal.
4. Run:
      py -m venv venv
      .\venv\Scripts\Activate.ps1
      py -m pip install -r requirements.txt
      py app.py
   If PowerShell blocks activation, run:
      Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   Then activate the environment again.
5. Open this address in your browser:
      http://127.0.0.1:5000

FIRST TEST
1. Register as Student / Job seeker.
2. Log out.
3. Register a second account as Company / Training provider.
4. Login as company and select Post opportunity.
5. Publish a Job, Internship or Training.
6. Log out and login as student; open the listing and apply.
7. Check each dashboard.

DATABASE
- portal.db is created in the project folder the first time app.py runs.
- Tables: users, opportunities, applications.
- Keep portal.db safe; it contains your local test data.

IMPORTANT
- This is a student project starter, not production-ready software.
- Before deployment, set a strong secret key using an environment variable,
  add email verification/password reset, validate uploads if added, add CSRF
  protection, HTTPS, rate limiting, and company verification.
- Do not commit real user data or passwords to a public repository.
