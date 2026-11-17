import { useState, type FormEvent, type ReactNode } from "react";
import { useApi, useCurriculum } from "../api";
import type { Course, CourseFields, CourseType, Id, Semester } from "../types";
import { Button, Field } from "./ui";

export function emptyCourse(semesterId: Id): CourseFields {
  return {
    semester_id: semesterId,
    course_code: "",
    title: "",
    course_type_code: "TH",
    credits: 3,
    category_code: null,
    counts_towards_gpa: true,
    counts_towards_earned_credits: true,
    counts_towards_requirement: true,
    status: "in_progress",
    grading_scheme_id: null,
    attempt: 1,
  };
}

/** Create / edit a course. `children` adds extra fields (e.g. the grade for a history entry). */
export default function CourseForm({
  initial,
  submitLabel,
  onSubmit,
  onCancel,
  children,
  busy = false,
}: {
  initial: CourseFields;
  submitLabel: string;
  onSubmit: (fields: CourseFields) => void;
  onCancel?: () => void;
  children?: ReactNode;
  busy?: boolean; // disables the submit button while saving, so a double click saves once
}) {
  const [fields, setFields] = useState(initial);
  const set = (changes: Partial<CourseFields>) => setFields({ ...fields, ...changes });
  const semesters = useApi<Semester[]>("/api/semesters").data ?? [];
  const courseTypes = useApi<CourseType[]>("/api/course-types").data ?? [];
  const categories = useCurriculum().data?.categories ?? [];
  const categoryKnown = categories.some((c) => c.code === fields.category_code);

  function submit(event: FormEvent) {
    event.preventDefault();
    onSubmit(fields);
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Field label="Course code">
          <input required maxLength={20} value={fields.course_code} onChange={(e) => set({ course_code: e.target.value.toUpperCase() })} />
        </Field>
        <Field label="Title" className="col-span-2 md:col-span-3">
          <input required maxLength={200} value={fields.title} onChange={(e) => set({ title: e.target.value })} />
        </Field>
        <Field label="Course type">
          <input list="course-types" maxLength={20} value={fields.course_type_code ?? ""} onChange={(e) => set({ course_type_code: e.target.value || null })} />
          <datalist id="course-types">
            {courseTypes.map((t) => <option key={t.id} value={t.code}>{t.name}</option>)}
          </datalist>
        </Field>
        <Field label="Credits">
          <input type="number" min={0} max={50} step={0.5} required value={fields.credits} onChange={(e) => set({ credits: Number(e.target.value) })} />
        </Field>
        <Field label="Category">
          <select value={fields.category_code ?? ""} onChange={(e) => set({ category_code: e.target.value || null })}>
            <option value="">— none —</option>
            {categories.map((c) => <option key={c.code} value={c.code}>{c.code} · {c.name}</option>)}
            {fields.category_code && !categoryKnown && <option value={fields.category_code}>{fields.category_code}</option>}
          </select>
        </Field>
        <Field label="Semester">
          <select value={fields.semester_id} onChange={(e) => set({ semester_id: e.target.value })}>
            {semesters.map((s) => <option key={s.id} value={s.id}>{s.label}</option>)}
          </select>
        </Field>
        <Field label="Status">
          <select value={fields.status} onChange={(e) => set({ status: e.target.value as CourseFields["status"] })}>
            <option value="planned">Planned</option>
            <option value="in_progress">In progress</option>
            <option value="completed">Completed</option>
            <option value="failed">Failed</option>
            <option value="withdrawn">Withdrawn</option>
          </select>
        </Field>
        <Field label="Attempt">
          <input type="number" min={1} max={20} value={fields.attempt} onChange={(e) => set({ attempt: Number(e.target.value) })} />
        </Field>
      </div>
      <div className="flex flex-wrap gap-5 text-sm text-slate-600">
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={fields.counts_towards_gpa} onChange={(e) => set({ counts_towards_gpa: e.target.checked })} />
          Counts towards GPA
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={fields.counts_towards_earned_credits} onChange={(e) => set({ counts_towards_earned_credits: e.target.checked })} />
          Counts towards earned credits
        </label>
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={fields.counts_towards_requirement} onChange={(e) => set({ counts_towards_requirement: e.target.checked })} />
          Counts towards its category requirement
        </label>
      </div>
      {children}
      <div className="flex gap-2">
        <Button type="submit" disabled={busy}>{busy ? "Saving…" : submitLabel}</Button>
        {onCancel && <Button variant="secondary" onClick={onCancel}>Cancel</Button>}
      </div>
    </form>
  );
}

/** The editable part of a stored course, ready to pre-fill the form. */
export function courseFields(course: Course): CourseFields {
  const { semester_id, course_code, title, course_type_code, credits, category_code, counts_towards_gpa,
    counts_towards_earned_credits, counts_towards_requirement, status, grading_scheme_id, attempt } = course;
  return { semester_id, course_code, title, course_type_code, credits, category_code, counts_towards_gpa,
    counts_towards_earned_credits, counts_towards_requirement, status, grading_scheme_id, attempt };
}
