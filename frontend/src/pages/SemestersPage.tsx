import { useState } from "react";
import { Link } from "react-router-dom";
import { api, useAction, useApi } from "../api";
import { NavRow, OpenRowHint, PageNav, RowLink } from "../components/navigation";
import SemesterForm, { EMPTY_SEMESTER } from "../components/SemesterForm";
import { Badge, Button, Card, ErrorMessage, Loading, PageHeader, gpa as gpaText, tableClass } from "../components/ui";
import type { CgpaReport, Semester } from "../types";

const STATUS_TONE = { planned: "slate", active: "indigo", completed: "green" } as const;

export default function SemestersPage() {
  const semesters = useApi<Semester[]>("/api/semesters");
  const cgpa = useApi<CgpaReport>("/api/cgpa");
  const [adding, setAdding] = useState(false);
  const { run, error, busy } = useAction();

  if (!semesters.data || !cgpa.data) return <Loading error={semesters.error ?? cgpa.error} />;
  const gpaBySemester = new Map(cgpa.data.semesters.map((s) => [s.semester_id, s]));
  const nextNumber = Math.max(0, ...semesters.data.map((s) => s.semester_number)) + 1;

  const create = (fields: typeof EMPTY_SEMESTER) =>
    run(async () => {
      await api.post("/api/semesters", fields);
      setAdding(false);
      semesters.reload();
      cgpa.reload();
    });

  return (
    <>
      <PageNav crumbs={[{ label: "Semesters" }]} />
      <PageHeader title="Semesters" actions={!adding && <Button onClick={() => setAdding(true)}>New semester</Button>} />
      <ErrorMessage message={error} />
      {adding && (
        <Card title="New semester">
          <SemesterForm initial={{ ...EMPTY_SEMESTER, semester_number: nextNumber }} submitLabel="Create semester" busy={busy} onSubmit={create}
            onCancel={() => setAdding(false)} />
        </Card>
      )}
      <Card>
        <table className={tableClass}>
          {semesters.data.length > 0 && <OpenRowHint />}
          <thead>
            <tr><th>Semester</th><th className="hidden sm:table-cell">Type</th><th className="hidden sm:table-cell">Academic year</th><th>Status</th><th>GPA</th><th>Predicted GPA</th><th>CGPA after</th></tr>
          </thead>
          <tbody>
            {semesters.data.map((s) => {
              const gpa = gpaBySemester.get(s.id);
              return (
                <NavRow key={s.id} to={`/semesters/${s.id}`} from="Semesters">
                  <td><RowLink>{s.label}</RowLink></td>
                  <td className="hidden capitalize sm:table-cell">{s.semester_type}</td>
                  <td className="hidden sm:table-cell">{s.academic_year ?? "—"}</td>
                  <td><Badge tone={STATUS_TONE[s.status]}>{s.status}</Badge></td>
                  <td>{gpaText(gpa?.confirmed_gpa)}</td>
                  <td>{gpaText(gpa?.predicted_gpa)}</td>
                  {/* A semester without confirmed results doesn't move the CGPA, so repeating it would mislead. */}
                  <td>{gpa?.confirmed_gpa != null || s.status === "completed" ? gpaText(gpa?.confirmed_cgpa) : "—"}</td>
                </NavRow>
              );
            })}
          </tbody>
        </table>
        {semesters.data.length === 0 && (
          <p className="text-sm text-slate-600">
            No semesters yet. Create one with New semester, or bring in your VTOP grade history on{" "}
            <Link className="text-indigo-700 hover:underline" to="/import-export">Import &amp; export</Link>.
          </p>
        )}
      </Card>
    </>
  );
}
