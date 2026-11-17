import { useState, type FormEvent } from "react";
import type { Semester } from "../types";
import { Button, Field } from "./ui";

export type SemesterFields = Omit<Semester, "id">;

export const EMPTY_SEMESTER: SemesterFields = {
  semester_number: 1,
  semester_type: "regular",
  label: "",
  academic_year: null,
  status: "active",
};

export default function SemesterForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
  busy = false,
}: {
  initial: SemesterFields;
  submitLabel: string;
  onSubmit: (fields: SemesterFields) => void;
  onCancel?: () => void;
  busy?: boolean; // disables the submit button while saving, so a double click saves once
}) {
  const [fields, setFields] = useState(initial);
  const set = (changes: Partial<SemesterFields>) => setFields({ ...fields, ...changes });

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit({ ...fields, label: fields.label || `Semester ${fields.semester_number}` });
  }

  return (
    <form onSubmit={submit} className="flex flex-wrap items-end gap-3">
      <Field label="Semester number">
        <input type="number" min={1} max={30} required className="w-20" value={fields.semester_number}
          onChange={(e) => set({ semester_number: Number(e.target.value) })} />
      </Field>
      <Field label="Type">
        <select value={fields.semester_type} onChange={(e) => set({ semester_type: e.target.value as SemesterFields["semester_type"] })}>
          <option value="regular">Regular</option>
          <option value="summer">Summer</option>
          <option value="other">Other</option>
        </select>
      </Field>
      <Field label="Name">
        <input maxLength={200} placeholder={`Semester ${fields.semester_number}`} value={fields.label} onChange={(e) => set({ label: e.target.value })} />
      </Field>
      <Field label="Academic year">
        <input maxLength={20} placeholder="2024-25" className="w-28" value={fields.academic_year ?? ""}
          onChange={(e) => set({ academic_year: e.target.value || null })} />
      </Field>
      <Field label="Status">
        <select value={fields.status} onChange={(e) => set({ status: e.target.value as SemesterFields["status"] })}>
          <option value="planned">Planned</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
        </select>
      </Field>
      <Button type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</Button>
      {onCancel && <Button variant="secondary" onClick={onCancel}>Cancel</Button>}
    </form>
  );
}
