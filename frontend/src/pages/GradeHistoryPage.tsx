import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, useAction, useApi, useCurriculum } from "../api";
import CourseForm, { emptyCourse } from "../components/CourseForm";
import { NavRow, OpenRowHint, RowLink } from "../components/navigation";
import { Badge, Button, Card, ErrorMessage, Field, Loading, PageHeader, RemoveButton, fmt, monthLabel, tableClass } from "../components/ui";
import type { Course, CourseFields, GradingScheme, ProfileData, Semester } from "../types";

const PAGE_SIZE = 50;
const NO_FILTERS = { semester_id: "", grade: "", course_type: "", category: "", search: "" };

export default function GradeHistoryPage() {
  // Filters and page live in the URL, so opening a course and coming back keeps the same view.
  const [params, setParams] = useSearchParams();
  const filters = Object.fromEntries(Object.keys(NO_FILTERS).map((k) => [k, params.get(k) ?? ""])) as typeof NO_FILTERS;
  const page = Number(params.get("page")) || 1;
  const setView = (nextFilters: typeof NO_FILTERS, nextPage: number) =>
    setParams(Object.fromEntries([...Object.entries(nextFilters).filter(([, v]) => v), ...(nextPage > 1 ? [["page", String(nextPage)]] : [])]),
      { replace: true });
  const setPage = (nextPage: number) => setView(filters, nextPage);
  const [adding, setAdding] = useState(false);
  const query = new URLSearchParams({ ...Object.fromEntries(Object.entries(filters).filter(([, v]) => v)), page: String(page), page_size: String(PAGE_SIZE) });
  const history = useApi<{ total: number; items: Course[] }>(`/api/grade-history?${query}`);
  const semesters = useApi<Semester[]>("/api/semesters");
  const profile = useApi<ProfileData>("/api/profile");
  const schemes = useApi<GradingScheme[]>("/api/grading-schemes");
  const categories = useCurriculum().data?.categories ?? [];
  const { run, error } = useAction();

  if (!semesters.data || !profile.data || !schemes.data) return <Loading error={semesters.error ?? profile.error ?? schemes.error} />;
  const semesterLabel = new Map(semesters.data.map((s) => [s.id, s.label]));
  const defaultScheme = schemes.data.find((s) => s.id === profile.data!.settings.default_grading_scheme_id);
  const grades = defaultScheme?.entries.map((e) => e.grade) ?? [];
  const pages = Math.max(1, Math.ceil((history.data?.total ?? 0) / PAGE_SIZE));

  const filter = (changes: Partial<typeof NO_FILTERS>) => setView({ ...filters, ...changes }, 1);
  const remove = (course: Course) =>
    confirm(`Remove the ${course.official_result!.grade} in ${course.course_code} from your grade history?` +
      (course.assessments.length ? " The course and its marks stay." : " The course is removed too.")) &&
    run(() => api.delete(`/api/grade-history/${course.id}`)).then((ok) => ok && history.reload());

  return (
    <>
      <PageHeader title="Grade history" subtitle={`${history.data?.total ?? "…"} graded courses`}
        actions={!adding && <Button onClick={() => setAdding(true)} disabled={semesters.data.length === 0}>Add past result</Button>} />
      <ErrorMessage message={error} />
      {semesters.data.length === 0 && <p className="mb-4 text-sm text-slate-500">Create a semester first to add past results.</p>}

      {adding && (
        <HistoryEntryForm semesterId={semesters.data[0].id} grades={grades}
          onDone={() => { setAdding(false); history.reload(); }} onCancel={() => setAdding(false)} />
      )}

      <Card>
        <div className="mb-4 grid grid-cols-1 gap-3 sm:flex sm:flex-wrap [&>*]:min-w-0 [&_select]:sm:max-w-56">
          <input aria-label="Search" maxLength={100} placeholder="Search code or title" value={filters.search} onChange={(e) => filter({ search: e.target.value })} />
          <select aria-label="Semester" value={filters.semester_id} onChange={(e) => filter({ semester_id: e.target.value })}>
            <option value="">All semesters</option>
            {semesters.data.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
          <select aria-label="Grade" value={filters.grade} onChange={(e) => filter({ grade: e.target.value })}>
            <option value="">All grades</option>
            {grades.map((g) => <option key={g} value={g}>{g}</option>)}
          </select>
          <input aria-label="Course type" placeholder="Course type, e.g. TH" className="sm:w-40" value={filters.course_type}
            onChange={(e) => filter({ course_type: e.target.value.toUpperCase() })} />
          <select aria-label="Category" value={filters.category} onChange={(e) => filter({ category: e.target.value })}>
            <option value="">All categories</option>
            {categories.map((c) => <option key={c.code} value={c.code}>{c.code} · {c.name}</option>)}
          </select>
          <Button variant="secondary" onClick={() => filter(NO_FILTERS)}>Clear filters</Button>
        </div>

        {!history.data ? <Loading error={history.error} /> : (
          <table className={tableClass}>
            {history.data.items.length > 0 && <OpenRowHint />}
            <thead>
              <tr><th>Code</th><th>Title</th><th className="hidden sm:table-cell">Type</th><th>Credits</th><th>Category</th><th>Grade</th><th>Grade points</th><th>Exam</th><th className="hidden lg:table-cell">Semester</th><th></th></tr>
            </thead>
            <tbody>
              {history.data.items.map((course) => {
                const result = course.official_result!;
                return (
                  <NavRow key={course.id} to={`/courses/${course.id}`} from="Grade history">
                    <td><RowLink>{course.course_code}</RowLink></td>
                    <td>{course.title}</td>
                    <td className="hidden sm:table-cell">{course.course_type_code}</td>
                    <td>{fmt(result.credits)}</td>
                    <td>{result.category_code ?? "—"}</td>
                    <td>
                      <span className="font-semibold">{result.grade}</span>{" "}
                      {result.result_status === "provisional" && <Badge tone="amber">provisional</Badge>}
                    </td>
                    <td>{result.counts_towards_gpa ? fmt(result.grade_point * result.credits) : <span className="text-slate-500">non-GPA</span>}</td>
                    <td className="whitespace-nowrap">{monthLabel(result.exam_month)}</td>
                    <td className="hidden lg:table-cell">{semesterLabel.get(course.semester_id)}</td>
                    <td className="text-right"><RemoveButton label={`Remove ${course.course_code} from the grade history`} onClick={() => remove(course)} /></td>
                  </NavRow>
                );
              })}
            </tbody>
          </table>
        )}
        {history.data?.total === 0 && (
          <p className="text-sm text-slate-600">
            {Object.values(filters).some(Boolean)
              ? "No graded courses match these filters."
              : "No graded courses yet. Import your VTOP grade history on Import & export, or use Add past result."}
          </p>
        )}
        {pages > 1 && (
          <div className="mt-4 flex items-center gap-3 text-sm">
            <Button variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button>
            Page {page} of {pages}
            <Button variant="secondary" disabled={page === pages} onClick={() => setPage(page + 1)}>Next</Button>
          </div>
        )}
      </Card>
    </>
  );
}

function HistoryEntryForm({ semesterId, grades, onDone, onCancel }: {
  semesterId: string;
  grades: string[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const [grade, setGrade] = useState(grades[0] ?? "");
  const [examMonth, setExamMonth] = useState("");
  const [resultDate, setResultDate] = useState("");
  const { run, error, busy } = useAction();

  const save = (fields: CourseFields) =>
    run(() => api.post("/api/grade-history", {
      ...fields, status: "completed", grade, exam_month: examMonth ? `${examMonth}-01` : null, result_date: resultDate || null,
    })).then((ok) => ok && onDone());

  return (
    <Card title="Add a past result">
      <ErrorMessage message={error} />
      <CourseForm initial={emptyCourse(semesterId)} submitLabel="Add to history" busy={busy} onSubmit={save} onCancel={onCancel}>
        <div className="flex flex-wrap gap-3">
          <Field label="Grade">
            <select value={grade} onChange={(e) => setGrade(e.target.value)}>
              {grades.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </Field>
          <Field label="Exam month"><input type="month" value={examMonth} onChange={(e) => setExamMonth(e.target.value)} /></Field>
          <Field label="Result declared"><input type="date" value={resultDate} onChange={(e) => setResultDate(e.target.value)} /></Field>
        </div>
      </CourseForm>
    </Card>
  );
}
