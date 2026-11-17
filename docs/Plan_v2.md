# VIT CGPA Tracker
## Functional Requirements & Database Design

**Document Version:** 2.0
**Status:** Revised Technical Specification
**Supersedes:** `Initial_plan.md` (v1.0)
**Application Type:** Academic Performance Tracking Platform (single-user first, multi-user in final phase)

### Changes from v1.0

| Area | v1.0 | v2.0 |
|---|---|---|
| Database | PostgreSQL (relational, RLS) | **MongoDB** (document model, repository-layer ownership scoping) |
| Authentication | Phase 2 | **Final feature phase (Phase 6)**; core product runs in single-user mode first |
| Grade history | Separate `academic_history` table | View over `courses` with an official result (no duplicates by design) |
| Calculated results | `semester_results` table | Computed on read; optional `calculation_snapshots` cache |
| ODM / ORM | SQLAlchemy | Beanie (Pydantic-based async ODM) |

---

# 1. Project Overview

## 1.1 Objective

Develop a web-based application that allows individual students to track their academic performance, calculate expected grades, monitor semester GPA and cumulative CGPA, and maintain curriculum credit completion.

The existing Excel workbook serves as the reference for the initial calculation engine and functional behaviour.

The core product is built first in **single-user mode**. The data model is multi-user from day one (every user-owned document carries a `userId`), so that authentication and multiple independent accounts can be enabled in the final phase without data migration.

## 1.2 Core Objectives

1. Track marks obtained in individual assessments.
2. Calculate weighted marks and remaining marks required for target grades.
3. Predict course grades and corresponding grade points.
4. Calculate semester GPA and cumulative CGPA.
5. Maintain semester-wise academic records.
6. Track completed and remaining curriculum credits.
7. Maintain grade history.
8. Generate academic performance analytics and graphs.
9. Support configurable grading schemes.
10. Support reusable course and curriculum templates.
11. Provide secure, isolated user accounts (final phase).

## 1.3 Design Principles

- Configurable instead of hardcoded academic rules.
- Dynamic assessment structures.
- Independent calculation engine.
- Separation of predicted and confirmed results.
- Single source of truth for academic records.
- Automatic recalculation when relevant data changes.
- Historical data preservation (snapshot official results).
- Ownership-ready data model: every user-owned document is scoped by `userId`, enforced in the repository layer.
- Core product before accounts: authentication must be addable without restructuring data.

---

# 2. Functional Requirements

## FR-01: Single-User Mode (Pre-Authentication)

Until authentication is delivered (Phase 6), the application runs for a single local user.

### FR-01.1 Local User
- On first start, the application seeds one **local user** document (`isLocal: true`, no email or password).
- All academic data created in this mode is owned by the local user via `userId`.

### FR-01.2 Current-User Resolution
- Every API route resolves the acting user through a single `get_current_user()` dependency.
- In single-user mode it returns the local user. In Phase 6 it is replaced with session/JWT resolution. No route, repository or data change is required for the switch.

### FR-01.3 User Profile

Store and allow editing of:
- Name
- University
- Programme
- Curriculum version
- Specialisation
- Admission year
- Expected graduation year

Email and password are not required in single-user mode.

### FR-01.4 Upgrade Path
When authentication is enabled, the first registered account claims the existing local user's data by setting `email` and `passwordHash` on that same user document (no data copy).

---

## FR-02: Academic Configuration

The application must support different academic programmes and grading configurations.

### FR-02.1 Academic Programme

A programme represents a degree or academic course.

Examples:
- B.Tech Computer Science
- B.Tech Computer Science – AI and Robotics
- B.Tech Information Technology

Attributes:
- Programme name
- University
- Degree type
- Programme duration
- Curriculum version
- Total required credits

### FR-02.2 Semester Management

Users must be able to:
- Create semesters.
- Edit semester details.
- Set academic year.
- Set semester number.
- Mark a semester as active, completed or planned.
- View semester-specific GPA.

Semester types must support regular semesters, summer terms and other academic periods.

### FR-02.3 Grading Configuration

Grading schemes must be configurable.

A grading scheme contains:

| Attribute | Description |
|---|---|
| Scheme name | Name of grading system |
| Grade label | S, A, B, C, D, E |
| Grade point | 10, 9, 8, 7, 6, 5 |
| Minimum marks | Lower grade boundary |
| Maximum marks | Upper grade boundary |
| Display order | Grade ordering |
| Passing status | Whether the grade is passing |

Example configuration:

| Grade | Grade point |
|---|---:|
| S | 10 |
| A | 9 |
| B | 8 |
| C | 7 |
| D | 6 |
| E | 5 |

The numerical grade boundaries must be configured independently.

The application must not assume that every institution uses the same boundaries.

Grading schemes must be versioned so that historical results remain unchanged when a scheme is modified. Editing a scheme creates a new version; previous versions are never mutated.

---

## FR-03: Curriculum and Course Management

### FR-03.1 Course Creation Methods

Support two methods.

**Method A – Template-based creation**

Users can select an existing academic programme or curriculum template.

The application imports:
- Course code
- Course name
- Course type
- Credits
- Curriculum category
- Default assessment structure, if available

Imported courses become individual student course documents (copied, not linked).

**Method B – Manual creation**

Users can create their own courses.

Fields:
- Course code
- Course title
- Course type
- Credits
- Curriculum category
- Semester
- GPA contribution eligibility
- Credit completion eligibility

### FR-03.2 Course Types

Course types must be configurable.

Examples from the workbook include:
- TH – Theory
- LO – Laboratory
- SS – Soft Skills
- ETL – Elective Theory/Laboratory
- OC – Other course
- ECA – Extra-curricular activity
- PJT – Project

