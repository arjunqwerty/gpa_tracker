# VIT CGPA Tracker
## Functional Requirements & Database Design

**Document Version:** 1.0  
**Status:** Initial Technical Specification  
**Application Type:** Multi-user Academic Performance Tracking Platform

---

# 1. Project Overview

## 1.1 Objective

Develop a web-based application that allows individual students to track their academic performance, calculate expected grades, monitor semester GPA and cumulative CGPA, and maintain curriculum credit completion.

The existing Excel workbook serves as the reference for the initial calculation engine and functional behaviour.

The application must support multiple independent users simultaneously, with each user maintaining their own academic records.

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
11. Provide secure, isolated user accounts.

## 1.3 Design Principles

- Configurable instead of hardcoded academic rules.
- Dynamic assessment structures.
- Independent calculation engine.
- Separation of predicted and confirmed results.
- Single source of truth for academic records.
- Automatic recalculation when relevant data changes.
- Historical data preservation.
- Strict user-level data isolation.

---

# 2. Functional Requirements

## FR-01: User Management

### FR-01.1 Registration
Users must be able to register using:
- Name
- Email address
- Password

Email addresses must be unique.

### FR-01.2 Authentication
- Login and logout.
- Secure password hashing.
- Session/token management.
- Password reset.
- Account management.

### FR-01.3 User Data Isolation

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

### FR-01.4 User Profile

Store:
- Name
- Email
- University
- Programme
- Specialisation
- Admission year
- Expected graduation year

These fields should be editable where appropriate.

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

Grading schemes must be versioned so that historical results remain unchanged when a scheme is modified.

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

Imported courses become individual student course records.

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

Historical records must not be silently changed when a course is edited.

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
| Status | Pending, completed or absent |
| Assessment date | Optional |
| Sequence | Display order |

### FR-04.3 Assessment Validation

- Maximum marks must be greater than zero.
- Obtained marks cannot exceed maximum marks unless explicitly configured otherwise.
- Weightages must be non-negative.
- Assessment weightages must normally total 100.
- Incomplete assessment structures must be allowed during setup.
- The application must identify incomplete configurations.

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

The user must be able to simulate possible future assessment marks without permanently modifying actual marks.

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

Predicted results must be stored separately from official grades.

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

The application must support two entry methods.

### FR-11.1 Manual Entry

Users can add historical academic records.

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

When a course receives a confirmed final grade, the application should generate its academic history record.

The user must be able to review and confirm the result.

### FR-11.3 History Management

- View all completed courses.
- Filter by semester.
- Filter by grade.
- Filter by course type.
- Filter by curriculum category.
- Search by course code/title.
- View historical GPA contribution.

Manual and automatically generated records must not create duplicate course completions.

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

Import must include a preview and validation stage.

### Export
Support:
- Academic summary PDF.
- Grade history CSV/Excel.
- Semester report.
- Credit completion report.
- Full user data export.

---

# 3. Calculation Engine Specification

The calculation engine must be a separate backend service.

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

- Use decimal arithmetic rather than binary floating-point arithmetic for financial-like precision.
- Do not round intermediate values.
- Apply rounding only for presentation or explicitly configured academic rules.
- Preserve original marks and weightages.
- Recalculate dependent values after relevant changes.
- Never overwrite official results with predictions.
- Exclude pending assessments from actual weighted marks.
- Validate the total assessment weightage before final calculation.

## 3.3 Source Workbook Compatibility

The calculation engine must initially reproduce the logic used in the later semester sheets.

Reference formula:

Weighted Mark = Scored × Weightage / Maximum Mark

Required FAT Mark = (Grade Threshold - Existing Weighted Marks) × FAT Maximum / FAT Weightage

Semester GPA = Sum(Course Credits × Grade Points) / Sum(Course Credits)

CGPA = Sum(Semester GPA × Semester Credits) / Sum(Semester Credits)

The workbook's actual formula errors must not be copied into the new implementation.

---

# 4. Database Design

Recommended database: PostgreSQL.

Use UUID primary keys, foreign keys, indexes and transaction-safe operations.

