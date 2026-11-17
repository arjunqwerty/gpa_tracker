# VIT CGPA Tracker

Track assessment marks, see what you need in each exam for every grade, and follow your
semester GPA, CGPA and curriculum credits, with confirmed results kept apart from predictions.

The specification is in [docs/Plan_v2.md](docs/Plan_v2.md). All seven phases are built: the core
product (1–5), accounts with login (6), and production deployment with backups (7).

## Running it

You need MongoDB running as a **replica set** (some saves use transactions) and Node 20.19+.

```bash
# 1. Backend (http://127.0.0.1:8000, API docs at /docs)
cd backend
workon gpa_tracker                 # the project's virtualenv
pip install -r requirements.txt
uvicorn app.main:app --reload

# 2. Frontend (http://localhost:5173), in a second terminal
cd frontend
npm install
npm run dev
```

**Using it from other devices on your network** (phone, another laptop): the dev server already
listens on your network. Open `http://<this machine's IP>:5173` (the address Vite prints as
"Network"). Only the frontend is exposed; it forwards `/api` to the backend, which stays private
on `127.0.0.1:8000`. If a firewall is on, allow port 5173 (`sudo ufw allow 5173/tcp`). For
password-reset links to work from other devices, start the backend with
`GPA_TRACKER_APP_URL=http://<this machine's IP>:5173`.

On every start the backend adds any missing VIT reference data from `app/seed_vit.json`: the
programme, the 2021 curriculum (10 credit categories plus 65 course templates), the course
types and the VIT grading scheme. To seed without starting the API: `python -m app.seed`.

Open the app and **register**. Each new account starts on the VIT curriculum with its own
editable copy of the VIT grading scheme. If the database still has data from before accounts
existed (the old "local user"), the first person to register is offered to keep it.

To bring in your existing record, open **Import & export** and upload a workbook that
contains the **Grade history** sheet copied from VTOP.

| Environment variable                 | Default                     | Purpose |
|--------------------------------------|-----------------------------|---------|
| `GPA_TRACKER_MONGO_URL`              | `mongodb://localhost:27017` | |
| `GPA_TRACKER_DB`                     | `gpa_tracker`               | |
| `GPA_TRACKER_SECRET_KEY`             | random on every start       | signs login tokens; set it in production |
| `GPA_TRACKER_COOKIE_SECURE`          | `false`                     | `true` when served over HTTPS |
| `GPA_TRACKER_APP_URL`                | `http://localhost:5173`     | used in password-reset links |
| `GPA_TRACKER_SMTP_HOST` (+ `_PORT`, `_USER`, `_PASSWORD`, `GPA_TRACKER_MAIL_FROM`) | unset | sends reset emails; when unset the link is written to the backend log |
| `GPA_TRACKER_AUTH_ATTEMPTS_PER_MINUTE` | `10`                      | login / register / reset attempts per address and endpoint |

## Accounts and login

- Passwords are hashed with Argon2id. Logging in sets two httpOnly, SameSite=Strict cookies:
  a 15-minute access token (JWT) and a 30-day refresh token that the browser swaps for a new
  pair automatically. Each refresh token works once; a stolen one being replayed ends every
  session of that user.
- Every endpoint except `/api/auth/*` needs a logged-in user, and every query is filtered by
  that user's id (`ownership.py`). `tests/api/test_isolation.py` tries every endpoint as a
  second user against the first user's data, and fails if anything is returned or changed.
- Settings → Account changes the email or password, or deletes the account with all its data.
- Forgot password emails a one-hour, single-use link (or logs it when no SMTP is configured).

## Deploying (Docker)

`docker-compose.yml` runs MongoDB (a single-node replica set, initialised on first boot), the
API, and Caddy, which serves the built frontend and gets an HTTPS certificate on its own.

```bash
cp .env.example .env               # set SITE_ADDRESS and GPA_TRACKER_SECRET_KEY (and SMTP for reset emails)
docker compose up -d --build       # then open https://<SITE_ADDRESS>
```

MongoDB is not published outside the compose network. Uploads are capped at 5 MB, and Caddy
adds the security headers (HSTS, CSP, no framing). Configuration: `deploy/Caddyfile`.

## Backups