The application must not restrict users to these values.

### FR-03.3 Course Categories

Examples from the workbook:

- Basic Sciences and Mathematics
- Basic Engineering Sciences
- Humanities, Social Sciences and Management
- Discipline-linked Engineering Sciences
- Discipline Core
- Projects and Internship
- Open Elective
- Non-graded Core Requirement
- Bridge Course
- Specialisation Elective

Categories must be configurable per curriculum.

### FR-03.4 Course Management

Users must be able to:
- Add courses.
- Edit courses.
- Delete courses before results are finalized.
- Assign courses to semesters.
- Change credits when permitted.
- Assign curriculum categories.
- Duplicate a course configuration.
- Import courses from a template.

Historical records must not be silently changed when a course is edited. Official results store a snapshot of credits, category and grading scheme version at the time of confirmation.

---

## FR-04: Assessment Management

This is one of the most important modules.

The application must support a completely dynamic assessment structure.

### FR-04.1 Assessment Creation

Each course can contain any number of assessments.

Examples:

Theory:
- CAT 1
- CAT 2
- DA 1
- DA 2
- DA 3
- Quiz
- FAT

Laboratory:
- Assessment 1
- Assessment 2
- IPS
- PAT
- FAT Lab

Project:
- Review 0
- Review 1
- Review 2
- Review 3
- Project Report

NPTEL:
- Assignments
- Final assessment

These are examples, not predefined mandatory assessment types.

### FR-04.2 Assessment Attributes

Each assessment must contain:

| Field | Description |
|---|---|
| Assessment name | CAT 1, FAT, Review 1, etc. |
| Maximum marks | Maximum achievable marks |
| Weightage | Contribution to final course marks |
| Obtained marks | Student's marks |
| Status | Pending, completed, absent or exempted |
| Assessment date | Optional |
| Sequence | Display order |

### FR-04.3 Assessment Validation

- Maximum marks must be greater than zero.
- Obtained marks cannot exceed maximum marks unless explicitly configured otherwise.
- Weightages must be non-negative.
- Assessment weightages must normally total 100.
- Incomplete assessment structures must be allowed during setup.
- The application must identify incomplete configurations (surfaced as warnings, not write rejections).

### FR-04.4 Assessment Status

Support:
- Pending
- Completed
- Absent
- Exempted

Pending assessments must not be treated as zero marks.

---

## FR-05: Marks Calculation Engine

### FR-05.1 Weighted Marks

For every assessment:

Weighted Marks = (Obtained Marks / Maximum Marks) × Weightage

Total Weighted Marks = Sum of all completed assessment contributions.

Example:

| Assessment | Maximum | Weightage | Obtained |
|---|---:|---:|---:|
| CAT 1 | 50 | 15 | 36 |
| CAT 2 | 50 | 15 | 46 |
| DA 1 | 10 | 10 | 9 |
| DA 2 | 10 | 10 | 9 |
| DA 3 | 10 | 10 | 9 |
| FAT | 100 | 40 | 64 |

The engine must support fractional marks.

### FR-05.2 Required Marks for Target Grades

For an incomplete final assessment:

Required Marks = ((Target Marks - Existing Weighted Marks) × Assessment Maximum Marks) / Assessment Weightage

The application must calculate this for every configured grade boundary.

Example:
- Existing weighted marks: 77.2
- FAT maximum: 100
- FAT weightage: 40
- Target grade boundary: 90

Required FAT marks = 32.

### FR-05.3 Target Status

Every target grade must have one of the following statuses:

- Already achieved.
- Achievable.
- Not achievable.
- Pending configuration.

Negative required marks must be displayed as already achieved, not as an actual negative exam requirement.

If the required marks exceed the assessment maximum, the target must be marked not achievable.

### FR-05.4 Multiple Pending Assessments

The calculation engine must also support more than one pending assessment.

It must calculate:
- Current weighted marks.
- Maximum possible final marks.
- Minimum marks required across the remaining assessments.
- Whether each grade remains achievable.

The user must be able to simulate possible future assessment marks without permanently modifying actual marks. Simulation is stateless: hypothetical marks are passed in the request and never persisted.

---

## FR-06: Grade Prediction

The application must calculate a predicted grade based on the configured grading scheme.

Predicted Grade = Grade corresponding to projected final weighted marks.

The system must support:
- Current predicted grade.
- Projected grade after hypothetical marks.
- Predicted grade point.
- Grade improvement analysis.
- Target grade comparison.

Predicted results are computed on read and are never written into a course's official result.

An incomplete course must not be treated as an officially completed course.

---

## FR-07: Course GPA Contribution

For every GPA-eligible course:

Course Grade Points = Course Credits × Grade Point

Example:

Course credits = 4
Grade point = 9

Course Grade Points = 36.

The application must maintain this contribution separately for each course.

Non-GPA courses must be excluded from the GPA calculation according to the academic rules.

---

## FR-08: Semester GPA

Semester GPA = Sum(Course Credits × Grade Points) / Sum(GPA-eligible Course Credits)

The application must display:

- Total semester credits.
- GPA-contributing credits.
- Total weighted grade points.
- Semester GPA.
- Predicted semester GPA.
- Confirmed semester GPA.

The calculation must be updated whenever an eligible course's official grade changes.

Predicted and confirmed semester GPAs must remain distinguishable.

---

## FR-09: CGPA

CGPA must be calculated using cumulative credit-weighted GPA.

CGPA = Sum(Semester Grade Points) / Sum(Semester GPA Credits)

Equivalent:

