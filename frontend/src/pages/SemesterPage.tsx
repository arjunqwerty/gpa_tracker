import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, useAction, useApi, useCurriculum } from "../api";
import CourseForm, { emptyCourse } from "../components/CourseForm";
import { NavRow, OpenRowHint, PageNav, RowLink, useCameFrom } from "../components/navigation";
import SemesterForm from "../components/SemesterForm";
import { Button, Card, ErrorMessage, GradeWithBasis, Loading, PageHeader, Stat, buttonClass, fmt, gpa as gpaText, tableClass } from "../components/ui";
import type { Course, CourseFields, Id, Semester, SemesterGpa } from "../types";

type Panel = "none" | "edit" | "course" | "templates";

const COURSE_STATUS = { planned: "Planned", in_progress: "In progress", completed: "Completed", failed: "Failed", withdrawn: "Withdrawn" };

export default function SemesterPage() {
  const { semesterId } = useParams() as { semesterId: Id };
  const navigate = useNavigate();
  const semester = useApi<Semester>(`/api/semesters/${semesterId}`);
  const gpa = useApi<SemesterGpa>(`/api/semesters/${semesterId}/gpa`);
  const courses = useApi<Course[]>(`/api/courses?semester_id=${semesterId}`);
  const [panel, setPanel] = useState<Panel>("none");
  const { run, error, busy } = useAction();
  const cameFrom = useCameFrom();

  if (!semester.data || !gpa.data || !courses.data) return <Loading error={semester.error ?? gpa.error ?? courses.error} />;
  const gradeByCourse = new Map(gpa.data.courses.map((c) => [c.course_id, c]));
  const label = semester.data.label;
  const courseCount = courses.data.length;

  const done = () => {
    setPanel("none");
    semester.reload();
    gpa.reload();
    courses.reload();
  };
  const update = (fields: Omit<Semester, "id">) => run(() => api.put(`/api/semesters/${semesterId}`, fields)).then((ok) => ok && done());
  const addCourse = (fields: CourseFields) => run(() => api.post("/api/courses", fields)).then((ok) => ok && done());
  const remove = () =>
    confirm(`Delete ${label} and its ${courseCount} ${courseCount === 1 ? "course" : "courses"}, with all their marks? This cannot be undone.`) &&
    run(() => api.delete(`/api/semesters/${semesterId}`)).then((ok) => ok && navigate("/semesters"));

  return (
    <>
      <PageNav back={cameFrom ?? { to: "/semesters", label: "Semesters" }} crumbs={[{ label: "Semesters", to: "/semesters" }, { label }]} />
      <PageHeader
        title={semester.data.label}
        subtitle={[`Semester ${semester.data.semester_number}`, semester.data.semester_type, semester.data.academic_year, semester.data.status]
          .filter(Boolean).join(" · ")}
        actions={<>
          <a className={buttonClass("secondary")} href={`/api/export/semesters/${semesterId}.pdf`} download>Download PDF report</a>
          <Button variant="secondary" onClick={() => setPanel("edit")}>Edit</Button>
          <Button variant="danger" onClick={remove}>Delete semester</Button>
        </>}
      />
      <ErrorMessage message={error} />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="GPA (confirmed)" value={gpaText(gpa.data.confirmed.gpa)} hint={`${fmt(gpa.data.confirmed.gpa_credits)} GPA credits`} />
        <Stat label="GPA (predicted)" value={gpaText(gpa.data.predicted.gpa)} hint={`${fmt(gpa.data.predicted.gpa_credits)} credits with a grade`} />
        <Stat label="Grade points" value={fmt(gpa.data.confirmed.grade_points)} hint="confirmed" />
        <Stat label="Registered credits" value={fmt(courses.data.reduce((sum, c) => sum + c.credits, 0))} hint={`${courses.data.length} courses`} />
      </div>

      {panel === "edit" && (
        <Card title="Edit semester">
          <SemesterForm initial={semester.data} submitLabel="Save semester" busy={busy} onSubmit={update} onCancel={() => setPanel("none")} />
        </Card>
      )}
      {panel === "course" && (
        <Card title="Add a course">
          <CourseForm initial={emptyCourse(semesterId)} submitLabel="Add course" busy={busy} onSubmit={addCourse} onCancel={() => setPanel("none")} />
        </Card>
      )}
      {panel === "templates" && (
        <TemplatePicker semesterId={semesterId} existingCodes={courses.data.map((c) => c.course_code)} onDone={done}
          onCancel={() => setPanel("none")} />
      )}

      <Card
        title="Courses"
        actions={<>
          <Button variant="secondary" onClick={() => setPanel("templates")}>Add from curriculum</Button>
          <Button onClick={() => setPanel("course")}>Add course</Button>
        </>}
      >
        <table className={tableClass}>
          {courses.data.length > 0 && <OpenRowHint />}
          <thead>
            <tr><th>Code</th><th>Title</th><th>Type</th><th>Category</th><th>Credits</th><th>Status</th><th>Grade</th></tr>
          </thead>
          <tbody>
            {courses.data.map((course) => {
              const grade = gradeByCourse.get(course.id);
              return (
                <NavRow key={course.id} to={`/courses/${course.id}`} from={label}>
                  <td><RowLink>{course.course_code}</RowLink></td>
                  <td>{course.title}</td>
                  <td>{course.course_type_code ?? "—"}</td>
                  <td>{course.category_code ?? "—"}</td>
                  <td>{fmt(course.credits)}{!course.counts_towards_gpa && <span className="text-xs text-slate-500"> (non-GPA)</span>}</td>
                  <td>{COURSE_STATUS[course.status]}</td>
                  <td><GradeWithBasis grade={grade?.grade ?? null} basis={grade?.basis ?? null} /></td>
                </NavRow>
              );
            })}
          </tbody>
        </table>
        {courses.data.length === 0 && (
          <p className="text-sm text-slate-600">No courses yet. Pick them from your curriculum with Add from curriculum, or use Add course.</p>
        )}
      </Card>
    </>
  );
}

