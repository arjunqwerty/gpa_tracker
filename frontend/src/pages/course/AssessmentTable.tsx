import { useState, type FormEvent } from "react";
import { api, useAction } from "../../api";
import { Button, Card, ErrorMessage, RemoveButton, UnsavedNote, fmt, tableClass } from "../../components/ui";
import type { Assessment, AssessmentStatus, Course } from "../../types";

type Draft = Omit<Assessment, "id">;

export default function AssessmentTable({ course, onChange }: { course: Course; onChange: () => void }) {
  const totalWeightage = course.assessments.reduce((sum, a) => sum + a.weightage, 0);

  return (
    <Card title="Assessments">
      <table className={tableClass}>
        <thead>
          <tr><th>Name</th><th>Max marks</th><th>Weightage</th><th>Obtained</th><th>Status</th><th>Weighted</th><th></th></tr>
        </thead>
        <tbody>
          {course.assessments.map((a) => <AssessmentRow key={a.id} courseId={course.id} assessment={a} onChange={onChange} />)}
          <NewAssessmentRow courseId={course.id} onChange={onChange} />
        </tbody>
        <tfoot className="border-t border-slate-200 font-medium">
          <tr>
            <td className="px-2 py-2">Total</td>
            <td></td>
            <td className={`px-2 ${totalWeightage === 100 ? "" : "text-amber-800"}`}>
              {fmt(totalWeightage)}{totalWeightage !== 100 && " · must total 100 before a grade can be predicted"}
            </td>
            <td colSpan={4}></td>
          </tr>
        </tfoot>
      </table>
      <p className="mt-3 text-xs text-slate-600">Edit any cell, then press Enter or Save. Escape discards the edits to a row.</p>
    </Card>
  );
}

function AssessmentRow({ courseId, assessment, onChange }: { courseId: string; assessment: Assessment; onChange: () => void }) {
  const { id, ...saved } = assessment;
  const [draft, setDraft] = useState<Draft>(saved);
  const { run, error, busy } = useAction();
  const dirty = JSON.stringify(draft) !== JSON.stringify(saved);
  const set = (changes: Partial<Draft>) => setDraft({ ...draft, ...changes });

  // Typing marks marks the assessment completed; clearing them makes it pending again.
  const setObtained = (value: string) =>
    set({
      obtained_marks: value === "" ? null : Number(value),
      status: value === "" ? (draft.status === "completed" ? "pending" : draft.status) : "completed",
    });

  const save = () => run(() => api.put(`/api/courses/${courseId}/assessments/${id}`, draft)).then((ok) => ok && onChange());
  const remove = () =>
    confirm(`Delete ${saved.name} and its marks?`) &&
    run(() => api.delete(`/api/courses/${courseId}/assessments/${id}`)).then((ok) => ok && onChange());
  const weighted = draft.status === "completed" && draft.obtained_marks != null
    ? (draft.obtained_marks * draft.weightage) / draft.maximum_marks : null;

  // Enter saves the row, Escape throws the edits away.
  const keys = (event: React.KeyboardEvent) => {
    if (event.key === "Enter" && dirty) save();
    if (event.key === "Escape") setDraft(saved);
  };

  return (
    <>
      <tr onKeyDown={keys} className={dirty ? "bg-amber-50" : ""}>
        <td><input className="w-36" value={draft.name} onChange={(e) => set({ name: e.target.value })} /></td>
        <td><input type="number" min={0} step="any" className="w-20" value={draft.maximum_marks} onChange={(e) => set({ maximum_marks: Number(e.target.value) })} /></td>
        <td><input type="number" min={0} step="any" className="w-20" value={draft.weightage} onChange={(e) => set({ weightage: Number(e.target.value) })} /></td>
        <td><input type="number" min={0} step="any" className="w-20" value={draft.obtained_marks ?? ""} onChange={(e) => setObtained(e.target.value)} /></td>
        <td>
          <select value={draft.status} onChange={(e) => set({ status: e.target.value as AssessmentStatus })}>
            <option value="pending">Pending</option>
            <option value="completed">Completed</option>
            <option value="absent">Absent</option>
            <option value="exempted">Exempted</option>
          </select>
        </td>
        <td>{fmt(weighted)}</td>
        <td className="whitespace-nowrap text-right">
          {dirty ? (
            <span className="inline-flex items-center gap-2">
              <UnsavedNote />
              <Button onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</Button>
              <Button variant="secondary" onClick={() => setDraft(saved)} disabled={busy}>Discard</Button>
            </span>
          ) : (
            <RemoveButton label={`Delete ${saved.name}`} onClick={remove} disabled={busy} />
          )}
        </td>
      </tr>
      {error && <tr><td colSpan={7}><ErrorMessage message={error} /></td></tr>}
    </>
  );
}

const NEW_ASSESSMENT = { name: "", maximum_marks: "", weightage: "" };

function NewAssessmentRow({ courseId, onChange }: { courseId: string; onChange: () => void }) {
  const [draft, setDraft] = useState(NEW_ASSESSMENT);
  const { run, error, busy } = useAction();

  const add = (event: FormEvent) => {
    event.preventDefault();
    const body = { name: draft.name, maximum_marks: Number(draft.maximum_marks), weightage: Number(draft.weightage) };
    run(() => api.post(`/api/courses/${courseId}/assessments`, body)).then((ok) => {
      if (ok) {
        setDraft(NEW_ASSESSMENT);
        onChange();
      }
    });
  };

  return (
    <>
      <tr>
        <td><input form="new-assessment" required placeholder="e.g. CAT 1" aria-label="New assessment name" className="w-36" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} /></td>
        <td><input form="new-assessment" required type="number" min={0} step="any" placeholder="e.g. 50" aria-label="New assessment maximum marks" className="w-20" value={draft.maximum_marks} onChange={(e) => setDraft({ ...draft, maximum_marks: e.target.value })} /></td>
        <td><input form="new-assessment" required type="number" min={0} step="any" placeholder="e.g. 15" aria-label="New assessment weightage" className="w-20" value={draft.weightage} onChange={(e) => setDraft({ ...draft, weightage: e.target.value })} /></td>
        <td colSpan={3}></td>
        <td className="text-right">
          <form id="new-assessment" onSubmit={add}><Button type="submit" variant="secondary" disabled={busy}>{busy ? "Adding…" : "Add assessment"}</Button></form>
        </td>
      </tr>
      {error && <tr><td colSpan={7}><ErrorMessage message={error} /></td></tr>}
    </>
  );
}
