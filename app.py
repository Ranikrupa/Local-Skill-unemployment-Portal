from flask import send_from_directory, abort
from flask import Flask, render_template, render_template_string, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
from functools import wraps

import os
import uuid
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "local-skill-portal-secret-key"

UPLOAD_FOLDER = os.path.join(
    app.root_path, "uploads", "resumes"
)

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

ALLOWED_RESUME_EXTENSIONS = {"pdf", "docx"}

# MYSQL DATABASE CONNECTION
def db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="Rani123",
        database="skill_employment_portal"
    )


# DATABASE HELPER FUNCTIONS
def fetch_one(sql, params=()):
    con = db()
    cur = con.cursor(dictionary=True)
    cur.execute(sql, params)
    result = cur.fetchone()
    cur.close()
    con.close()
    return result


def fetch_all(sql, params=()):
    con = db()
    cur = con.cursor(dictionary=True)
    cur.execute(sql, params)
    result = cur.fetchall()
    cur.close()
    con.close()
    return result


def execute(sql, params=()):
    con = db()
    cur = con.cursor()
    cur.execute(sql, params)
    con.commit()
    cur.close()
    con.close()


# CREATE ADDITIONAL PORTAL TABLES
def init_db():
    con = db()
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS opportunities (
            id INT AUTO_INCREMENT PRIMARY KEY,
            company_id INT NOT NULL,
            title VARCHAR(200) NOT NULL,
            kind VARCHAR(30) NOT NULL,
            description TEXT NOT NULL,
            location VARCHAR(150) NOT NULL,
            skills TEXT,
            deadline VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (company_id)
                REFERENCES companies(company_id)
        ) ENGINE=InnoDB
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INT AUTO_INCREMENT PRIMARY KEY,
            opportunity_id INT NOT NULL,
            user_id INT NOT NULL,
            message TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE KEY unique_application (opportunity_id, user_id),
            FOREIGN KEY (opportunity_id)
                REFERENCES opportunities(id),
            FOREIGN KEY (user_id)
                REFERENCES users(user_id)
        ) ENGINE=InnoDB
    """)

    con.commit()
    cur.close()
    con.close()


# LOGIN REQUIRED
def login_required(role=None):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                flash("Please login first.", "warning")
                return redirect(url_for("login"))

            if role and session.get("role") != role:
                flash("Access denied.", "danger")
                return redirect(url_for("index"))

            return fn(*args, **kwargs)

        return wrapper
    return decorator





# HOME PAGE - DISPLAY AND SEARCH OPPORTUNITIES
@app.route("/")
def index():

    kind = request.args.get("kind", "").strip()
    keyword = request.args.get("q", "").strip()
    selected_skill = request.args.get("skill", "").strip()

    # Get available skills from MySQL
    skill_rows = fetch_all("""
        SELECT DISTINCT skills
        FROM opportunities
        WHERE skills IS NOT NULL AND skills != ''
    """)

    skill_options = set()

    for row in skill_rows:
        for skill in row["skills"].split(","):
            skill = skill.strip()
            if skill:
                skill_options.add(skill)

    skill_options = sorted(skill_options)

    # Fetch opportunities from MySQL
    sql = """
        SELECT
            opportunities.*,
            companies.company_name AS company_name
        FROM opportunities
        LEFT JOIN companies
            ON opportunities.company_id = companies.company_id
        WHERE 1=1
    """

    params = []

    # Filter by opportunity type
    if kind in ("Job", "Internship", "Training"):
        sql += " AND opportunities.kind = %s"
        params.append(kind)

    # Search by keyword
    if keyword:
        sql += """
            AND (
                opportunities.title LIKE %s
                OR opportunities.description LIKE %s
                OR opportunities.skills LIKE %s
                OR opportunities.location LIKE %s
                OR companies.company_name LIKE %s
            )
        """

        value = f"%{keyword}%"
        params.extend([value] * 5)

    # Filter by skill
    if selected_skill:
        sql += " AND opportunities.skills LIKE %s"
        params.append(f"%{selected_skill}%")

    sql += " ORDER BY opportunities.created_at DESC"

    opportunities = fetch_all(sql, tuple(params))

    return render_template(
        "index.html",
        opportunities=opportunities,
        skill_options=skill_options
    )




# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = (
            request.form.get("name")
            or request.form.get("company_name", "")
        ).strip()

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "")
        phone = request.form.get("phone", "")

        if not name or not email or len(password) < 6:
            flash("Enter valid details. Password must be at least 6 characters.", "danger")
            return render_template("register.html")

        if role not in ("user", "company"):
            flash("Please select a valid account type.", "danger")
            return render_template("register.html")

        hashed_password = generate_password_hash(password)

        try:
            if role == "user":
                execute("""
                    INSERT INTO users
                    (full_name, email, password, phone)
                    VALUES (%s, %s, %s, %s)
                """, (name, email, hashed_password, phone))

            else:
                execute("""
                    INSERT INTO companies
                    (company_name, email, password, phone)
                    VALUES (%s, %s, %s, %s)
                """, (name, email, hashed_password, phone))

            flash("Registration successful. Please login.", "success")
            return redirect(url_for("login"))

        except mysql.connector.IntegrityError:
            flash("Email already registered.", "danger")

        except mysql.connector.Error as e:
            flash("Database error: " + str(e), "danger")

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        tables = [
            ("users", "user_id", "full_name", "user"),
            ("companies", "company_id", "company_name", "company"),
            ("admin", "admin_id", "admin_name", "admin")
        ]

        for table, id_col, name_col, role in tables:

            user = fetch_one(
                f"SELECT * FROM `{table}` WHERE email = %s",
                (email,)
            )

            if user:
                stored_password = user["password"]

                try:
                    valid = check_password_hash(stored_password, password)
                except (ValueError, TypeError):
                    valid = False

                if valid:
                    session.clear()
                    session["user_id"] = user[id_col]
                    session["name"] = user[name_col]
                    session["role"] = role

                    flash("Login successful!", "success")
                    return redirect(url_for("dashboard"))

        flash("Incorrect email or password.", "danger")

    return render_template("login.html")



# DASHBOARD
@app.route("/dashboard")
@login_required()
def dashboard():

    role = session["role"]

    # ADMIN DASHBOARD
    if role == "admin":

        users = fetch_all(
            "SELECT user_id, full_name, email FROM users"
        )

        companies = fetch_all(
            "SELECT company_id, company_name, email FROM companies"
        )

        opportunities = fetch_all(
            "SELECT * FROM opportunities"
        )

        return render_template_string("""
            <h1>Admin Dashboard</h1>

            <h2>Users</h2>
            {% for u in users %}
                <p>{{ u.full_name }} - {{ u.email }}</p>
            {% endfor %}

            <h2>Companies</h2>
            {% for c in companies %}
                <p>{{ c.company_name }} - {{ c.email }}</p>
            {% endfor %}

            <h2>Opportunities</h2>
            {% for o in opportunities %}
                <p>{{ o.title }}</p>
            {% endfor %}

            <a href="{{ url_for('logout') }}">Logout</a>

        """, users=users, companies=companies,
             opportunities=opportunities)

    # COMPANY DASHBOARD
    elif role == "company":

        opportunities = fetch_all("""
            SELECT *
            FROM opportunities
            WHERE company_id = %s
            ORDER BY created_at DESC
        """, (session["user_id"],))

        applications = fetch_all("""
            SELECT applications.*,
                   users.full_name AS applicant,
                   users.email AS email,
                   opportunities.title
            FROM applications
            JOIN users
                ON users.user_id = applications.user_id
            JOIN opportunities
                ON opportunities.id = applications.opportunity_id
            WHERE opportunities.company_id = %s
            ORDER BY applications.applied_at DESC
        """, (session["user_id"],))

        # LOAD ELIGIBILITY ANSWERS
        for application in applications:

            application["answers"] = fetch_all("""
                SELECT eligibility_questions.question_text,
                       application_answers.answer
                FROM application_answers
                JOIN eligibility_questions
                    ON eligibility_questions.id =
                       application_answers.question_id
                WHERE application_answers.application_id = %s
            """, (application["id"],))

    # STUDENT DASHBOARD
    elif role == "user":

        opportunities = fetch_all("""
            SELECT opportunities.*,
                   companies.company_name
            FROM applications
            JOIN opportunities
                ON opportunities.id = applications.opportunity_id
            JOIN companies
                ON companies.company_id = opportunities.company_id
            WHERE applications.user_id = %s
            ORDER BY applications.applied_at DESC
        """, (session["user_id"],))

        applications = []

    else:
        flash("Invalid account role.", "danger")
        return redirect(url_for("index"))

    return render_template(
        "dashboard.html",
        opportunities=opportunities,
        applications=applications
    )

# POST OPPORTUNITY
@app.route("/post", methods=["GET", "POST"])
@login_required("company")
def post_opportunity():

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        kind = request.form.get("kind", "")
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        main_skill = request.form.get("skills", "").strip()
        extra_skills = request.form.get("extra_skills", "").strip()
        deadline = request.form.get("deadline", "").strip()

        qualification = request.form.get("qualification", "")
        experience = request.form.get("experience", "")
        eligibility = request.form.get("eligibility", "").strip()

        questions = request.form.getlist("question_text[]")
        question_types = request.form.getlist("question_type[]")

        skills = ", ".join(
            value for value in [main_skill, extra_skills] if value
        )

        if not all([title, kind, description, location, main_skill]):
            flash("Please complete all required fields.", "danger")
            return render_template("post.html")

        if kind not in ("Job", "Internship", "Training"):
            flash("Invalid opportunity type.", "danger")
            return render_template("post.html")

        con = db()
        cur = con.cursor()

        try:

            cur.execute("""
                INSERT INTO opportunities
                (
                    company_id, title, kind, description,
                    location, skills, deadline,
                    qualification, experience, eligibility
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                session["user_id"],
                title,
                kind,
                description,
                location,
                skills,
                deadline or None,
                qualification,
                experience,
                eligibility
            ))

            opportunity_id = cur.lastrowid

            for question, question_type in zip(
                questions, question_types
            ):

                question = question.strip()

                if question:
                    if question_type not in ("text", "textarea"):
                        question_type = "text"

                    cur.execute("""
                        INSERT INTO eligibility_questions
                        (opportunity_id, question_text, question_type)
                        VALUES (%s, %s, %s)
                    """, (
                        opportunity_id,
                        question,
                        question_type
                    ))

            con.commit()

            flash("Opportunity and eligibility questions published successfully!", "success")

            return redirect(url_for("dashboard"))

        except mysql.connector.Error as e:

            con.rollback()
            flash("Database error: " + str(e), "danger")

        finally:
            cur.close()
            con.close()

    return render_template("post.html")



