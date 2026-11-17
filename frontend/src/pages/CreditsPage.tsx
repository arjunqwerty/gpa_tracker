import { Link } from "react-router-dom";
import { useApi } from "../api";
import { NavRow, OpenRowHint, RowLink, useFromHere } from "../components/navigation";
import { Card, Loading, PageHeader, ProgressBar, Stat, fmt, tableClass } from "../components/ui";
import type { CreditReport } from "../types";

export default function CreditsPage() {
  const { data, error } = useApi<CreditReport>("/api/credits/progress");
  const fromCredits = useFromHere("Credits");
  if (!data) return <Loading error={error} />;

  return (
    <>
      <PageHeader title="Credits" subtitle={data.curriculum
        ? `${data.curriculum.version_name} curriculum`
        : <>No curriculum chosen, so there are no requirements to track. Choose one in <Link className="text-indigo-700 hover:underline" to="/settings">Settings</Link>.</>} />

      <div className="mb-6 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat label="Earned" value={`${fmt(data.earned_credits)} / ${fmt(data.required_credits)}`} hint={`${fmt(data.completion_percentage, 1)}% complete`} />
        <Stat label={data.surplus_credits > 0 ? "Surplus" : "Remaining"}
          value={fmt(data.surplus_credits > 0 ? data.surplus_credits : data.remaining_credits)} />
        <Stat label="GPA credits" value={fmt(data.gpa_credits)} hint="earned credits that count in the CGPA" />
        <Stat label="Non-GPA credits" value={fmt(data.non_gpa_credits)} hint="e.g. pass/fail courses" />
      </div>

      {data.warnings.length > 0 && (
        <Card title={`${data.warnings.length} ${data.warnings.length === 1 ? "course needs" : "courses need"} attention`}>
          <ul className="space-y-1 text-sm">
            {data.warnings.map((w, i) => (
              <li key={i}>
                <Link className="font-medium text-indigo-700 hover:underline" to={`/courses/${w.course_id}`} state={fromCredits}>{w.course_code}</Link>
                {" "}{w.message}
              </li>
            ))}
          </ul>
        </Card>
      )}

      <Card title="By category">
        <table className={tableClass}>
          <thead><tr><th>Category</th><th>Required</th><th>Earned</th><th>Remaining</th><th>Progress</th></tr></thead>
          <tbody>
            {data.categories.map((c) => (
              <tr key={c.code}>
                <td><span className="font-medium">{c.code}</span> <span className="text-slate-500">{c.name}</span></td>
                <td>{fmt(c.required_credits)}</td>
                <td>{fmt(c.earned_credits)}</td>
                <td>{c.surplus_credits > 0 ? <span className="text-emerald-700">+{fmt(c.surplus_credits)} surplus</span> : fmt(c.remaining_credits)}</td>
                <td className="flex items-center gap-2">
                  {c.required_credits > 0
                    ? <><ProgressBar value={c.earned_credits} max={c.required_credits} className="w-40" /> <span className="tabular-nums">{fmt(c.completion_percentage, 0)}%</span></>
                    : <span className="text-slate-600">none required</span>}
                </td>
              </tr>
            ))}
            {data.uncategorised_credits > 0 && (
              <tr><td className="text-slate-500">Not in any curriculum category</td><td>—</td><td>{fmt(data.uncategorised_credits)}</td><td></td><td></td></tr>
            )}
          </tbody>
        </table>
      </Card>

      <Card title="By semester">
        <table className={tableClass}>
          {data.semesters.length > 0 && <OpenRowHint />}
          <thead><tr><th>Semester</th><th>Registered credits</th><th>Earned credits</th></tr></thead>
          <tbody>
            {data.semesters.map((s) => (
              <NavRow key={s.semester_id} to={`/semesters/${s.semester_id}`} from="Credits">
                <td><RowLink>{s.label}</RowLink></td>
                <td>{fmt(s.registered_credits)}</td>
                <td>{fmt(s.earned_credits)}</td>
              </NavRow>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
