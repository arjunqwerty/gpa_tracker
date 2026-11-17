import { useState } from "react";
import { api, useAction } from "../../api";
import { Badge, Button, Card, ErrorMessage, Field, fmt, tableClass } from "../../components/ui";
import type { Course, CourseAnalysis, GradeTarget, TargetStatus } from "../../types";

const STATUS = {
  already_achieved: { tone: "green", text: "Already achieved" },
  achievable: { tone: "indigo", text: "Achievable" },
  not_achievable: { tone: "red", text: "Not achievable" },
  pending_configuration: { tone: "amber", text: "Needs weightages totalling 100" },
} as const satisfies Record<TargetStatus, { tone: string; text: string }>;

/** Marks needed for every grade, plus a "what if" simulator for the pending assessments. */
export default function GradeTargets({ course, analysis }: { course: Course; analysis: CourseAnalysis }) {
  const maximumByName = new Map(course.assessments.map((a) => [a.name, a.maximum_marks]));

  return (
    <Card title="What you need for each grade">
      <table className={tableClass}>
        <thead><tr><th>Grade</th><th>Minimum marks</th><th>Status</th><th>Needed on the pending assessments</th></tr></thead>
        <tbody>
          {analysis.targets.map((target) => (
            <tr key={target.grade}>
              <td className="font-semibold">{target.grade}</td>
              <td>{fmt(target.minimum_marks)}</td>
              <td><Badge tone={STATUS[target.status].tone}>{STATUS[target.status].text}</Badge></td>
              <td><RequiredMarks target={target} maximumByName={maximumByName} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      {analysis.targets.length === 0 && (
        <p className="text-sm text-slate-600">
          Its grading scheme has no minimum marks to work from. Add them under Settings → Grading scheme.
        </p>
      )}
      {analysis.pending_assessments.length > 0 && <Simulator course={course} />}
    </Card>
  );
}

function RequiredMarks({ target, maximumByName }: { target: GradeTarget; maximumByName: Map<string, number> }) {
  const entries = Object.entries(target.required_marks);
  if (entries.length === 0) return <span className="text-slate-500">—</span>;
  return (
    <span>
      {entries.map(([name, marks]) => `${name}: ${fmt(marks)} / ${fmt(maximumByName.get(name))}`).join(", ")}
      {entries.length > 1 && <span className="text-slate-500"> ({fmt(target.required_percentage, 1)}% on each)</span>}
    </span>
  );
}

function Simulator({ course }: { course: Course }) {
  const pending = course.assessments.filter((a) => a.status === "pending" || (a.status === "completed" && a.obtained_marks == null));
  const [marks, setMarks] = useState<Record<string, string>>({});
  const [result, setResult] = useState<CourseAnalysis>();
  const { run, error, busy } = useAction();

  const simulate = () =>
    run(async () => {
      const hypothetical = Object.fromEntries(Object.entries(marks).filter(([, v]) => v !== "").map(([id, v]) => [id, Number(v)]));
      setResult(await api.post<CourseAnalysis>(`/api/courses/${course.id}/simulate`, { marks: hypothetical }));
    });

  return (
    <div className="mt-6 border-t border-slate-100 pt-4">
      <h3 className="mb-3 text-sm font-semibold text-slate-700">Try some marks <span className="font-normal text-slate-500">(nothing is saved)</span></h3>
      <ErrorMessage message={error} />
      <div className="flex flex-wrap items-end gap-3">
        {pending.map((a) => (
          <Field key={a.id} label={`${a.name} (out of ${fmt(a.maximum_marks)})`}>
            <input type="number" min={0} max={a.allow_over_max ? undefined : a.maximum_marks} step="any" className="w-28"
              value={marks[a.id] ?? ""} onChange={(e) => setMarks({ ...marks, [a.id]: e.target.value })} />
          </Field>
        ))}
        <Button variant="secondary" onClick={simulate} disabled={busy}>Show the grade</Button>
      </div>
      {result && (
        <p className="mt-3 text-sm" aria-live="polite">
          With these marks you would have <strong>{fmt(result.current_marks)}</strong> weighted marks
          {result.pending_assessments.length > 0 && <>, projected to {fmt(result.projected_marks)} with the rest still to come</>}
          {result.predicted_grade
            ? <>: grade <strong>{result.predicted_grade}</strong> ({fmt(result.predicted_grade_point)} grade points).</>
            : <>. No grade can be predicted until the weightages total 100.</>}
        </p>
      )}
    </div>
  );
}