All user-owned entities must contain an owner/user relationship, either directly or through a parent entity.

## 4.1 Entity Overview

Core entities:

1. users
2. user_profiles
3. universities
4. academic_programmes
5. curriculum_versions
6. semesters
7. course_templates
8. student_courses
9. course_types
10. credit_categories
11. curriculum_requirements
12. grading_schemes
13. grade_scale_entries
14. course_assessments
15. course_grades
16. semester_results
17. academic_history
18. calculation_snapshots
19. import_jobs

---

## 4.2 Table Definitions

### users

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| email | VARCHAR(255) | Unique email |
| password_hash | TEXT | Password hash |
| is_active | BOOLEAN | Account status |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update |

### user_profiles

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| full_name | VARCHAR(150) | Name |
| university_id | UUID | FK universities |
| programme_id | UUID | FK academic_programmes |
| admission_year | INTEGER | Admission year |
| graduation_year | INTEGER | Expected graduation |

### universities

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR(255) | University name |
| short_name | VARCHAR(100) | University abbreviation |

### academic_programmes

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| university_id | UUID | FK universities |
| name | VARCHAR(255) | Programme name |
| degree_type | VARCHAR(100) | Degree |
| duration_semesters | INTEGER | Duration |

### curriculum_versions

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| programme_id | UUID | FK academic_programmes |
| version_name | VARCHAR(100) | Version |
| effective_year | INTEGER | Applicable year |
| total_required_credits | DECIMAL(7,2) | Required credits |
| is_active | BOOLEAN | Active template |

### semesters

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| curriculum_version_id | UUID | FK curriculum_versions |
| semester_number | INTEGER | Semester |
| academic_year | VARCHAR(20) | Academic year |
| semester_type | VARCHAR(30) | Regular/summer/other |
| status | VARCHAR(30) | Planned/active/completed |

### course_templates

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| curriculum_version_id | UUID | FK curriculum_versions |
| course_code | VARCHAR(50) | Course code |
| title | VARCHAR(255) | Course title |
| course_type_id | UUID | FK course_types |
| credits | DECIMAL(5,2) | Credits |
| credit_category_id | UUID | FK credit_categories |

### student_courses

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| semester_id | UUID | FK semesters |
| template_id | UUID nullable | Source template |
| course_code | VARCHAR(50) | Course code |
| title | VARCHAR(255) | Course title |
| credits | DECIMAL(5,2) | Credits |
| course_type_id | UUID | FK course_types |
| credit_category_id | UUID | FK credit_categories |
| counts_towards_gpa | BOOLEAN | GPA eligibility |
| counts_towards_earned_credits | BOOLEAN | Earned-credit eligibility |
| counts_towards_requirement | BOOLEAN | Curriculum eligibility |
| status | VARCHAR(30) | Planned/in progress/completed |

### course_types

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID nullable | Owner; NULL for shared types |
| code | VARCHAR(30) | Type code |
| name | VARCHAR(100) | Display name |

### credit_categories

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| curriculum_version_id | UUID | FK curriculum_versions |
| code | VARCHAR(50) | Category code |
| name | VARCHAR(255) | Category name |

### curriculum_requirements

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| curriculum_version_id | UUID | FK curriculum_versions |
| credit_category_id | UUID | FK credit_categories |
| required_credits | DECIMAL(7,2) | Required credits |

### grading_schemes

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Owner |
| name | VARCHAR(100) | Scheme name |
| version | INTEGER | Scheme version |
| is_default | BOOLEAN | Default scheme |

### grade_scale_entries

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| grading_scheme_id | UUID | FK grading_schemes |
| grade | VARCHAR(10) | Grade label |
| grade_point | DECIMAL(5,2) | Grade point |
| minimum_marks | DECIMAL(6,2) | Minimum boundary |
| maximum_marks | DECIMAL(6,2) | Maximum boundary |
| is_passing | BOOLEAN | Passing status |
| display_order | INTEGER | Display sequence |

