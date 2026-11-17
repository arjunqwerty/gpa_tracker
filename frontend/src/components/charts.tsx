// Dashboard charts (Recharts). Colour carries the basis of a number, as the badges do elsewhere:
// emerald = confirmed, indigo (dashed) = predicted. Slate is context, warm grey is a reference value.
// Legend text stays slate; the coloured swatch beside it carries the identity.
import type { ReactNode } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { CgpaReport, CreditReport } from "../types";
import { fmt, gpa } from "./ui";

export const BASIS_COLOURS = { confirmed: "#047857", predicted: "#4f46e5" };
const CONTEXT = "#64748b";
const REFERENCE = "#a8a29e";
const GRID = "#e7e5e4";
const AXIS = { fontSize: 12, fill: "#475569" };
const legend = { wrapperStyle: { fontSize: 12 }, formatter: (name: string) => <span style={{ color: "#334155" }}>{name}</span> };

/** "Exams Jan 2022" -> "Jan 2022", "Semester 8" -> "Sem 8": axis labels stay short. */
const shortLabel = (label: string) => label.replace(/^Exams /, "").replace(/^Semester /, "Sem ");

/** A chart with a sentence that says what it shows, for screen readers and as a text alternative. */
function Figure({ summary, children }: { summary: string; children: ReactNode }) {
  return (
    <div role="img" aria-label={summary}>
      {children}
    </div>
  );
}

/**
 * Semester GPA and running CGPA, with the target as a reference line, all on one GPA axis.
 * Confirmed CGPA stops at the last semester with confirmed results; predicted CGPA is drawn only
 * from there on, so the two lines never sit on top of each other. No line is drawn through a
 * semester that has no GPA.
 */
export function GpaTrendChart({ report, target }: { report: CgpaReport; target: number | null }) {
  const semesters = report.semesters;
  const lastConfirmed = semesters.map((s) => s.confirmed_gpa != null).lastIndexOf(true);
  const data = semesters.map((s, i) => ({
    label: s.label,
    gpa: s.confirmed_gpa,
    cgpa: i <= lastConfirmed ? s.confirmed_cgpa : null,
    predicted: i >= lastConfirmed ? s.predicted_cgpa : null,
  }));
  const hasPrediction = data.some((d, i) => i > lastConfirmed && d.predicted != null);

  const values = data.flatMap((d) => [d.gpa, d.cgpa, d.predicted]).filter((v): v is number => v != null);
  const lowest = Math.max(0, Math.floor(Math.min(...values, target ?? 10) * 2) / 2 - 0.5);
  const ticks = Array.from({ length: Math.round((10 - lowest) * 2) + 1 }, (_, i) => lowest + i * 0.5);

  const first = semesters.find((s) => s.confirmed_cgpa != null);
  const last = semesters[lastConfirmed];
  const summary = first && last
    ? `Confirmed CGPA went from ${gpa(first.confirmed_cgpa)} after ${first.label} to ${gpa(last.confirmed_cgpa)} after ${last.label}` +
      (target != null ? `; target ${gpa(target)}.` : ".")
    : "No confirmed results yet.";

  return (
    <Figure summary={summary}>
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 10, right: 64, bottom: 0, left: -10 }} accessibilityLayer={false}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} tickFormatter={shortLabel}
            interval="preserveStartEnd" minTickGap={12} />
          <YAxis domain={[lowest, 10]} ticks={ticks} tick={AXIS} tickLine={false} axisLine={false} />
          <Tooltip formatter={(value) => (typeof value === "number" ? gpa(value) : "—")} />
          <Legend {...legend} />
          {target != null && (
            <ReferenceLine y={target} stroke={REFERENCE} strokeDasharray="4 4"
              label={{ value: `Target ${gpa(target)}`, position: "right", fontSize: 11, fill: "#475569" }} />
          )}
          <Line name="Semester GPA (confirmed)" dataKey="gpa" stroke={CONTEXT} strokeWidth={1.5} dot={{ r: 3 }} />
          <Line name="CGPA (confirmed)" dataKey="cgpa" stroke={BASIS_COLOURS.confirmed} strokeWidth={2.5} dot={{ r: 4 }} />
          {hasPrediction && (
            <Line name="CGPA (predicted)" dataKey="predicted" stroke={BASIS_COLOURS.predicted} strokeWidth={2.5}
              strokeDasharray="6 4" dot={{ r: 4, strokeDasharray: "0" }} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </Figure>
  );
}

/** Number of confirmed results per grade. Grades nobody has are left out. */
export function GradeDistributionChart({ grades, counts }: { grades: string[]; counts: Record<string, number> }) {
  const data = grades.filter((grade) => counts[grade]).map((grade) => ({ grade, courses: counts[grade] }));
  const summary = data.length ? `Confirmed grades: ${data.map((d) => `${d.courses} ${d.grade}`).join(", ")}.` : "No confirmed grades yet.";
  return (
    <Figure summary={summary}>
      <ResponsiveContainer width="100%" height={240}>
        <BarChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: -20 }} accessibilityLayer={false}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="grade" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} />
          <YAxis allowDecimals={false} tick={AXIS} tickLine={false} axisLine={false} />
          <Tooltip cursor={{ fill: "#f5f5f4" }} />
          <Bar name="Courses" dataKey="courses" fill={BASIS_COLOURS.confirmed} radius={[4, 4, 0, 0]} maxBarSize={36} />
        </BarChart>
      </ResponsiveContainer>
    </Figure>
  );
}

/** Registered versus earned (confirmed) credits per semester. */
export function CreditsBySemesterChart({ semesters }: { semesters: CreditReport["semesters"] }) {
  const summary = `Credits per semester: ${semesters
    .map((s) => `${s.label} ${fmt(s.earned_credits)} earned of ${fmt(s.registered_credits)} registered`)
    .join("; ")}.`;
  return (
    <Figure summary={summary}>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart data={semesters} margin={{ top: 10, right: 10, bottom: 0, left: -20 }} barGap={2} accessibilityLayer={false}>
          <CartesianGrid stroke={GRID} vertical={false} />
          <XAxis dataKey="label" tick={AXIS} tickLine={false} axisLine={{ stroke: GRID }} tickFormatter={shortLabel}
            interval="preserveStartEnd" minTickGap={8} />
          <YAxis tick={AXIS} tickLine={false} axisLine={false} />
          <Tooltip formatter={(value) => fmt(Number(value))} cursor={{ fill: "#f5f5f4" }} />
          <Legend {...legend} />
          <Bar name="Registered" dataKey="registered_credits" fill={REFERENCE} radius={[4, 4, 0, 0]} maxBarSize={22} />
          <Bar name="Earned" dataKey="earned_credits" fill={BASIS_COLOURS.confirmed} radius={[4, 4, 0, 0]} maxBarSize={22} />
        </BarChart>
      </ResponsiveContainer>
    </Figure>
  );
}