# APPLY FOR OPPORTUNITY
@app.route("/apply/<int:opportunity_id>", methods=["POST"])
@login_required("user")
def apply(opportunity_id):

    opportunity = fetch_one(
        "SELECT id, kind FROM opportunities WHERE id = %s",
        (opportunity_id,)
    )

    if not opportunity:
        flash("Opportunity not found.", "danger")
        return redirect(url_for("index"))

    applicant_name = request.form.get("applicant_name", "").strip()
    email = request.form.get("email", "").strip().lower()
    phone = request.form.get("phone", "").strip()
    education = request.form.get("education", "").strip()
    college = request.form.get("college", "").strip()
    experience = request.form.get("applicant_experience", "").strip()
    message = request.form.get("message", "").strip()

    if not all([
        applicant_name, email, phone, education, experience
    ]):
        flash("Please complete all required applicant details.", "danger")
        return redirect(url_for("opportunity_detail", opportunity_id=opportunity_id))

    # RESUME VALIDATION
    resume = request.files.get("resume")
    resume_path = None

    if opportunity["kind"] in ("Job", "Internship"):
        if not resume or not resume.filename:
            flash("Resume is required for jobs and internships.", "danger")
            return redirect(url_for("opportunity_detail", opportunity_id=opportunity_id))

    if resume and resume.filename:

        filename = secure_filename(resume.filename)
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

        if extension not in ALLOWED_RESUME_EXTENSIONS:
            flash("Only PDF and DOCX resumes are allowed.", "danger")
            return redirect(url_for("opportunity_detail", opportunity_id=opportunity_id))

        unique_filename = f"{uuid.uuid4().hex}.{extension}"

        resume_path = unique_filename

    # GET COMPANY QUESTIONS
    questions = fetch_all("""
        SELECT id
        FROM eligibility_questions
        WHERE opportunity_id = %s
    """, (opportunity_id,))

    answers = []

    for question in questions:

        answer = request.form.get(
            f"answer_{question['id']}", ""
        ).strip()

        if not answer:
            flash("Please answer all eligibility questions.", "danger")
            return redirect(url_for("opportunity_detail", opportunity_id=opportunity_id))

        answers.append((question["id"], answer))

    # SAVE APPLICATION AND ANSWERS
    con = db()
    cur = con.cursor()

    try:

        if resume_path:
            resume.save(
                os.path.join(
                    app.config["UPLOAD_FOLDER"],
                    resume_path
                )
            )

        cur.execute("""
            INSERT INTO applications
            (
                opportunity_id,
                user_id,
                message,
                applicant_name,
                email,
                phone,
                education,
                college,
                applicant_experience,
                resume_path
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            opportunity_id,
            session["user_id"],
            message,
            applicant_name,
            email,
            phone,
            education,
            college,
            experience,
            resume_path
        ))

        application_id = cur.lastrowid

        for question_id, answer in answers:

            cur.execute("""
                INSERT INTO application_answers
                (application_id, question_id, answer)
                VALUES (%s, %s, %s)
            """, (
                application_id,
                question_id,
                answer
            ))

        con.commit()

        flash("Your application was submitted successfully!", "success")

        return redirect(url_for("index"))

    except mysql.connector.IntegrityError:

        con.rollback()

        if resume_path:
            path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                resume_path
            )
            if os.path.exists(path):
                os.remove(path)

        flash("You have already applied for this opportunity.", "warning")

    except mysql.connector.Error as e:

        con.rollback()

        if resume_path:
            path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                resume_path
            )
            if os.path.exists(path):
                os.remove(path)

        flash("Application database error: " + str(e), "danger")

    finally:
        cur.close()
        con.close()

    return redirect(url_for(
        "opportunity_detail",
        opportunity_id=opportunity_id
    ))


# OPPORTUNITY DETAILS
@app.route("/opportunity/<int:opportunity_id>")
def opportunity_detail(opportunity_id):

    item = fetch_one("""
        SELECT opportunities.*,
               companies.company_name,
               companies.email
        FROM opportunities
        JOIN companies
        ON companies.company_id = opportunities.company_id
        WHERE opportunities.id = %s
    """, (opportunity_id,))

    if not item:
        flash("Opportunity not found.", "danger")
        return redirect(url_for("index"))

    questions = fetch_all("""
        SELECT id, question_text, question_type
        FROM eligibility_questions
        WHERE opportunity_id = %s
        ORDER BY id
    """, (opportunity_id,))

    return render_template(
        "detail.html",
        item=item,
        questions=questions
    )



# LOGOUT
@app.route("/logout")
def logout():

    session.clear()
    flash("You have logged out.", "success")

    return redirect(url_for("index"))


# RUN APPLICATION
if __name__ == "__main__":

    try:
        init_db()
        print("MySQL Database Connected Successfully!")
        app.run(debug=True)

    except mysql.connector.Error as e:
        print("MySQL Connection Error:", e)

        