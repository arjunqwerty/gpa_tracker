import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, useAction, useApi } from "../../api";
import CourseForm, { courseFields } from "../../components/CourseForm";
import { PageNav, useCameFrom } from "../../components/navigation";
import { Button, Card, ErrorMessage, Loading, PageHeader, Stat, fmt } from "../../components/ui";
import type { Course, CourseAnalysis, CourseFields, GradingScheme, Id, Semester } from "../../types";
import AssessmentTable from "./AssessmentTable";
import GradeTargets from "./GradeTargets";
import OfficialResultCard from "./OfficialResultCard";

export default function CoursePage() {
  const { courseId } = useParams() as { courseId: Id };
  const navigate = useNavigate();
  const course = useApi<Course>(`/api/courses/${courseId}`);
  const analysis = useApi<CourseAnalysis>(`/api/courses/${courseId}/calculation`);
  const schemes = useApi<GradingScheme[]>("/api/grading-schemes?include_archived=true");
  const cameFrom = useCameFrom();
  const semester = useApi<Semester>(course.data ? `/api/semesters/${course.data.semester_id}` : null);
  const [editing, setEditing] = useState(false);
  const { run, error, busy } = useAction();

  if (!course.data || !analysis.data || !schemes.data) return <Loading error={course.error ?? analysis.error ?? schemes.error} />;
  const c = course.data;
  const a = analysis.data;
  const scheme = schemes.data.find((s) => s.id === c.grading_scheme_id);

  const refresh = () => {
    course.reload();
    analysis.reload();
  };
  const save = (fields: CourseFields) =>
    run(() => api.put(`/api/courses/${courseId}`, fields)).then((ok) => {
      if (ok) {
        setEditing(false);
        refresh();
      }
    });
  const duplicate = () =>
    run(async () => navigate(`/courses/${(await api.post<Course>(`/api/courses/${courseId}/duplicate`, {})).id}`));
  const remove = () =>
    confirm(`Delete ${c.course_code} and all its marks? This cannot be undone.`) &&
    run(() => api.delete(`/api/courses/${courseId}`)).then((ok) => ok && navigate(`/semesters/${c.semester_id}`));

  const semesterPath = `/semesters/${c.semester_id}`;
  const semesterLabel = semester.data?.label ?? "semester";

  return (
    <>
      <PageNav back={cameFrom ?? { to: semesterPath, label: semesterLabel }}
        crumbs={[{ label: "Semesters", to: "/semesters" }, { label: semesterLabel, to: semesterPath }, { label: `${c.course_code} · ${c.title}` }]} />
      <PageHeader
        title={`${c.course_code} · ${c.title}`}
        subtitle={<>
          {fmt(c.credits)} credits · {c.course_type_code ?? "no type"} · {c.category_code ?? "no category"}
          {!c.counts_towards_gpa && " · non-GPA"}
        </>}
        actions={<>
          <Button variant="secondary" onClick={() => setEditing(true)}>Edit</Button>
          <Button variant="secondary" onClick={duplicate} disabled={busy}>Duplicate</Button>
          <Button variant="danger" onClick={remove} disabled={busy}>Delete course</Button>
        </>}
      />
      <ErrorMessage message={error} />

      {editing && (
        <Card title="Edit course">
          <CourseForm initial={courseFields(c)} submitLabel="Save course" busy={busy} onSubmit={save} onCancel={() => setEditing(false)} />
        </Card>
      )}

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Marks so far" value={fmt(a.current_marks)} hint={`weighted, out of ${fmt(a.weightage_total)}`} />
        <Stat label="Maximum possible" value={fmt(a.maximum_possible_marks)} hint="if every pending assessment gets full marks" />
        <Stat label="Projected marks" value={fmt(a.projected_marks)} hint="if you keep scoring at your current rate" />
        <Stat label="Predicted grade" value={a.predicted_grade ?? "—"}
          hint={a.is_configuration_complete
            ? `${fmt(a.predicted_grade_point)} grade points`
            : `shown once weightages total 100 (now ${fmt(a.weightage_total)})`} />
      </div>

      <AssessmentTable course={c} onChange={refresh} />
      <GradeTargets course={c} analysis={a} />
      <OfficialResultCard course={c} scheme={scheme} predictedGrade={a.predicted_grade} onChange={refresh} />
    </>
  );
}
