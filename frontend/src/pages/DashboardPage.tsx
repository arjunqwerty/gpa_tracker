// The whole record at a glance, in three parts: standing (CGPA, trend, target), credits, and the record.
// Confirmed and predicted figures are kept visibly apart everywhere on this page.
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, useApi } from "../api";
import { CreditsBySemesterChart, GpaTrendChart, GradeDistributionChart } from "../components/charts";
import { NavRow, OpenRowHint, RowLink } from "../components/navigation";
import { Badge, Button, Card, ErrorMessage, Field, ProgressBar, Skeleton, fmt, gpa, tableClass, usePageTitle } from "../components/ui";
import type { CgpaReport, CreditReport, GradeDistribution, GradingScheme, ProfileData, TargetCgpa } from "../types";

const linkClass = "text-indigo-700 hover:underline";

export default function DashboardPage() {
  const cgpa = useApi<CgpaReport>("/api/cgpa");
  const credits = useApi<CreditReport>("/api/credits/progress");
  const profile = useApi<ProfileData>("/api/profile");
  const grades = useApi<GradeDistribution>("/api/dashboard/grade-distribution");

  usePageTitle("Academic record");
  const name = profile.data?.profile.full_name;
  const curriculum = credits.data?.curriculum?.version_name;

  return (
    <>
      <header className="mb-6">
        <h1 className="text-2xl font-semibold text-slate-900">Academic record</h1>
        <p className="mt-1 text-sm text-slate-600">
          {[name, curriculum && `${curriculum} curriculum`].filter(Boolean).join(" · ") || " "}
        </p>
      </header>

      <SectionHeading>Standing</SectionHeading>
      {cgpa.data && credits.data && profile.data ? (
        <>
          <StandingPanel cgpa={cgpa.data} credits={credits.data} target={profile.data.settings.target_cgpa} />
          {cgpa.data.semesters.length > 0 && (
            <div className="grid gap-x-6 lg:grid-cols-3">
              <Card title="GPA and CGPA by semester" level={3} className="lg:col-span-2">
                <GpaTrendChart report={cgpa.data} target={profile.data.settings.target_cgpa} />
              </Card>
              <TargetPlanner profile={profile.data} defaultRemaining={credits.data.remaining_credits} onSaved={profile.reload} />
            </div>
          )}
        </>
      ) : (
        <Pending error={cgpa.error ?? credits.error ?? profile.error} className="mb-6 h-44" />
      )}

      <SectionHeading>Credits</SectionHeading>
      {credits.data ? (
        <div className="grid gap-x-6 lg:grid-cols-2">
          <Card title="Credits by category" level={3}>
            <CategoryProgressList credits={credits.data} />
          </Card>
          <Card title="Credits by semester" level={3}>
            {credits.data.semesters.length > 0
              ? <CreditsBySemesterChart semesters={credits.data.semesters} />
              : <p className="text-sm text-slate-600">Credits appear here once you add semesters.</p>}
            <p className="mt-2 text-xs text-slate-600">
              {fmt(credits.data.gpa_credits)} of the {fmt(credits.data.earned_credits)} earned credits count towards the
              CGPA; {fmt(credits.data.non_gpa_credits)} are non-GPA credits (pass/fail courses).
            </p>
          </Card>
        </div>
      ) : (
        <Pending error={credits.error} className="mb-6 h-64" />
      )}

      <SectionHeading>Record</SectionHeading>
      {cgpa.data && grades.data && credits.data ? (
        <div className="grid gap-x-6 lg:grid-cols-3">
          <Card title="Semesters" level={3} className="lg:col-span-2">
            <SemesterTable report={cgpa.data} />
          </Card>
          <Card title="Confirmed grades" level={3}>
            {Object.keys(grades.data.overall).length > 0 ? (
              <>
                <GradeDistributionChart grades={grades.data.grades} counts={grades.data.overall} />
                <GradeBreakdown grades={grades.data} categoryNames={Object.fromEntries(credits.data.categories.map((c) => [c.code, c.name]))} />
              </>
            ) : (
              <p className="text-sm text-slate-600">No confirmed grades yet.</p>
            )}
          </Card>
        </div>
      ) : (
        <Pending error={cgpa.error ?? grades.error ?? credits.error} className="mb-6 h-64" />
      )}
    </>
  );
}

function SectionHeading({ children }: { children: string }) {
  return <h2 className="mb-3 mt-2 text-lg font-semibold text-slate-900">{children}</h2>;
}