CGPA = Sum(Semester GPA × Semester GPA Credits) / Sum(Semester GPA Credits)

The application must support:

- Current CGPA.
- Semester-wise CGPA progression.
- Total GPA-contributing credits.
- Total accumulated grade points.
- Predicted CGPA.
- Confirmed CGPA.
- Target CGPA calculations.

### Target CGPA

Required future GPA = ((Target CGPA × Total Future Credits) - Existing Grade Points) / Remaining Future Credits

The application must identify when a target CGPA is impossible or already achieved.

The denominator must be checked before performing the calculation.

---

## FR-10: Credit Tracking

### FR-10.1 Curriculum Credit Requirements

Each curriculum contains credit requirements by category.

Example:

| Category | Required credits |
|---|---:|
| Basic Sciences and Mathematics | 24 |
| Basic Engineering Sciences | 16 |
| Humanities, Social Sciences and Management | 15 |
| Discipline-linked Engineering Sciences | 12 |
| Discipline Core | 44 |
| Projects and Internship | 9 |
| Open Elective | 9 |
| Non-graded Core Requirement | 11 |
| Bridge Course | 0 |
| Specialisation Elective | 21 |

These are reference values from the workbook, not universal programme requirements.

### FR-10.2 Credit Status

Every course must have configurable credit treatment:

- Counts towards graduation requirements.
- Counts towards GPA.
- Counts towards earned credits.
- Counts towards a particular curriculum category.

This avoids assuming that all earned credits contribute to CGPA.

### FR-10.3 Credit Calculations

Earned Credits = Sum of eligible completed course credits.

Remaining Credits = Required Credits - Earned Credits.

Completion Percentage = Earned Credits / Required Credits × 100.

### FR-10.4 Credit Dashboard

Display:

- Total required credits.
- Total completed credits.
- Total remaining credits.
- GPA-contributing credits.
- Non-GPA credits.
- Category-wise progress.
- Semester-wise credit distribution.

If earned credits exceed required credits, the application should show the surplus rather than silently cap the stored total.

### FR-10.5 Credit Validation

The system must detect:
- Missing category assignments.
- Courses counted in multiple incompatible categories.
- Completed courses missing official grades.
- Credits exceeding curriculum requirements.
- Differences between earned credits and GPA-contributing credits.

---

## FR-11: Grade History

Grade history is a **view over course documents that carry an official result**. There is no separate history store, so manual and automatically generated entries cannot produce duplicate course completions.

### FR-11.1 Manual Entry

Users can add historical academic records. A manual entry creates a course document with `source: "manual"`, no assessments, and an official result.

Fields:
- Course code
- Course title
- Course type
- Credits
- Final grade
- Grade point
- Semester
- Exam month
- Result declaration date
- Curriculum category

### FR-11.2 Automatic Generation

When a tracked course receives a final grade, the application records an official result on that course (status `provisional`).

The user must be able to review and confirm the result (status `confirmed`).

### FR-11.3 History Management

- View all completed courses.
- Filter by semester.
- Filter by grade.
- Filter by course type.
- Filter by curriculum category.
- Search by course code/title.
- View historical GPA contribution.

A user cannot hold two official results for the same course code and attempt number (enforced by a unique index).

---

## FR-12: Analytics Dashboard

The dashboard must provide:

### Academic Summary
- Current CGPA.
- Latest semester GPA.
- Total completed credits.
- Remaining credits.
- Overall curriculum completion.

### GPA Analytics
- Semester-wise GPA graph.
- Semester-wise CGPA progression.
- Target CGPA comparison.
- GPA improvement analysis.

### Grade Analytics
- Grade distribution.
- Grade distribution by course category.
- Grade distribution by course type.
- Grade history.

### Credit Analytics
- Completed versus required credits.
- Category-wise progress.
- Semester-wise credits.
- GPA-contributing versus non-GPA credits.

All analytics must be generated from the underlying academic records, not separately maintained values.

---

## FR-13: Import and Export

### Import
Support importing academic information from Excel.

Initial import functionality should support:
- Semester information.
- Course details.
- Assessment configurations.
- Obtained marks.
- Grade history.
- Curriculum credit requirements.

Import must include a preview and validation stage. Nothing is written to academic collections until the user commits the import.

### Export
Support:
- Academic summary PDF.
- Grade history CSV/Excel.
- Semester report.
- Credit completion report.
- Full user data export (JSON).

---

## FR-14: User Accounts & Authentication (Final Phase)

Delivered in Phase 6, after the core product is complete.

### FR-14.1 Registration
Users must be able to register using:
- Name
- Email address
- Password

Email addresses must be unique.

### FR-14.2 Authentication
- Login and logout.
- Secure password hashing (Argon2id).
- Session/token management (short-lived access token + rotating refresh token).
- Password reset.
- Account management.

### FR-14.3 User Data Isolation

Every student's academic data must belong to their account.

A user must never be able to retrieve or modify another user's:
- Courses
- Marks
- Assessments
- Grades
- GPA
- CGPA
- Credit progress
- Academic history

### FR-14.4 Local Data Claim
The first account registered on an instance that has local-mode data is offered the option to claim it (see FR-01.4).

---

# 3. Calculation Engine Specification

The calculation engine must be a separate module with no database dependency. It accepts plain input models and returns results, so it can be tested in isolation and reused by the API, import validation and simulation.

## 3.1 Core Calculation Functions

1. calculate_assessment_weighted_marks()
2. calculate_course_total()
3. calculate_required_marks()
4. calculate_maximum_possible_marks()
5. predict_course_grade()
6. calculate_course_grade_points()
7. calculate_semester_gpa()
8. calculate_cumulative_cgpa()
9. calculate_target_cgpa()
10. calculate_earned_credits()
11. calculate_remaining_credits()
12. calculate_credit_completion_percentage()