```bash
deploy/backup.sh                   # dump to backups/<db>-<date>.archive.gz, keeping the newest 14
deploy/restore.sh FILE             # put a backup back (asks before replacing live data)
deploy/restore.sh FILE other_db    # restore into another database instead
deploy/restore_drill.sh            # back up, restore into a scratch database, compare, clean up
```

Prefix any of them with `IN_DOCKER=1` for the Docker deployment, and schedule the backup with
cron, e.g. `0 3 * * * cd /path/to/VIT_GPA_Tracker && IN_DOCKER=1 deploy/backup.sh`. Copy the
`backups/` folder off the machine as well.

## Tests

```bash
cd backend && python -m pytest        # engine, API, login, isolation and concurrency tests (needs MongoDB; uses gpa_tracker_test)
cd frontend && npm run build          # type-checks the frontend
```

The engine tests check results against the reference workbook (Semesters 4–7, the CGPA
sheet, the target-CGPA formula). They also check two places where the workbook was wrong:
`#DIV/0!` when no credits remain, and required marks when several assessments are pending.

## Where things are

```
backend/app/
  engine/            Pure calculations: no database, Decimal only. Start here for any maths question.
    marks.py           weighted marks, required marks per grade, projected and predicted grade
    gpa.py             grade points, semester GPA, CGPA, target CGPA
    credits.py         earned / remaining credits, progress per category
  models/            MongoDB documents (Beanie). One file per area; ALL_DOCUMENTS lists every collection.
  routers/           HTTP endpoints, one file per area (auth, courses, results, calculations, imports, ...)
  services/
    calculations.py    loads a user's record and runs the engine over it
    excel_import.py    Excel preview + commit, and the sheet / column layout
    exports.py         Excel, CSV and PDF files
  ownership.py       get_current_user() and the user_id checks every route uses
  security.py        passwords, login tokens, auth cookies, login rate limit
  database.py        MongoDB connection and transaction() helper
  seed.py            reference data from seed_vit.json, and the starting setup of a new account
backend/tests/       engine/ (pure maths) and api/ (against a real MongoDB)
deploy/              Caddyfile and the backup / restore scripts; docker-compose.yml is in the project root

frontend/src/
  api.ts             fetch helpers: useApi() to load data, useAction() for saves; renews the login
  auth.tsx           who is logged in: AuthProvider and useAuth()
  types.ts           the JSON shapes the backend returns
  components/        shared UI: ui.tsx (cards, buttons, ...), forms, charts.tsx
  pages/             one file per screen (AuthPages.tsx: log in, register, password reset);
                     course/ holds the course screen's parts
```

## How the data fits together

- **Courses hold everything about a course.** A course document contains its assessments
  and, once declared, its `official_result`. Grade history is simply every course that has
  an official result, so the same completion can never be recorded twice.
- **Official results are snapshots.** Credits, category, GPA eligibility and the grading
  scheme version are copied into the result when it is recorded, so editing the course,
  the curriculum or the grading scheme later never changes past results.
- **Results go provisional, then confirmed.** Confirmed GPA/CGPA use confirmed results
  only. Predicted figures use the best grade known for each course: its official result
  if it has one, otherwise the grade predicted from its marks.
- **Editing a grading scheme creates a new version.** Courses still in progress move to
  the new version; recorded results keep the version they were graded with.
- **Nothing calculated is stored.** GPA, CGPA and credit totals are worked out from the
  records on every request.
- **Every document carries `user_id`, and every query filters on it** (see `ownership.py`).
  Shared reference data (the VIT curriculum, course types) has `user_id: null` and is read-only.

## Academic rules (configurable or easy to change)

| Rule | Where |
|---|---|
| Pending assessments add nothing (they are not zero); absent ones count as zero | `engine/marks.py` |
| An exempted assessment's weightage is spread over the remaining assessments | `engine/marks.py` |
| Grades are predicted only when the weightages total exactly 100 | `engine/marks.py` |
| Projected marks assume the pending assessments are scored at your current rate | `engine/marks.py` |
| Rounding marks before grading | Settings → "Round total marks…" |
| Grade boundaries, grade points, passing grades | Settings → grading scheme |
| A repeated course (higher `attempt`) replaces earlier attempts in the CGPA | `services/calculations.py` |
| Grades without a minimum mark (P, N) are awarded only by hand; on import they count as non-GPA | grading scheme / `excel_import.py` |