/** Placeholder while a section loads; that section's error if its data could not be loaded. */
function Pending({ error, className }: { error?: string; className: string }) {
  return error ? <ErrorMessage message={`This part could not be loaded: ${error}`} /> : <Skeleton className={className} />;
}

// --- Standing -------------------------------------------------------------------------------

function StandingPanel({ cgpa, credits, target }: { cgpa: CgpaReport; credits: CreditReport; target: number | null }) {
  const confirmed = cgpa.confirmed.cgpa;
  if (confirmed == null && cgpa.predicted.cgpa == null) {
    return (
      <Card>
        <p className="font-medium text-slate-900">No results yet.</p>
        <p className="mt-1 text-sm text-slate-600">
          Bring in your record from VTOP on <Link className={linkClass} to="/import-export">Import &amp; export</Link>, or
          {" "}<Link className={linkClass} to="/semesters">add a semester</Link> and its courses by hand.
        </p>
      </Card>
    );
  }

  const confirmedSemesters = cgpa.semesters.filter((s) => s.confirmed_gpa != null);
  const latest = confirmedSemesters.at(-1);
  const before = confirmedSemesters.at(-2);
  const inProgress = cgpa.semesters.filter((s) => s.confirmed_gpa == null && s.predicted_gpa != null);
  const registered = Object.fromEntries(credits.semesters.map((s) => [s.semester_id, s.registered_credits]));
  const inProgressCredits = inProgress.reduce((sum, s) => sum + (registered[s.semester_id] ?? 0), 0);
  const gap = confirmed != null && target != null ? confirmed - target : null;

  return (
    <section className="mb-6 grid rounded-lg border border-slate-200 bg-white shadow-sm md:grid-cols-[1.4fr_1fr_1fr] md:divide-x divide-y md:divide-y-0 divide-slate-200">
      <div className="p-5">
        <div className="flex items-center gap-2 text-sm text-slate-600">CGPA <Badge tone="green">confirmed</Badge></div>
        <div className="mt-1 text-5xl font-semibold tracking-tight text-slate-900 tabular-nums">{gpa(confirmed)}</div>
        <p className="mt-2 text-sm text-slate-600">Over {fmt(cgpa.confirmed.gpa_credits)} GPA credits.</p>
        {gap != null && (
          <p className={`mt-1 text-sm font-medium ${gap >= 0 ? "text-emerald-800" : "text-amber-800"}`}>
            {gap >= 0 ? `At or above your ${gpa(target)} target` : `${gpa(-gap)} below your ${gpa(target)} target`}
          </p>
        )}
        {latest && (
          <p className="mt-3 text-sm text-slate-600">
            Latest semester: <span className="font-medium text-slate-900 tabular-nums">{gpa(latest.confirmed_gpa)}</span> GPA
            in <Link className={linkClass} to={`/semesters/${latest.semester_id}`}>{latest.label}</Link>
            {before?.confirmed_gpa != null && latest.confirmed_gpa != null && (
              <> ({latest.confirmed_gpa >= before.confirmed_gpa ? "up" : "down"} {gpa(Math.abs(latest.confirmed_gpa - before.confirmed_gpa))} on {before.label})</>
            )}
          </p>
        )}
      </div>

      <div className="p-5">
        <div className="flex items-center gap-2 text-sm text-slate-600">CGPA <Badge tone="indigo">predicted</Badge></div>
        <div className="mt-1 text-3xl font-medium tracking-tight text-slate-700 tabular-nums">{gpa(cgpa.predicted.cgpa)}</div>
        {inProgress.length > 0 ? (
          <p className="mt-2 text-sm text-slate-600">
            If {inProgress.map((s, i) => (
              <span key={s.semester_id}>
                {i > 0 && " and "}
                <Link className={linkClass} to={`/semesters/${s.semester_id}`}>{s.label}</Link> ends at its predicted{" "}
                <span className="tabular-nums">{gpa(s.predicted_gpa)}</span> GPA
              </span>
            ))}. Each course is predicted from its marks so far.
          </p>
        ) : (
          <p className="mt-2 text-sm text-slate-600">Includes provisional results; nothing is in progress.</p>
        )}
      </div>

      <div className="p-5">
        <div className="text-sm text-slate-600">Credits earned</div>
        <div className="mt-1 text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">
          {fmt(credits.earned_credits)}<span className="text-lg font-normal text-slate-500"> / {fmt(credits.required_credits)}</span>
        </div>
        <ProgressBar value={credits.earned_credits} max={credits.required_credits} />
        <p className="mt-2 text-sm text-slate-600">
          {fmt(credits.remaining_credits)} to go{inProgressCredits > 0 && <>, {fmt(inProgressCredits)} in progress</>}.{" "}
          <Link className={linkClass} to="/credits">Credit details</Link>
        </p>
      </div>
    </section>
  );
}