## 3.2 Calculation Rules

- Use decimal arithmetic rather than binary floating-point arithmetic.
- Numeric values are stored in MongoDB as BSON `Decimal128` and converted to Python `Decimal` at the model boundary. `float` is never used for marks, credits or grade points.
- Do not round intermediate values.
- Apply rounding only for presentation or explicitly configured academic rules.
- Preserve original marks and weightages.
- Recalculate dependent values after relevant changes.
- Never overwrite official results with predictions.
- Exclude pending assessments from actual weighted marks.
- Validate the total assessment weightage before final calculation.
- Every result carries an `engineVersion` so cached snapshots can be invalidated when the engine changes.

## 3.3 Source Workbook Compatibility

The calculation engine must initially reproduce the logic used in the later semester sheets.

Reference formula:

Weighted Mark = Scored × Weightage / Maximum Mark

Required FAT Mark = (Grade Threshold - Existing Weighted Marks) × FAT Maximum / FAT Weightage

Semester GPA = Sum(Course Credits × Grade Points) / Sum(Course Credits)

CGPA = Sum(Semester GPA × Semester Credits) / Sum(Semester Credits)

The workbook's actual formula errors must not be copied into the new implementation.

---

# 4. Database Design (MongoDB)

Database: **MongoDB 7+**, deployed as a replica set (a single-node replica set in development) so that multi-document transactions are available.

## 4.1 Modelling Principles

- **Embed** data that is bounded in size and always read with its parent: assessments in a course, grade entries in a grading scheme, categories / requirements / templates in a curriculum version, profile in a user.
- **Reference** data that is shared or queried independently: semesters, courses, grading schemes, curricula.
- **Snapshot, don't reference, for history.** An official result copies the grade, grade point, grading scheme id and version, credits, category and GPA eligibility at the time it is recorded. Later edits to schemes, templates or the course never change it.
- **Derived values are not a source of truth.** GPA, CGPA and credit totals are computed by the engine on read. `calculation_snapshots` is an optional cache and audit trail.
- All identifiers are `ObjectId`. Every collection has `createdAt` and `updatedAt`.
- Every user-owned collection has a `userId` field, and every index on it is prefixed with `userId`.
- Field names use camelCase.

## 4.2 Collection Overview

| # | Collection | Ownership | Purpose |
|---|---|---|---|
| 1 | users | self | Account, embedded profile and settings |
| 2 | universities | shared | Reference data |
| 3 | programmes | shared | Reference data |
| 4 | curriculum_versions | shared or user | Categories, credit requirements, course templates |
| 5 | course_types | shared or user | TH, LO, SS, … |
| 6 | grading_schemes | user (or shared default) | Versioned grade scales |
| 7 | semesters | user | Academic periods |
| 8 | courses | user | Course, embedded assessments, embedded official result |
| 9 | calculation_snapshots | user | Optional cache / audit of computed results |
| 10 | import_jobs | user | Excel import preview and validation |
| 11 | audit_log | user | Changes to official academic records |
| 12 | refresh_tokens | user | Phase 6 only |
| 13 | password_reset_tokens | user | Phase 6 only |

## 4.3 Collection Definitions

### users

```js
{
  _id: ObjectId,
  email: String | null,          // null until Phase 6
  passwordHash: String | null,   // null until Phase 6
  isActive: Boolean,
  isLocal: Boolean,              // true for the single-user-mode account
  profile: {
    fullName: String,
    universityId: ObjectId | null,
    programmeId: ObjectId | null,
    curriculumVersionId: ObjectId | null,
    specialisation: String | null,
    admissionYear: Int | null,
    graduationYear: Int | null
  },
  settings: {
    defaultGradingSchemeId: ObjectId | null,
    roundingMode: "none" | "half_up" | "half_even",
    displayDecimals: Int
  },
  createdAt: Date,
  updatedAt: Date
}
```

Indexes:
- `{ email: 1 }` unique, partial filter `{ email: { $type: "string" } }`

### universities

```js
{ _id, name: String, shortName: String, createdAt, updatedAt }
```

Indexes: `{ shortName: 1 }` unique.

### programmes

```js
{
  _id, universityId: ObjectId,
  name: String, degreeType: String, durationSemesters: Int,
  createdAt, updatedAt
}
```

Indexes: `{ universityId: 1, name: 1 }` unique.

### curriculum_versions

Merges v1 `curriculum_versions`, `credit_categories`, `curriculum_requirements` and `course_templates`.

```js
{
  _id: ObjectId,
  programmeId: ObjectId,
  ownerUserId: ObjectId | null,      // null = shared template
  versionName: String,
  effectiveYear: Int,
  totalRequiredCredits: Decimal128,
  isActive: Boolean,
  categories: [
    { code: String, name: String, requiredCredits: Decimal128 }
  ],
  courseTemplates: [
    {
      templateId: ObjectId,
      courseCode: String,
      title: String,
      courseTypeCode: String,
      credits: Decimal128,
      categoryCode: String,
      countsTowardsGpa: Boolean,
      countsTowardsEarnedCredits: Boolean,
      countsTowardsRequirement: Boolean,
      defaultAssessments: [
        { name: String, maximumMarks: Decimal128, weightage: Decimal128, sequence: Int }
      ]
    }
  ],
  createdAt, updatedAt
}
```

Indexes:
- `{ programmeId: 1, versionName: 1, ownerUserId: 1 }` unique
- `{ "courseTemplates.courseCode": 1 }`

