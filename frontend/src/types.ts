// Shapes of the JSON the backend sends. Field names match the backend models.

export type Id = string;

export type SemesterType = "regular" | "summer" | "other";
export type SemesterStatus = "planned" | "active" | "completed";
export type AssessmentStatus = "pending" | "completed" | "absent" | "exempted";
export type CourseStatus = "planned" | "in_progress" | "completed" | "failed" | "withdrawn";

export interface Semester {
  id: Id;
  semester_number: number;
  semester_type: SemesterType;
  label: string;
  academic_year: string | null;
  status: SemesterStatus;
}

export interface Assessment {
  id: Id;
  name: string;
  maximum_marks: number;
  weightage: number;
  obtained_marks: number | null;
  status: AssessmentStatus;
  allow_over_max: boolean;
  assessment_date: string | null;
}

export interface OfficialResult {
  grade: string;
  grade_point: number;
  is_passing: boolean;
  result_status: "provisional" | "confirmed";
  credits: number;
  category_code: string | null;
  counts_towards_gpa: boolean;
  grading_scheme_version: number | null;
  exam_month: string | null;
  result_date: string | null;
  source: "manual" | "import" | "generated";
}

// The fields a user edits on a course (create / update request body).
export interface CourseFields {
  semester_id: Id;
  course_code: string;
  title: string;
  course_type_code: string | null;
  credits: number;
  category_code: string | null;
  counts_towards_gpa: boolean;
  counts_towards_earned_credits: boolean;
  counts_towards_requirement: boolean;
  status: CourseStatus;
  grading_scheme_id: Id | null;
  attempt: number;
}

export interface Course extends CourseFields {
  id: Id;
  template_id: Id | null;
  source: "manual" | "template" | "import";
  assessments: Assessment[];
  official_result: OfficialResult | null;
}

export interface GradeEntry {
  grade: string;
  grade_point: number;
  minimum_marks: number | null;
  maximum_marks: number | null;
  is_passing: boolean;
}

export interface GradingScheme {
  id: Id;
  name: string;
  scheme_key: string;
  version: number;
  is_archived: boolean;
  entries: GradeEntry[];
}

export interface CreditCategory {
  code: string;
  name: string;
  required_credits: number;
}

export interface CourseTemplate {
  template_id: Id;
  course_code: string;
  title: string;
  course_type_code: string | null;
  credits: number;
  category_code: string | null;
}

export interface Curriculum {
  id: Id;
  user_id: Id | null; // null = shared, read-only
  programme_id: Id | null;
  version_name: string;
  effective_year: number | null;
  categories: CreditCategory[];
  course_templates: CourseTemplate[];
}

export interface CourseType {
  id: Id;
  user_id: Id | null;
  code: string;
  name: string;
}

export interface ProfileData {
  profile: {
    full_name: string;
    university_id: Id | null;
    programme_id: Id | null;
    curriculum_version_id: Id | null;
    specialisation: string | null;
    admission_year: number | null;
    graduation_year: number | null;
  };
  settings: {
    default_grading_scheme_id: Id | null;
    round_marks_before_grading: boolean;
    target_cgpa: number | null;
  };
}

// --- Calculation results ---

export type TargetStatus = "already_achieved" | "achievable" | "not_achievable" | "pending_configuration";

export interface GradeTarget {
  grade: string;
  minimum_marks: number;
  status: TargetStatus;
  required_percentage: number | null;
  required_marks: Record<string, number>;
}

export interface CourseAnalysis {
  weightage_total: number;
  is_configuration_complete: boolean;
  current_marks: number;
  maximum_possible_marks: number;
  projected_marks: number | null;
  predicted_grade: string | null;
  predicted_grade_point: number | null;
  pending_assessments: string[];
  targets: GradeTarget[];
}

export interface GpaSummary {
  total_credits: number;
  gpa_credits: number;
  grade_points: number;
  gpa: number | null;
}

export type GradeBasis = "confirmed" | "provisional" | "predicted" | null;

export interface CourseGrade {
  course_id: Id;
  course_code: string;
  title: string;
  credits: number;
  counts_towards_gpa: boolean;
  grade: string | null;
  grade_point: number | null;
  basis: GradeBasis;
}

export interface SemesterGpa {
  semester_id: Id;
  label: string;
  confirmed: GpaSummary;
  predicted: GpaSummary;
  courses: CourseGrade[];
}

export interface CgpaSummary {
  gpa_credits: number;
  grade_points: number;
  cgpa: number | null;
  progression: (number | null)[];
}

export interface CgpaReport {
  confirmed: CgpaSummary;
  predicted: CgpaSummary;
  semesters: {
    semester_id: Id;
    label: string;
    confirmed_gpa: number | null;
    predicted_gpa: number | null;
    confirmed_cgpa: number | null;
    predicted_cgpa: number | null;
    gpa_credits: number;
  }[];
}

export interface TargetCgpa {
  target_cgpa: number;
  required_gpa: number | null;
  status: "already_achieved" | "achievable" | "not_achievable";
  remaining_credits: number;
  highest_reachable_cgpa: number | null;
}

export interface CategoryProgress {
  code: string;
  name: string;
  required_credits: number;
  earned_credits: number;
  remaining_credits: number;
  surplus_credits: number;
  completion_percentage: number | null;
}

export interface CreditReport {
  curriculum: { id: Id; version_name: string } | null;
  required_credits: number;
  earned_credits: number;
  remaining_credits: number;
  surplus_credits: number;
  completion_percentage: number | null;
  gpa_credits: number;
  non_gpa_credits: number;
  categories: CategoryProgress[];
  uncategorised_credits: number;
  semesters: { semester_id: Id; label: string; registered_credits: number; earned_credits: number }[];
  warnings: { type: string; course_id: Id; course_code: string; message: string }[];
}

export interface GradeDistribution {
  grades: string[]; // in grading-scheme order
  overall: Record<string, number>;
  by_category: Record<string, Record<string, number>>;
  by_course_type: Record<string, Record<string, number>>;
}

export interface ImportJob {
  id: Id;
  filename: string;
  status: "validated" | "failed" | "committed";
  errors: string[];
  warnings: string[];
  preview: {
    semesters: Omit<Semester, "id">[];
    courses: (Omit<CourseFields, "semester_id"> & { semester: string; grade: string | null; assessments: unknown[] })[];
    marks_for_existing_courses: Record<Id, unknown[]>;
    requirements: CreditCategory[];
  };
}

export interface Account {
  email: string;
  full_name: string;
}
