import { useState } from "react";
import { api, useAction } from "../../api";
import { Badge, Button, Card, ErrorMessage, Field, dayLabel, fmt, monthLabel } from "../../components/ui";
import type { Course, GradingScheme, OfficialResult } from "../../types";

/** The declared grade: record it (provisional), then confirm it once checked. */
export default function OfficialResultCard({ course, scheme, predictedGrade, onChange }: {
  course: Course;
  scheme: GradingScheme | undefined;
  predictedGrade: string | null;
  onChange: () => void;
}) {
  const result = course.official_result;
  const [editing, setEditing] = useState(false);
  const { run, error, busy } = useAction();
  const act = (action: () => Promise<unknown>) => run(action).then((ok) => {
    if (ok) {
      setEditing(false);
      onChange();
    }
  });

  const confirmResult = () => act(() => api.post(`/api/courses/${course.id}/official-result/confirm`));
  const removeResult = () => act(() => api.delete(`/api/courses/${course.id}/official-result`));

  return (
    <Card title="Official result">
      <ErrorMessage message={error} />
      {result && !editing && (
        <div className="flex flex-wrap items-center gap-4">
          <span className="text-3xl font-bold">{result.grade}</span>
          <Badge tone={result.result_status === "confirmed" ? "green" : "amber"}>{result.result_status}</Badge>
          <span className="text-sm text-slate-600">
            {fmt(result.grade_point)} grade points × {fmt(result.credits)} credits
            {result.exam_month && ` · exams ${monthLabel(result.exam_month)}`}
            {result.result_date && ` · declared ${dayLabel(result.result_date)}`}
            {` · grading scheme v${result.grading_scheme_version}`}
          </span>
          <div className="ml-auto flex gap-2">
            {result.result_status === "provisional" && <>
              <Button onClick={confirmResult} disabled={busy}>Confirm result</Button>
              <Button variant="danger" onClick={removeResult} disabled={busy}>Remove result</Button>
            </>}
            <Button variant="secondary" onClick={() => setEditing(true)}>
              {result.result_status === "confirmed" ? "Correct confirmed result" : "Change grade"}
            </Button>
          </div>
        </div>
      )}
      {(!result || editing) && (
        <ResultForm
          key={predictedGrade ?? ""} // re-initialise when the prediction changes
          grades={scheme?.entries.map((e) => e.grade) ?? []}
          current={result}
          predictedGrade={predictedGrade}
          busy={busy}
          onSubmit={(body) => act(() => api.put(`/api/courses/${course.id}/official-result`, body))}
          onCancel={editing ? () => setEditing(false) : undefined}
        />
      )}
      {!result && (
        <p className="mt-3 text-xs text-slate-600">
          Record the grade as provisional when results are declared, then confirm it once you have checked it on VTOP.
          Only confirmed results count towards your confirmed GPA.
        </p>
      )}
      {result?.result_status === "provisional" && !editing && (
        <p className="mt-3 text-xs text-slate-600">Provisional: counted in predicted figures only. Confirm it once you have checked it on VTOP.</p>
      )}
    </Card>
  );
}

function ResultForm({ grades, current, predictedGrade, busy, onSubmit, onCancel }: {
  busy: boolean;
  grades: string[];
  current: OfficialResult | null; // pre-fills the form when correcting a result
  predictedGrade: string | null;
  onSubmit: (body: object) => void;
  onCancel?: () => void;
}) {
  const [grade, setGrade] = useState(current?.grade ?? predictedGrade ?? grades[0] ?? "");
  const [examMonth, setExamMonth] = useState(current?.exam_month?.slice(0, 7) ?? "");
  const [resultDate, setResultDate] = useState(current?.result_date?.slice(0, 10) ?? "");

  const submit = () =>
    onSubmit({
      grade,
      exam_month: examMonth ? `${examMonth}-01` : null,
      result_date: resultDate || null,
      source: grade === predictedGrade ? "generated" : "manual",
    });

  return (
    <div className="flex flex-wrap items-end gap-3">
      <Field label="Grade">
        <select value={grade} onChange={(e) => setGrade(e.target.value)}>
          {grades.map((g) => <option key={g} value={g}>{g}{g === predictedGrade ? " (predicted)" : ""}</option>)}
        </select>
      </Field>
      <Field label="Exam month"><input type="month" value={examMonth} onChange={(e) => setExamMonth(e.target.value)} /></Field>
      <Field label="Result declared"><input type="date" value={resultDate} onChange={(e) => setResultDate(e.target.value)} /></Field>
      <Button onClick={submit} disabled={!grade || busy}>{busy ? "Saving…" : "Record provisional result"}</Button>
      {onCancel && <Button variant="secondary" onClick={onCancel}>Cancel</Button>}
    </div>
  );
}