A curriculum holds roughly 60–100 templates, far below MongoDB's 16 MB document limit.

### course_types

```js
{ _id, userId: ObjectId | null, code: String, name: String, createdAt, updatedAt }
```

`userId: null` marks shared types. Seeded with TH, LO, SS, ETL, OC, ECA, PJT.

Indexes: `{ userId: 1, code: 1 }` unique.

### grading_schemes

Merges v1 `grading_schemes` and `grade_scale_entries`. Documents are **immutable once used**: editing creates a new document with `version + 1` and archives the previous one.

```js
{
  _id: ObjectId,
  userId: ObjectId | null,           // null = shared default (e.g. VIT)
  schemeKey: String,                 // stable across versions
  name: String,
  version: Int,
  isDefault: Boolean,
  isArchived: Boolean,
  entries: [
    {
      grade: String,                 // "S", "A", ...
      gradePoint: Decimal128,
      minimumMarks: Decimal128,
      maximumMarks: Decimal128,
      isPassing: Boolean,
      displayOrder: Int
    }
  ],
  createdAt, updatedAt
}
```

Indexes: `{ userId: 1, schemeKey: 1, version: -1 }` unique.

Validation: entries must not overlap, must be ordered by `displayOrder`, and `gradePoint` values must be unique within a version.

### semesters

```js
{
  _id: ObjectId,
  userId: ObjectId,
  curriculumVersionId: ObjectId | null,
  semesterNumber: Int,
  label: String,                     // e.g. "Fall 2025-26"
  academicYear: String,              // e.g. "2025-26"
  semesterType: "regular" | "summer" | "other",
  status: "planned" | "active" | "completed",
  gradingSchemeId: ObjectId,         // default scheme for courses in this semester
  createdAt, updatedAt
}
```

Indexes: `{ userId: 1, semesterNumber: 1, semesterType: 1 }`.

### courses

Merges v1 `student_courses`, `course_assessments`, `course_grades` and `academic_history`.

```js
{
  _id: ObjectId,
  userId: ObjectId,
  semesterId: ObjectId,
  templateRef: { curriculumVersionId: ObjectId, templateId: ObjectId } | null,

  courseCode: String,
  title: String,
  courseTypeCode: String,
  credits: Decimal128,
  categoryCode: String | null,

  countsTowardsGpa: Boolean,
  countsTowardsEarnedCredits: Boolean,
  countsTowardsRequirement: Boolean,

  status: "planned" | "in_progress" | "completed" | "failed" | "withdrawn",
  source: "manual" | "template" | "import",
  gradingSchemeId: ObjectId,

  assessments: [
    {
      _id: ObjectId,
      name: String,
      maximumMarks: Decimal128,
      weightage: Decimal128,
      obtainedMarks: Decimal128 | null,
      status: "pending" | "completed" | "absent" | "exempted",
      allowOverMax: Boolean,
      sequence: Int,
      assessmentDate: Date | null
    }
  ],

  officialResult: null | {
    grade: String,
    gradePoint: Decimal128,
    resultStatus: "provisional" | "confirmed",
    gradingSchemeId: ObjectId,       // snapshot
    gradingSchemeVersion: Int,       // snapshot
    creditsAtResult: Decimal128,     // snapshot
    categoryAtResult: String | null, // snapshot
    gpaEligibleAtResult: Boolean,    // snapshot
    examMonth: Date | null,
    resultDate: Date | null,
    source: "manual" | "import" | "generated",
    confirmedAt: Date | null
  },

  attempt: Int,                      // 1 by default; >1 for repeats
  supersedesCourseId: ObjectId | null,

  createdAt, updatedAt
}
```

Indexes:
- `{ userId: 1, semesterId: 1 }`
- `{ userId: 1, "officialResult.resultStatus": 1 }` (grade history)
- `{ userId: 1, courseCode: 1, attempt: 1 }` unique, partial filter `{ officialResult: { $type: "object" } }` (no duplicate official completions)
- `{ userId: 1, courseCode: "text", title: "text" }` (history search)

Rules:
- Predictions are never stored on a course. They are computed on read and by the stateless simulate endpoint.
- Grade history is `courses.find({ userId, officialResult: { $ne: null } })`.
- A course with a confirmed official result cannot be deleted, and changes to its credits or category do not alter the snapshot.
- Repeat attempts (Outstanding Decision 7) are modelled with `attempt` and `supersedesCourseId`; the engine decides whether a superseded attempt counts in CGPA based on configuration.

### calculation_snapshots

Replaces v1 `semester_results` and `calculation_snapshots`. Optional cache and audit trail; never the source of truth.

```js
{
  _id: ObjectId,
  userId: ObjectId,
  scope: "course" | "semester" | "cgpa" | "credits",
  semesterId: ObjectId | null,
  courseId: ObjectId | null,
  resultType: "predicted" | "confirmed",
  engineVersion: String,
  inputsHash: String,                // hash of the inputs used; mismatch = stale
  result: Object,
  createdAt: Date
}
```

Indexes: `{ userId: 1, scope: 1, semesterId: 1, createdAt: -1 }`.

### import_jobs

```js
{
  _id: ObjectId,
  userId: ObjectId,
  filename: String,
  status: "pending" | "validated" | "committed" | "failed",
  parsedPreview: Object,
  validationReport: { errors: [Object], warnings: [Object] },
  createdAt: Date,
  committedAt: Date | null
}
```

Indexes: `{ userId: 1, createdAt: -1 }`; TTL index on `createdAt` (7 days) with partial filter `{ status: { $ne: "committed" } }`.

### audit_log

