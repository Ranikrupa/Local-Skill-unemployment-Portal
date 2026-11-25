
import mysql.connector
from werkzeug.security import generate_password_hash

# DATABASE CONNECTION
con = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Rani123",
    database="skill_employment_portal"
)

cur = con.cursor()

# DEMO COMPANIES
companies = [
    ("Infosys Demo", "infosys.demo@example.com", "9876500001"),
    ("TCS Demo", "tcs.demo@example.com", "9876500002"),
    ("Wipro Demo", "wipro.demo@example.com", "9876500003"),
    ("Accenture Demo", "accenture.demo@example.com", "9876500004"),
    ("Capgemini Demo", "capgemini.demo@example.com", "9876500005")
]

# SAME DEMO PASSWORD FOR THESE SAMPLE ACCOUNTS
demo_password = generate_password_hash("Demo@123")

company_ids = {}

# INSERT COMPANIES
for name, email, phone in companies:

    cur.execute(
        "SELECT company_id FROM companies WHERE email = %s",
        (email,)
    )

    existing = cur.fetchone()

    if existing:
        company_id = existing[0]
        print(name, "already exists")

    else:
        cur.execute("""
            INSERT INTO companies
            (company_name, email, password, phone)
            VALUES (%s, %s, %s, %s)
        """, (name, email, demo_password, phone))

        company_id = cur.lastrowid
        print(name, "added successfully")

    company_ids[name] = company_id


# SAMPLE OPPORTUNITIES
opportunities = [
    (
        "Infosys Demo",
        "Python Developer",
        "Job",
        "Sample opening for Python development and database skills.",
        "Bengaluru",
        "Python, Flask, MySQL"
    ),
    (
        "Infosys Demo",
        "Web Development Intern",
        "Internship",
        "Sample internship for students interested in web development.",
        "Mysuru",
        "HTML, CSS, JavaScript"
    ),
    (
        "TCS Demo",
        "Java Developer",
        "Job",
        "Sample Java development opportunity for graduates.",
        "Bengaluru",
        "Java, SQL, Spring Boot"
    ),
    (
        "TCS Demo",
        "Data Analytics Training",
        "Training",
        "Sample training program covering data analysis fundamentals.",
        "Online",
        "Python, Excel, SQL"
    ),
    (
        "Wipro Demo",
        "Software Testing Intern",
        "Internship",
        "Sample internship in software testing.",
        "Hyderabad",
        "Testing, Java, Selenium"
    ),
    (
        "Accenture Demo",
        "Data Analyst",
        "Job",
        "Sample opportunity in data analytics.",
        "Pune",
        "Python, SQL, Excel"
    ),
    (
        "Capgemini Demo",
        "Full Stack Development Training",
        "Training",
        "Sample full stack development training program.",
        "Online",
        "HTML, CSS, JavaScript, Python"
    )
]


# INSERT OPPORTUNITIES
for company, title, kind, description, location, skills in opportunities:

    company_id = company_ids[company]

    cur.execute("""
        SELECT id FROM opportunities
        WHERE company_id = %s AND title = %s
    """, (company_id, title))

    if cur.fetchone():
        print(title, "already exists")
        continue

    cur.execute("""
        INSERT INTO opportunities
        (
            company_id, title, kind, description,
            location, skills
        )
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (
        company_id,
        title,
        kind,
        description,
        location,
        skills
    ))

    print(title, "added successfully")


con.commit()

cur.close()
con.close()

print("\nAll demo companies and opportunities processed!")