/** What average GPA the remaining credits need for a target CGPA, worked out as you type. */
function TargetPlanner({ profile, defaultRemaining, onSaved }: { profile: ProfileData; defaultRemaining: number; onSaved: () => void }) {
  const saved = profile.settings.target_cgpa;
  const [target, setTarget] = useState(String(saved ?? 9));
  const [remaining, setRemaining] = useState(String(defaultRemaining));
  const [result, setResult] = useState<TargetCgpa>();
  const [error, setError] = useState<string>();
  const schemes = useApi<GradingScheme[]>("/api/grading-schemes");
  const scheme = schemes.data?.find((s) => s.id === profile.settings.default_grading_scheme_id);

  const valid = target !== "" && Number(target) > 0 && Number(target) <= 10 && remaining !== "" && Number(remaining) >= 0;
  useEffect(() => {
    if (!valid) return;
    const timer = setTimeout(() => {
      api.post<TargetCgpa>("/api/cgpa/target", { target_cgpa: Number(target), remaining_credits: Number(remaining) })
        .then((r) => { setResult(r); setError(undefined); }, (e: Error) => setError(e.message));
    }, 250);
    return () => clearTimeout(timer);
  }, [target, remaining, valid]);

  const saveTarget = () =>
    api.put("/api/profile", { ...profile, settings: { ...profile.settings, target_cgpa: Number(target) } }).then(onSaved, (e: Error) => setError(e.message));

  return (
    <Card title="Reaching a target" level={3}>
      <div className="grid grid-cols-2 gap-3">
        <Field label="Target CGPA">
          <input type="number" step={0.01} min={0.01} max={10} value={target} onChange={(e) => setTarget(e.target.value)} />
        </Field>
        <Field label="Credits still to take">
          <input type="number" min={0} step={0.5} value={remaining} onChange={(e) => setRemaining(e.target.value)} />
        </Field>
      </div>
      <div className="mt-4 min-h-24" aria-live="polite">
        <ErrorMessage message={error} />
        {!valid && <p className="text-sm text-slate-600">Enter a target between 0 and 10 and the credits you still have to take.</p>}
        {valid && result && <TargetAnswer result={result} scheme={scheme} />}
      </div>
      {valid && Number(target) !== saved && (
        <Button variant="secondary" onClick={saveTarget}>Save {gpa(Number(target))} as my target</Button>
      )}
    </Card>
  );
}

function TargetAnswer({ result, scheme }: { result: TargetCgpa; scheme?: GradingScheme }) {
  if (result.status === "already_achieved") {
    return <p className="text-sm text-emerald-800">Already secured: your CGPA stays at or above {gpa(result.target_cgpa)} whatever you score from here.</p>;
  }
  if (result.status === "not_achievable") {
    return (
      <p className="text-sm text-amber-800">
        Out of reach with {fmt(result.remaining_credits)} credits left. The highest CGPA still possible is{" "}
        <strong className="tabular-nums">{gpa(result.highest_reachable_cgpa)}</strong>, with the top grade in every remaining course.
      </p>
    );
  }
  return (
    <>
      <p className="text-sm text-slate-600">Average GPA needed over the next {fmt(result.remaining_credits)} credits</p>
      <p className="text-3xl font-semibold tracking-tight text-slate-900 tabular-nums">{gpa(result.required_gpa)}</p>
      {scheme && result.required_gpa != null && <p className="mt-1 text-sm text-slate-600">{gradeHint(result.required_gpa, scheme)}</p>}
    </>
  );
}

/** Puts a required GPA in grade terms using the user's own grading scheme, e.g. "Between A (9) and S (10) on average." */
function gradeHint(required: number, scheme: GradingScheme): string {
  const ladder = scheme.entries.filter((e) => e.minimum_marks != null && e.grade_point > 0).sort((a, b) => b.grade_point - a.grade_point);
  const above = [...ladder].reverse().find((e) => e.grade_point >= required);
  const below = ladder.find((e) => e.grade_point < required);
  if (!above) return "";
  if (above.grade_point === required || !below) return `A straight ${above.grade} (${above.grade_point}) average.`;
  return `Between ${below.grade} (${below.grade_point}) and ${above.grade} (${above.grade_point}) on average.`;
}

