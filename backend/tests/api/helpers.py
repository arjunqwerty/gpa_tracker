"""Small builders so tests read as scenarios rather than request plumbing."""

THEORY = [  # Semester 4 "Complex" before the FAT
    {"name": "CAT 1", "maximum_marks": 50, "weightage": 15, "obtained_marks": 36, "status": "completed"},
    {"name": "CAT 2", "maximum_marks": 50, "weightage": 15, "obtained_marks": 46, "status": "completed"},
    {"name": "DA 1", "maximum_marks": 10, "weightage": 10, "obtained_marks": 9, "status": "completed"},
    {"name": "DA 2", "maximum_marks": 10, "weightage": 10, "obtained_marks": 9, "status": "completed"},
    {"name": "DA 3", "maximum_marks": 10, "weightage": 10, "obtained_marks": 9, "status": "completed"},
    {"name": "FAT", "maximum_marks": 100, "weightage": 40},
]


PASSWORD = "correct horse battery"


def ok(response, status=200):
    assert response.status_code == status, response.text
    return response.json() if response.content else None


def register(client, email, name="Student", **fields):
    """Registers and logs `client` in as the new account."""
    client.cookies.clear()
    body = {"full_name": name, "email": email, "password": PASSWORD, **fields}
    return ok(client.post("/api/auth/register", json=body), 201)


def login(client, email, password=PASSWORD):
    client.cookies.clear()
    return ok(client.post("/api/auth/login", json={"email": email, "password": password}))


def create_semester(client, number=1, label=None, **fields):
    body = {"semester_number": number, "label": label or f"Semester {number}", **fields}
    return ok(client.post("/api/semesters", json=body), 201)


def create_course(client, semester_id, code="BMAT101L", credits=3, assessments=(), **fields):
    body = {"semester_id": semester_id, "course_code": code, "title": f"Course {code}", "credits": credits,
            "assessments": list(assessments), **fields}
    return ok(client.post("/api/courses", json=body), 201)


def add_history(client, semester_id, code, grade, credits=3, category="DC", **fields):
    body = {"semester_id": semester_id, "course_code": code, "title": f"Course {code}", "credits": credits,
            "category_code": category, "grade": grade, **fields}
    return ok(client.post("/api/grade-history", json=body), 201)