### course_assessments

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| student_course_id | UUID | FK student_courses |
| name | VARCHAR(100) | Assessment name |
| maximum_marks | DECIMAL(8,2) | Maximum marks |
| weightage | DECIMAL(6,2) | Weightage |
| obtained_marks | DECIMAL(8,2) nullable | Marks scored |
| status | VARCHAR(30) | Pending/completed/absent/exempted |
| sequence | INTEGER | Display order |
| assessment_date | DATE nullable | Date |

### course_grades

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| student_course_id | UUID | FK student_courses |
| grading_scheme_id | UUID | FK grading_schemes |
| grade_scale_entry_id | UUID nullable | FK grade_scale_entries |
| awarded_grade | VARCHAR(10) | Official grade |
| grade_point | DECIMAL(5,2) | Official grade point |
| result_status | VARCHAR(30) | Provisional/confirmed |
| result_date | DATE nullable | Result date |
| source | VARCHAR(30) | Manual/import/generated |

### semester_results

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| semester_id | UUID | FK semesters |
| result_type | VARCHAR(30) | Predicted/confirmed |
| total_credits | DECIMAL(8,2) | GPA credits |
| total_grade_points | DECIMAL(10,2) | Weighted grade points |
| gpa | DECIMAL(6,4) | Calculated GPA |
| calculated_at | TIMESTAMP | Calculation time |

### academic_history

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| student_course_id | UUID nullable | Linked course |
| semester_id | UUID nullable | Semester |
| course_code | VARCHAR(50) | Course code |
| course_title | VARCHAR(255) | Course title |
| course_type_id | UUID nullable | Course type |
| credits | DECIMAL(5,2) | Credits |
| grade | VARCHAR(10) | Final grade |
| grade_point | DECIMAL(5,2) | Grade point |
| exam_month | DATE nullable | Exam month |
| result_date | DATE nullable | Declaration date |
| credit_category_id | UUID nullable | Curriculum category |
| source | VARCHAR(30) | Manual/import/generated |

### calculation_snapshots

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| semester_id | UUID nullable | Semester |
| calculation_type | VARCHAR(50) | GPA/CGPA/credit |
| result_data | JSONB | Calculated result |
| source_version | INTEGER | Calculation version |
| created_at | TIMESTAMP | Snapshot time |

### import_jobs

| Column | Type | Description |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | FK users |
| filename | VARCHAR(255) | Imported file |
| status | VARCHAR(30) | Pending/validated/completed/failed |
| validation_report | JSONB | Import issues |
| created_at | TIMESTAMP | Import time |

---

# 5. Database Relationships

- One user has one profile.
- One user has multiple semesters.
- One academic programme has multiple curriculum versions.
- One curriculum version has multiple course templates.
- One curriculum version has multiple credit categories.
- One curriculum version has multiple curriculum requirements.
- One semester has multiple student courses.
- One student course has multiple assessments.
- One student course has zero or one current official grade record.
- One grading scheme has multiple grade scale entries.
- One semester has multiple result snapshots.
- One user has multiple historical academic records.

Course templates are reusable reference data. Student courses are individual records created from templates or manually.

Changing a template must not modify existing student courses.

---

# 6. Important Database Constraints

1. User email must be unique.
2. Semester number must be valid.
3. Course credits cannot be negative.
4. Maximum marks must be greater than zero.
5. Obtained marks must be within the permitted range.
6. Grade points must follow the selected grading scheme.
7. Assessment weightages must be validated.
8. A student course must belong to the same user as its semester.
9. An official course result must not be duplicated.
10. Historical records must retain their original grading configuration.

Use composite ownership constraints where possible, and PostgreSQL Row-Level Security for user-owned records.

---

# 7. API Structure

Suggested REST API structure.

## Authentication
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/auth/refresh
- POST /api/auth/forgot-password

## Profile
- GET /api/profile
- PUT /api/profile

## Academic Configuration
- GET /api/programmes
- POST /api/programmes
- GET /api/grading-schemes
- POST /api/grading-schemes
- PUT /api/grading-schemes/{id}

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
- PUT /api/courses/{id}
- DELETE /api/courses/{id}

