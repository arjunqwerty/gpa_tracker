"""Phase 7: many users working at the same moment.

Requests run concurrently on the test client's event loop (the one the database is connected on).
"""
import asyncio

import httpx

from app.main import app
from tests.api.helpers import PASSWORD

GRADES = ["S", "A", "B"]  # 10, 9 and 8 grade points over 3 credits each -> CGPA 9


async def _student(number: int) -> tuple[str, dict, list]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        email = f"student{number}@example.com"
        await client.post("/api/auth/register", json={"full_name": f"S{number}", "email": email, "password": PASSWORD})
        semester = (await client.post("/api/semesters", json={"semester_number": 1, "label": f"Sem of {number}"})).json()
        entries = [{"semester_id": semester["id"], "course_code": f"C{number}{i}", "title": "X", "credits": 3, "grade": grade}
                   for i, grade in enumerate(GRADES)]
        await asyncio.gather(*(client.post("/api/grade-history", json=entry) for entry in entries))
        cgpa = (await client.get("/api/cgpa")).json()
        history = (await client.get("/api/grade-history")).json()
        return email, cgpa, history["items"]


def test_many_students_at_once(client):
    async def everyone():
        return await asyncio.gather(*(_student(number) for number in range(10)))

    for email, cgpa, history in client.portal.call(everyone):
        number = email.removeprefix("student").split("@")[0]
        assert cgpa["confirmed"]["cgpa"] == 9, email
        assert sorted(course["course_code"] for course in history) == [f"C{number}{i}" for i in range(3)]


def test_simultaneous_edits_of_one_grading_scheme(client, db):
    scheme = client.get("/api/grading-schemes").json()[0]
    cookies = dict(client.cookies)

    async def two_tabs():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test", cookies=cookies) as tab:
            edits = [{**scheme, "name": f"Edit {n}"} for n in (1, 2)]
            return await asyncio.gather(*(tab.put(f"/api/grading-schemes/{scheme['id']}", json=edit) for edit in edits))

    codes = sorted(response.status_code for response in client.portal.call(two_tabs))
    assert codes[0] == 200 and codes[1] == 409, codes  # exactly one new version; the other edit is refused
    assert db.grading_schemes.count_documents({"is_archived": False}) == 1
    assert db.grading_schemes.count_documents({}) == 2