```js
{
  _id: ObjectId,
  userId: ObjectId,
  entity: "course" | "grading_scheme" | "semester",
  entityId: ObjectId,
  action: "create" | "update" | "delete" | "confirm_result",
  before: Object | null,
  after: Object | null,
  at: Date
}
```

Indexes: `{ userId: 1, entity: 1, entityId: 1, at: -1 }`.

### refresh_tokens (Phase 6)

```js
{ _id, userId, tokenHash: String, expiresAt: Date, revokedAt: Date | null, createdAt }
```

Indexes: `{ tokenHash: 1 }` unique; TTL on `expiresAt`.

### password_reset_tokens (Phase 6)

```js
{ _id, userId, tokenHash: String, expiresAt: Date, usedAt: Date | null }
```

Indexes: `{ tokenHash: 1 }` unique; TTL on `expiresAt`.

## 4.4 Mapping from v1 Tables

| v1.0 table(s) | v2.0 collection |
|---|---|
| users, user_profiles | `users` (profile embedded) |
| universities | `universities` |
| academic_programmes | `programmes` |
| curriculum_versions, credit_categories, curriculum_requirements, course_templates | `curriculum_versions` (embedded arrays) |
| course_types | `course_types` |
| grading_schemes, grade_scale_entries | `grading_schemes` (embedded entries, versioned documents) |
| semesters | `semesters` |
| student_courses, course_assessments, course_grades, academic_history | `courses` (embedded assessments and official-result snapshot) |
| semester_results, calculation_snapshots | `calculation_snapshots` (cache only) |
| import_jobs | `import_jobs` |
| — | `audit_log`, `refresh_tokens`, `password_reset_tokens` (new) |

---

# 5. Data Relationships

- One user embeds one profile and one settings object.
- One university has many programmes (reference).
- One programme has many curriculum versions (reference).
- One curriculum version embeds its categories, credit requirements and course templates.
- One grading scheme version embeds its grade entries.
- One user has many semesters (reference by `userId`).
- One semester has many courses (reference by `semesterId`).
- One course embeds zero or more assessments.
- One course embeds zero or one official result.
- One user has many calculation snapshots, import jobs and audit entries.

Course templates are reusable reference data. Courses are copied from templates (or created manually); changing a template never modifies existing courses.

---

# 6. Data Integrity and Constraints

MongoDB has no foreign keys or row-level security, so integrity is enforced in layers.

1. **Unique indexes** (Section 4.3): unique email; unique scheme versions; no duplicate official course completions; unique course types per owner.
2. **Model validation** with Pydantic (via Beanie) on every write:
   - Credits ≥ 0.
   - Maximum marks > 0.
   - 0 ≤ obtained marks ≤ maximum marks, unless `allowOverMax` is true.
   - Weightage ≥ 0.
   - Semester number ≥ 1.
   - Official grade and grade point must match an entry in the referenced grading scheme version.
3. **Collection validators** (`$jsonSchema`) on `courses`, `semesters` and `grading_schemes` as a second line of defence for required fields and types.
4. **Ownership scoping** (replaces RLS):
   - All data access goes through a repository layer. Every query, update and delete on a user-owned collection must include `userId`; routes never touch collections directly.
   - Cross-reference checks in the service layer: a course's `semesterId` must belong to the same user; a referenced grading scheme or curriculum must be owned by the user or shared.
   - An isolation test suite verifies that no endpoint can read or change another user's documents.
5. **Transactions**: multi-document transactions are used for recording/confirming an official result (course update + audit entry + snapshot invalidation) and for committing an import.
6. **Weightage totals**: a total other than 100 is reported as a configuration warning by the engine, not rejected on write, so incomplete structures can be saved during setup.
7. **Historical immutability**: official-result snapshots and used grading scheme versions are never updated in place.

---

# 7. API Structure

REST API. Every route resolves the acting user with `Depends(get_current_user)` from the start (local user until Phase 6).

## Profile
- GET /api/profile
- PUT /api/profile

## Academic Configuration
- GET /api/universities
- GET /api/programmes
- POST /api/programmes
- GET /api/curricula
- GET /api/curricula/{id}
- POST /api/curricula
- GET /api/course-types
- POST /api/course-types
- GET /api/grading-schemes
- POST /api/grading-schemes
- PUT /api/grading-schemes/{id} (creates a new version)

## Semesters
- GET /api/semesters
- POST /api/semesters
- GET /api/semesters/{id}
- PUT /api/semesters/{id}
- DELETE /api/semesters/{id}

## Courses
- GET /api/courses
- POST /api/courses
- POST /api/courses/from-template
- POST /api/courses/{id}/duplicate
- PUT /api/courses/{id}
- DELETE /api/courses/{id}

## Assessments
- GET /api/courses/{id}/assessments
- POST /api/courses/{id}/assessments
- PUT /api/courses/{id}/assessments/{assessmentId}
- DELETE /api/courses/{id}/assessments/{assessmentId}

Assessments are embedded in the course document, so their routes are nested under the course.

## Official Results
- PUT /api/courses/{id}/official-result
- POST /api/courses/{id}/official-result/confirm

## Calculations
- GET /api/courses/{id}/calculation
- POST /api/courses/{id}/simulate
- GET /api/semesters/{id}/gpa
- GET /api/cgpa
- POST /api/cgpa/target
- GET /api/credits/progress

## Grade History
- GET /api/grade-history (filters: semester, grade, course type, category, search; paginated)
- POST /api/grade-history (manual historical entry)
- PUT /api/grade-history/{courseId}
- DELETE /api/grade-history/{courseId}