## Assessments
- GET /api/courses/{id}/assessments
- POST /api/courses/{id}/assessments
- PUT /api/assessments/{id}
- DELETE /api/assessments/{id}

## Calculations
- GET /api/courses/{id}/calculation
- POST /api/courses/{id}/simulate
- GET /api/semesters/{id}/gpa
- GET /api/cgpa
- GET /api/credits/progress

## Grade History
- GET /api/grade-history
- POST /api/grade-history
- PUT /api/grade-history/{id}
- DELETE /api/grade-history/{id}

## Dashboard
- GET /api/dashboard/summary
- GET /api/dashboard/gpa-history
- GET /api/dashboard/grade-distribution
- GET /api/dashboard/credit-progress

---

# 8. Non-Functional Requirements

## Performance
- Dashboard should load within an acceptable response time.
- Calculation updates should be near real-time.
- Large grade-history queries should use pagination.
- Frequently requested aggregates should be indexed or cached.

## Security
- Password hashing using a modern password hashing algorithm.
- HTTPS for deployed environments.
- Secure authentication.
- Input validation.
- Protection against SQL injection.
- User-level authorization.
- Database Row-Level Security.
- Audit logging for important academic changes.

## Data Integrity
- Use database transactions for related updates.
- Maintain foreign-key constraints.
- Preserve historical results.
- Avoid duplicated calculated data.
- Record calculation versions.

## Maintainability
- Separate frontend, backend, database and calculation engine.
- Use database migrations.
- Implement automated unit and integration tests.
- Maintain API documentation.

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
- Pydantic
- SQLAlchemy

## Database
- PostgreSQL
- JSONB for flexible calculation snapshots and import reports.

## Authentication
- JWT or secure session-based authentication.
- Argon2id password hashing.

## Testing
- Pytest for calculation engine.
- API integration tests.
- Database isolation tests.
- Frontend component tests.

## Deployment
- Docker
- Docker Compose
- PostgreSQL
- Nginx or an equivalent reverse proxy.

---

# 10. Development Phases

## Phase 1 – Calculation Engine
Implement and test:
- Assessment weighted marks.
- Required marks.
- Grade prediction.
- Course grade points.
- Semester GPA.
- CGPA.
- Credit calculations.

Validate against Semester 4, 5, 6 and 7.

## Phase 2 – Database and Backend
Implement:
- Authentication.
- Academic configuration.
- Semester management.
- Course management.
- Assessment management.
- Database migrations.

## Phase 3 – Academic Tracking
Implement:
- Grade history.
- Curriculum requirements.
- Credit progress.
- Confirmed and predicted results.

## Phase 4 – Frontend
Implement:
- Dashboard.
- Semester views.
- Course details.
- Assessment calculator.
- Credit tracker.
- Grade history.

## Phase 5 – Analytics and Import/Export
Implement:
- GPA and CGPA graphs.
- Grade distribution.
- Excel import.
- PDF/Excel export.

## Phase 6 – Multi-user Testing and Deployment
Implement:
- User isolation testing.
- Security checks.
- Concurrent user testing.
- Backups.
- Deployment.

---

# 11. Acceptance Criteria

The initial application will be considered functionally complete when:

1. Multiple users can register and maintain separate academic records.
2. A user can configure their own grading scheme.
3. A user can create courses manually or from templates.
4. A course can contain any number of assessments.
5. Weighted marks are calculated correctly.
6. Required final examination marks are calculated for every configured grade.
7. Predicted and confirmed grades remain separate.
8. Semester GPA is credit-weighted.
9. CGPA is cumulatively credit-weighted.
10. Credit progress is tracked by category.
11. Manual and automatic grade-history entries are supported.
12. Dashboard analytics reflect the underlying academic records.
13. Excel imports can be validated before being committed.
14. Historical results remain unchanged when templates are edited.
15. One user's data cannot be accessed by another user.

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

These rules must be configurable where possible, rather than embedded as assumptions in the calculation code.

---

**End of Specification – Version 1.0**