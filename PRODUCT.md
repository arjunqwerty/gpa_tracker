# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The owner, a VIT student, tracking their own academic record. A few classmates may later get accounts on the same self-hosted deployment. It is not a public sign-up product.

Typical use is a sit-down session on a laptop: entering assessment marks after a CAT or DA, importing the VTOP grade history, checking credit progress, and planning toward a target CGPA. A phone is secondary, used for occasional quick checks.

## Product Purpose

One place for the whole academic record: every semester, course, assessment mark, official grade, credit and curriculum requirement. It replaces a hand-maintained Excel workbook (`marks.xlsx`) and scattered VTOP pages.

It succeeds when the student trusts it as their record of truth and no longer needs the spreadsheet.

## Positioning

A complete record kept against the student's actual VIT curriculum (2021: 10 credit categories, 65 course templates), where:
- the GPA, CGPA and credits shown always come from the records themselves;
- official results are kept apart from predictions;
- past results are frozen as they were awarded, even if the grading scheme or the curriculum changes later.

VTOP shows results but doesn't plan. A spreadsheet plans, but its formulas drift and break, as the workbook's `#DIV/0!` and its wrong figure for multiple pending assessments showed.

## Operating Context

- **Data sources:** marks come from VIT assessments (CAT 1/2, DAs, FAT, lab components). Official grades come from VTOP.
- **Import:** the VTOP "Grade history" sheet is imported as is. VTOP gives no semester, so courses are grouped into one semester per exam month.
- **Exports:** a PDF summary or semester report, Excel and CSV files, and a full JSON backup. The Excel export can be re-imported.
- **Hosting:** self-hosted with Docker Compose (MongoDB, the FastAPI API, Caddy for HTTPS), with backups from `deploy/backup.sh`.

## Capabilities and Constraints

- **Courses and marks:**
  - Courses can be added by hand or copied from curriculum templates.
  - Each course holds any number of weighted assessments, each pending, completed, absent or exempted.
  - For every grade, the app shows the marks still needed. A simulator tries "what if" marks without saving them.
- **Grades and GPA:**
  - Grades are predicted only when the weightages total exactly 100.
  - An official result is recorded as provisional first, then confirmed, and every change is logged.
  - GPA and CGPA are always shown as both confirmed and predicted. A target-CGPA calculator sits alongside.
- **Credits:** progress by curriculum category, with warnings for courses that have no category or are missing a grade.
- **Grading scheme:** grades S, A, B, C, D, E, F (with grade points) plus P and N. Each user edits their own copy. Every edit creates a new version, and results already recorded keep the version they were graded with.
- **Accounts:** email and password login. Each user's data is fully isolated.
- **Terminology:** CGPA, GPA credits, CAT, DA, FAT, VTOP, curriculum category codes (DC, OE, SPE, …), confirmed / provisional / predicted.
- **Undecided:** the exact D and E grade boundaries (currently D ≥ 55, E ≥ 50, editable) and the remaining academic rules in Plan_v2 section 12.

## Evidence on Hand

- `marks.xlsx`: the owner's reference workbook. It is the validation source for Semesters 4–7 and for the CGPA sheet.
- The owner's real VTOP grade history (65 courses).
- The VIT 2021 curriculum data in `backend/app/seed_vit.json`.
- There are no testimonials, user base or public claims, and none should be invented.

## Product Principles

1. **Never show a misleading number.** Confirmed, provisional and predicted figures stay visibly apart.
2. **The record is the source of truth.** Figures are derived from it, and history is frozen as it was awarded.
3. **Whole record at a glance, detail one click away.** The overview comes first; individual courses and marks are a click deeper.
4. **Built for focused laptop sessions.** Data entry and planning should be quick and calm on a wide screen, and still usable on a phone.
5. **Personal scale.** Favour clarity and correctness over growth features, onboarding funnels or social features.