## Dashboard
- GET /api/dashboard/summary
- GET /api/dashboard/gpa-history
- GET /api/dashboard/grade-distribution
- GET /api/dashboard/credit-progress

## Import / Export
- POST /api/import (upload, returns preview and validation report)
- GET /api/import/{jobId}
- POST /api/import/{jobId}/commit
- GET /api/export/summary.pdf
- GET /api/export/grade-history.{csv|xlsx}
- GET /api/export/semester/{id}
- GET /api/export/credits
- GET /api/export/full.json

## Authentication (Phase 6)
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- POST /api/auth/forgot-password
- POST /api/auth/reset-password
- POST /api/auth/claim-local-data

---

# 8. Non-Functional Requirements

## Performance
- Dashboard should load within an acceptable response time.
- Calculation updates should be near real-time.
- Large grade-history queries should use pagination.
- All user-owned queries hit `userId`-prefixed indexes.
- Frequently requested aggregates may be cached in `calculation_snapshots`, keyed by `inputsHash`.

## Security
- Input validation on every request (Pydantic).
- Protection against NoSQL injection: no raw user-supplied query operators; all filters built server-side.
- Repository-layer ownership scoping on every user-owned collection.
- Audit logging for changes to official academic records.
- Phase 6: Argon2id password hashing, secure token handling, HTTPS in deployed environments, rate limiting on auth endpoints, user isolation tests.

## Data Integrity
- Multi-document transactions for related updates (requires replica set).
- `Decimal128` for all marks, credits and grade points.
- Preserve historical results via snapshots.
- Avoid duplicated calculated data.
- Record engine versions on cached calculations.

## Maintainability
- Separate frontend, backend, database access and calculation engine.
- Index and validator definitions kept in code and applied at startup; data migrations as versioned scripts.
- Automated unit and integration tests.
- OpenAPI documentation generated by FastAPI.

---

# 9. Recommended Technology Stack

## Frontend
- React
- TypeScript
- Tailwind CSS
- Recharts for analytics

## Backend
- Python
- FastAPI
- Pydantic v2
- Beanie (async ODM on the PyMongo async driver)

## Database
- MongoDB 7+ as a replica set (single-node in development)

## Authentication (Phase 6)
- Argon2id password hashing (`argon2-cffi`)
- JWT access tokens with rotating refresh tokens (stored hashed in `refresh_tokens`)

## Testing
- Pytest for the calculation engine (no database).
- API integration tests against a disposable MongoDB container (testcontainers).
- User isolation tests (Phase 6).
- Frontend component tests.

## Deployment
- Docker
- Docker Compose (api, web, mongo replica set, reverse proxy)
- Nginx or an equivalent reverse proxy
- Scheduled `mongodump` backups

---

# 10. Development Phases

## Phase 1 – Calculation Engine
Pure Python package, no database. Implement and test:
- Assessment weighted marks.
- Required marks (single and multiple pending assessments).
- Grade prediction.
- Course grade points.
- Semester GPA.
- CGPA and target CGPA.
- Credit calculations.

Validate against Semester 4, 5, 6 and 7 of the workbook.

## Phase 2 – MongoDB Data Layer and Core API (Single-User Mode)
Implement:
- Docker Compose with a single-node MongoDB replica set.
- Beanie document models, indexes and collection validators.
- Seed data: local user, VIT university/programme, curriculum version with categories and templates, default grading scheme, course types.
- Repository layer with mandatory `userId` scoping.
- `get_current_user()` dependency returning the local user.
- Profile, academic configuration, semester, course and assessment endpoints.

## Phase 3 – Academic Tracking
Implement:
- Official results with snapshots and confirmation flow.
- Grade history view and manual history entries.
- Curriculum requirements and credit progress.
- Predicted and confirmed GPA/CGPA.
- Target CGPA.
- Audit log.

## Phase 4 – Frontend
Implement (no login screens):
- Dashboard.
- Semester views.
- Course details.
- Assessment calculator and simulator.
- Credit tracker.
- Grade history.
- Profile and grading scheme settings.

## Phase 5 – Analytics and Import/Export
Implement:
- GPA and CGPA graphs.
- Grade distribution.
- Excel import with preview, validation and commit.
- PDF/CSV/Excel export and full JSON export.

## Phase 6 – Authentication and Multi-User
Implement:
- Registration, login, logout, refresh, password reset, account management.
- Argon2id hashing and token handling.
- Replace `get_current_user()` with token-based resolution.
- Local data claim for the first registered account.
- Login and registration UI.
- User isolation test suite across every endpoint.

## Phase 7 – Hardening and Deployment
Implement:
- Security review.
- Concurrent user testing.
- Backups and restore drill.
- HTTPS and production deployment.

---

# 11. Acceptance Criteria

## Core product (Phases 1–5)
1. The application is fully usable in single-user mode without any login.
2. A user can configure their own grading scheme; editing it does not change existing results.
3. A user can create courses manually or from templates.
4. A course can contain any number of assessments.
5. Weighted marks are calculated correctly.
6. Required final examination marks are calculated for every configured grade.
7. Predicted and confirmed grades remain separate.
8. Semester GPA is credit-weighted.
9. CGPA is cumulatively credit-weighted.
10. Credit progress is tracked by category.
11. Manual and automatic grade-history entries are supported without duplicates.
12. Dashboard analytics reflect the underlying academic records.
13. Excel imports can be validated before being committed.
14. Historical results remain unchanged when templates, courses or grading schemes are edited.

## Multi-user (Phase 6)
15. Multiple users can register and maintain separate academic records.
16. One user's data cannot be accessed or modified by another user through any endpoint.
17. Enabling authentication requires no data migration; local-mode data can be claimed by the first account.