// --- Credits --------------------------------------------------------------------------------

/** Earned against required credits for each curriculum category, with the full category names. */
function CategoryProgressList({ credits }: { credits: CreditReport }) {
  if (credits.categories.length === 0) {
    return <p className="text-sm text-slate-600">Choose a curriculum in <Link className={linkClass} to="/settings">Settings</Link> to track credits by category.</p>;
  }
  return (
    <ul className="space-y-3">
      {credits.categories.map((c) => (
        <li key={c.code}>
          <div className="flex items-baseline justify-between gap-3 text-sm">
            <span className="min-w-0 text-slate-800">
              {c.name} <span className="text-xs text-slate-500">{c.code}</span>
            </span>
            <span className="shrink-0 tabular-nums text-slate-600">
              {c.required_credits > 0
                ? <><span className="font-medium text-slate-900">{fmt(c.earned_credits)}</span> / {fmt(c.required_credits)}</>
                : "none required"}
            </span>
          </div>
          {c.required_credits > 0 && <ProgressBar value={c.earned_credits} max={c.required_credits} />}
        </li>
      ))}
    </ul>
  );
}

// --- Record ---------------------------------------------------------------------------------

function SemesterTable({ report }: { report: CgpaReport }) {
  if (report.semesters.length === 0) {
    return <p className="text-sm text-slate-600">No semesters yet. <Link className={linkClass} to="/semesters">Add your first semester</Link>.</p>;
  }
  return (
    <table className={tableClass}>
      <OpenRowHint />
      <thead>
        <tr><th>Semester</th><th className="text-right">GPA</th><th className="text-right">CGPA after</th><th className="text-right">GPA credits</th><th /></tr>
      </thead>
      <tbody>
        {report.semesters.map((s) => {
          const predictedOnly = s.confirmed_gpa == null && s.predicted_gpa != null;
          return (
            <NavRow key={s.semester_id} to={`/semesters/${s.semester_id}`} from="Dashboard">
              <td><RowLink>{s.label}</RowLink></td>
              <td className={`text-right ${predictedOnly ? "text-indigo-800" : ""}`}>{gpa(predictedOnly ? s.predicted_gpa : s.confirmed_gpa)}</td>
              <td className={`text-right ${predictedOnly ? "text-indigo-800" : ""}`}>{gpa(predictedOnly ? s.predicted_cgpa : s.confirmed_cgpa)}</td>
              <td className="text-right">{predictedOnly ? "—" : fmt(s.gpa_credits)}</td>
              <td className="text-right">
                {predictedOnly && <Badge tone="indigo">predicted</Badge>}
                {s.confirmed_gpa == null && !predictedOnly && <span className="text-xs text-slate-500">non-GPA only</span>}
              </td>
            </NavRow>
          );
        })}
      </tbody>
    </table>
  );
}

/** Grade counts per category and course type, folded away until asked for. */
function GradeBreakdown({ grades, categoryNames }: { grades: GradeDistribution; categoryNames: Record<string, string> }) {
  return (
    <details className="mt-4 text-sm">
      <summary className="cursor-pointer text-indigo-700">Counts by category and course type</summary>
      <div className="mt-3 space-y-4">
        <GradeTable title="Category" grades={grades.grades} rows={grades.by_category} names={categoryNames} />
        <GradeTable title="Course type" grades={grades.grades} rows={grades.by_course_type} />
      </div>
    </details>
  );
}

function GradeTable({ title, grades, rows, names = {} }: {
  title: string;
  grades: string[];
  rows: Record<string, Record<string, number>>;
  names?: Record<string, string>;
}) {
  const used = grades.filter((g) => Object.values(rows).some((counts) => counts[g]));
  return (
    <table className={tableClass}>
      <thead><tr><th>{title}</th>{used.map((g) => <th key={g} className="text-right">{g}</th>)}<th className="text-right">Total</th></tr></thead>
      <tbody>
        {Object.entries(rows).map(([code, counts]) => (
          <tr key={code}>
            <td title={names[code]}>{code}</td>
            {used.map((g) => <td key={g} className="text-right">{counts[g] ?? <span className="text-slate-500" aria-label="none">·</span>}</td>)}
            <td className="text-right font-medium">{Object.values(counts).reduce((a, b) => a + b, 0)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