function TemplatePicker({ semesterId, existingCodes, onDone, onCancel }: {
  semesterId: Id;
  existingCodes: string[];
  onDone: () => void;
  onCancel: () => void;
}) {
  const curriculum = useCurriculum();
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Set<Id>>(new Set());
  const { run, error, busy } = useAction();

  if (!curriculum.data) return <Card title="Add from curriculum"><Loading error={curriculum.error} /></Card>;
  const query = search.toLowerCase();
  const templates = curriculum.data.course_templates.filter(
    (t) => t.course_code.toLowerCase().includes(query) || t.title.toLowerCase().includes(query),
  );

  const toggle = (id: Id) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };
  const add = () =>
    run(() => api.post("/api/courses/from-template", {
      semester_id: semesterId, curriculum_version_id: curriculum.data!.id, template_ids: [...selected],
    })).then((ok) => ok && onDone());

  return (
    <Card title={`Add from curriculum (${curriculum.data.version_name})`}
      actions={<>
        <Button variant="secondary" onClick={onCancel}>Cancel</Button>
        <Button onClick={add} disabled={busy || selected.size === 0}>
          {selected.size === 1 ? "Add 1 course" : selected.size > 1 ? `Add ${selected.size} courses` : "Add courses"}
        </Button>
      </>}>
      <ErrorMessage message={error} />
      <input className="mb-3 w-full" aria-label="Search the curriculum" placeholder="Search by code or title" value={search} onChange={(e) => setSearch(e.target.value)} />
      <div className="max-h-96 overflow-y-auto">
        <table className={tableClass}>
          <thead><tr><th></th><th>Code</th><th>Title</th><th>Type</th><th>Category</th><th>Credits</th></tr></thead>
          <tbody>
            {templates.map((t) => {
              const alreadyAdded = existingCodes.includes(t.course_code);
              return (
                <tr key={t.template_id} onClick={() => !alreadyAdded && toggle(t.template_id)}
                  className={alreadyAdded ? "text-slate-500" : `cursor-pointer hover:bg-slate-50 ${selected.has(t.template_id) ? "bg-indigo-50" : ""}`}>
                  <td><input type="checkbox" disabled={alreadyAdded} checked={selected.has(t.template_id)}
                    aria-label={`Select ${t.course_code}`} onClick={(e) => e.stopPropagation()} onChange={() => toggle(t.template_id)} /></td>
                  <td>{t.course_code}</td>
                  <td>{t.title}{alreadyAdded && <span className="text-xs"> · already in this semester</span>}</td>
                  <td>{t.course_type_code}</td>
                  <td>{t.category_code}</td>
                  <td>{fmt(t.credits)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {templates.length === 0 && <p className="text-sm text-slate-600">No curriculum course matches “{search}”.</p>}
      </div>
    </Card>
  );
}