---

# 12. Outstanding Academic Decisions

The following must be confirmed before finalizing the calculation engine:

1. Exact numerical boundaries for D and E grades.
2. Whether rounding is applied before or after grade determination.
3. Whether all assessment weightages must total exactly 100.
4. How absent and exempted assessments affect calculations.
5. Which course types contribute to GPA.
6. Which course types count towards graduation credits.
7. Whether failed/repeated courses replace or supplement previous grades in CGPA.
8. Whether summer courses and additional courses contribute to CGPA.
9. Whether non-graded courses contribute to any graduation requirement.
10. Whether course credits and categories can be changed after official results.

These rules must be configurable where possible (user `settings`, grading scheme, or per-course flags), rather than embedded as assumptions in the calculation code.

---

# 13. Implementation Notes (as built)

All seven phases are implemented. Where the build differs from Sections 4–7, the build is
deliberately simpler:

| Spec | As built | Why |
|---|---|---|
| camelCase field names | snake_case in MongoDB, the API and the frontend | One naming style end to end; nothing to translate. |
| `calculation_snapshots` collection | Not created | Calculations take milliseconds; storing them would create a second source of truth. |
| Shared default grading scheme | Each user gets an editable copy of the VIT scheme | No special read-only case; editing simply creates a new version. |
| `grade_scale_entries.display_order`, `assessments.sequence` | List order is the display order | Not needed with embedded lists. |
| `curriculum_versions.total_required_credits` | Derived from the sum of category requirements | Cannot get out of step with the categories. |
| `semesters.curriculum_version_id` / grading scheme | Taken from the user's profile and settings | One place to change them. |
| `templateRef`, `supersedes_course_id` | `template_id` only; repeats use `attempt` (latest graded attempt counts) | Fewer fields to keep consistent. |
| `/api/dashboard/summary`, `gpa-history`, `credit-progress` | Served by `/api/cgpa` and `/api/credits/progress`; `/api/dashboard/grade-distribution` added | Avoids duplicate endpoints. |
| Import TTL on `status` | `expires_at` field with a TTL index, cleared on commit | MongoDB partial TTL indexes cannot express "not committed". |

Answers chosen for the outstanding academic decisions (Section 12), each easy to change:
D ≥ 55 and E ≥ 50 (editable in the grading scheme); rounding before grading off by default
(a setting); a grade is predicted only when weightages total exactly 100; absent = 0,
exempted = weightage spread over the remaining assessments; GPA, earned-credit and
requirement flags are set per course (templates and the import default sensibly, e.g. P
grades are non-GPA); a repeated course's latest graded attempt replaces earlier ones in
the CGPA; course credits and categories can be edited after results, but official
results keep their snapshot.

Additional endpoints not in Section 7: `POST /api/curricula/{id}/copy`,
`DELETE /api/courses/{id}/official-result`, `POST /api/courses/{id}/duplicate`,
`GET /api/import/template.xlsx`, `GET /api/export/semesters/{id}.pdf`.

The Excel import also reads VTOP's "Grade history" sheet as is. VTOP gives no semester,
so courses are grouped into one semester per exam month.

## Phase 6 (authentication) as built

| Spec | As built | Why |
|---|---|---|
| Access token + rotating refresh token | Both in httpOnly, SameSite=Strict cookies (`access_token` on `/api`, 15 min; `refresh_token` on `/api/auth`, 30 days) | JavaScript never holds a token, plain download links stay authenticated, and SameSite=Strict blocks cross-site requests (CSRF). |
| `refresh_tokens` and `password_reset_tokens` collections | One `auth_tokens` collection with a `kind` field (SHA-256 hashes only, TTL on `expires_at`) | Same lifecycle; one model. |
| Refresh-token reuse | Each token works once; a reuse more than a minute later ends every session of that user | Two tabs refreshing at the same moment are not mistaken for theft. |
| `POST /api/auth/claim-local-data` | `claim_local_data: true` on `POST /api/auth/register`; `GET /api/auth/status` says whether there is anything to claim | The claim is part of creating the first account; no half-registered state. |
| The local user is created at first start | No longer created; an existing one stays claimable | New installs start with registration. |
| Account management | `GET /api/auth/me`, `PUT /api/auth/email`, `PUT /api/auth/password` (logs out other sessions), `POST /api/auth/delete-account` (deletes everything the user owns) | |
| Rate limiting | In memory, per client address and endpoint (10 per minute) on login, register, password reset and account changes | Enough for a single API process; use a shared store if the API is ever scaled out. |

Every route except `/api/auth/*` requires a logged-in user, including the shared reference data.
An access token stays valid for up to 15 minutes after a password change or logout elsewhere.

## Phase 7 (hardening and deployment) as built

- `docker-compose.yml`: MongoDB 7 single-node replica set (not published outside the compose network), the API, and Caddy serving the built frontend with automatic HTTPS and security headers (`deploy/Caddyfile`). Caddy replaces Nginx because it obtains and renews certificates itself.
- Backups with `mongodump` archives (`deploy/backup.sh`, keeps 14), `deploy/restore.sh`, and `deploy/restore_drill.sh`, which restores the newest backup into a scratch database and compares every collection.
- Tests added: user isolation across every endpoint (`test_isolation.py`, enumerated from the OpenAPI schema so new routes are covered automatically) and concurrent users (`test_concurrency.py`).
- Fixes from the security and concurrency review: two requests changing the same documents in transactions at once now get 409 instead of a server error; uploads are limited to 5 MB; no response includes password hashes.

---

**End of Specification – Version 2.0**
