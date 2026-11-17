import { useState } from "react";
import { api, useAction } from "../api";
import { ButtonLink } from "../components/navigation";
import { Badge, Button, Card, ErrorMessage, PageHeader, buttonClass, fmt, tableClass } from "../components/ui";
import type { ImportJob } from "../types";

const DOWNLOADS = [
  { href: "/api/export/summary.pdf", label: "Academic summary", detail: "PDF with CGPA, every semester and credit progress" },
  { href: "/api/export/workbook.xlsx", label: "Full record (Excel)", detail: "Semesters, courses, marks and requirements; can be imported again" },
  { href: "/api/export/grade-history.xlsx", label: "Grade history (Excel)", detail: "Confirmed results in VTOP's layout" },
  { href: "/api/export/grade-history.csv", label: "Grade history (CSV)", detail: "Same as above, as CSV" },
  { href: "/api/export/credits.csv", label: "Credit progress (CSV)", detail: "Required, earned and remaining credits per category" },
  { href: "/api/export/full.json", label: "Full backup (JSON)", detail: "Every record you own, including the audit log" },
];

export default function ImportExportPage() {
  return (
    <>
      <PageHeader title="Import & export" />
      <ImportCard />
      <Card title="Export">
        <ul className="divide-y divide-slate-100">
          {DOWNLOADS.map((d) => (
            <li key={d.href} className="flex items-center justify-between gap-4 py-2">
              <div>
                <div className="font-medium text-slate-800">{d.label}</div>
                <div className="text-xs text-slate-500">{d.detail}</div>
              </div>
              <a className={buttonClass("secondary", "shrink-0")} href={d.href} download aria-label={`Download ${d.label}`}>Download</a>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-xs text-slate-500">A PDF report for a single semester is available on each semester's page.</p>
      </Card>
    </>
  );
}

const plural = (count: number, noun: string) => `${count} ${noun}${count === 1 ? "" : "s"}`;

function ImportCard() {
  const [file, setFile] = useState<File>();
  const [job, setJob] = useState<ImportJob>();
  const { run, error, busy } = useAction();

  const upload = () =>
    run(async () => {
      if (file!.size > 5 * 1024 * 1024) throw new Error("This file is larger than 5 MB. Remove unused sheets or images and try again.");
      const form = new FormData();
      form.append("file", file!);
      setJob(await api.post<ImportJob>("/api/import", form));
    });
  const commit = () => run(async () => setJob(await api.post<ImportJob>(`/api/import/${job!.id}/commit`)));

  return (
    <Card title="Import from Excel">
      <p className="mb-3 text-sm text-slate-600">
        Upload a workbook with any of these sheets: <em>Semesters</em>, <em>Courses</em>, <em>Assessments</em>,{" "}
        <em>Requirements</em>, or a <em>Grade history</em> sheet copied straight from VTOP.{" "}
        <a className="text-indigo-700 hover:underline" href="/api/import/template.xlsx" download>Download the template</a>.
        You will see a preview before anything is saved.
      </p>
      <ErrorMessage message={error} />
      <div className="flex flex-wrap items-center gap-3">
        <input type="file" accept=".xlsx" aria-label="Excel workbook to import"
          className="max-w-full border-0 p-0 text-sm text-slate-700 file:mr-3 file:cursor-pointer file:rounded-md file:border file:border-slate-300 file:bg-white file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-slate-700 hover:file:bg-slate-50" onChange={(e) => { setFile(e.target.files?.[0]); setJob(undefined); }} />
        <Button onClick={upload} disabled={!file || busy}>{busy ? "Checking…" : "Check file"}</Button>
      </div>
      {job && <ImportPreview job={job} onCommit={commit} busy={busy} />}
    </Card>
  );
}

function ImportPreview({ job, onCommit, busy }: { job: ImportJob; onCommit: () => void; busy: boolean }) {
  const { semesters, courses, marks_for_existing_courses, requirements } = job.preview;
  const marksCount = Object.values(marks_for_existing_courses).reduce((sum, list) => sum + list.length, 0);

  if (job.status === "committed") {
    return (
      <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
        <p>Imported {plural(courses.length, "course")} and {plural(semesters.length, "new semester")}.</p>
        <div className="mt-2"><ButtonLink to="/">See your dashboard</ButtonLink></div>
      </div>
    );
  }

  return (
    <div className="mt-5 space-y-4">
      <div className="flex flex-wrap items-center gap-2 text-sm">
        <Badge tone={job.status === "validated" ? "green" : "red"}>{job.status === "validated" ? "ready to import" : "has errors"}</Badge>
        {plural(semesters.length, "new semester")} · {plural(courses.length, "course")} · {plural(marksCount, "mark")} for existing courses
        {" "}· {plural(requirements.length, "credit requirement")}
      </div>

      {job.errors.length > 0 && (
        <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <div className="mb-1 font-medium">Fix these in the file and upload it again:</div>
          <ul className="list-disc pl-5">{job.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
        </div>
      )}
      {job.warnings.length > 0 && (
        <ul className="list-disc rounded-md border border-amber-200 bg-amber-50 py-2 pl-8 pr-3 text-sm text-amber-800">
          {job.warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}

      {courses.length > 0 && (
        <div className="max-h-80 overflow-y-auto">
          <table className={tableClass}>
            <thead><tr><th>Semester</th><th>Code</th><th>Title</th><th>Credits</th><th>Category</th><th>Grade</th><th>Assessments</th></tr></thead>
            <tbody>
              {courses.map((c, i) => (
                <tr key={i}>
                  <td>{c.semester}</td><td>{c.course_code}</td><td>{c.title}</td><td>{fmt(c.credits)}</td>
                  <td>{c.category_code ?? "—"}</td><td>{c.grade ?? "—"}</td><td>{c.assessments.length || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Button onClick={onCommit} disabled={job.status !== "validated" || busy}>
        {job.status === "validated" ? `Import ${plural(courses.length, "course")}` : "Fix the errors to import"}
      </Button>
    </div>
  );
}
