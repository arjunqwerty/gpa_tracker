// Small building blocks used by every page.
import { useEffect, type ButtonHTMLAttributes, type ReactNode } from "react";
import type { GradeBasis } from "../types";

/** 8.7234 -> "8.72", 9 -> "9", null -> "—" */
export function fmt(value: number | null | undefined, digits = 2): string {
  return value == null ? "—" : String(Number(value.toFixed(digits)));
}

/** GPA and CGPA always show two decimals: 8.8099 -> "8.81", 8 -> "8.00", null -> "—" */
export function gpa(value: number | null | undefined): string {
  return value == null ? "—" : value.toFixed(2);
}

// Dates come from the API as UTC timestamps; they are shown in UTC so a month never shifts by a day.
const MONTH = new Intl.DateTimeFormat(undefined, { month: "short", year: "numeric", timeZone: "UTC" });
const DAY = new Intl.DateTimeFormat(undefined, { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

/** "2024-05-01T00:00:00Z" -> "May 2024" (in the browser's language); null -> "—" */
export function monthLabel(value: string | null | undefined): string {
  return value ? MONTH.format(new Date(value)) : "—";
}

/** "2024-05-21T00:00:00Z" -> "21 May 2024" (in the browser's language); null -> "—" */
export function dayLabel(value: string | null | undefined): string {
  return value ? DAY.format(new Date(value)) : "—";
}

/** Names the browser tab after the page, so history, tabs and screen readers say where you are. */
export function usePageTitle(title: string) {
  useEffect(() => {
    document.title = `${title} · CGPA Tracker`;
  }, [title]);
}

export function PageHeader({ title, subtitle, actions }: { title: string; subtitle?: ReactNode; actions?: ReactNode }) {
  usePageTitle(title);
  return (
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div className="min-w-0">
        <h1 className="text-2xl font-semibold text-balance break-words text-slate-900">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  );
}

export function Card({ title, actions, level = 2, className = "", children }: {
  title?: string;
  actions?: ReactNode;
  level?: 2 | 3; // heading level: 3 when the card sits under a section heading
  className?: string;
  children: ReactNode;
}) {
  const Heading = level === 2 ? "h2" : "h3";
  return (
    <section className={`mb-6 min-w-0 rounded-lg border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      {(title || actions) && (
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          {title && <Heading className="font-semibold text-slate-800">{title}</Heading>}
          {actions && <div className="flex flex-wrap items-center justify-end gap-2">{actions}</div>}
        </div>
      )}
      {/* Wide tables scroll sideways inside the card instead of widening the page. */}
      <div className="overflow-x-auto">{children}</div>
    </section>
  );
}

/** A grey placeholder in the shape of the content that is still loading. */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`animate-pulse rounded-lg bg-slate-200/70 motion-reduce:animate-none ${className}`} />;
}

const BUTTON_STYLES = {
  primary: "bg-indigo-600 text-white hover:bg-indigo-700 active:bg-indigo-800",
  secondary: "border border-slate-300 bg-white text-slate-700 hover:border-slate-400 hover:bg-slate-50 active:bg-slate-100",
  danger: "border border-red-200 bg-white text-red-700 hover:border-red-300 hover:bg-red-50 active:bg-red-100",
};

/** Classes for anything that should look like a button, e.g. a download link. */
export function buttonClass(variant: keyof typeof BUTTON_STYLES = "primary", className = "") {
  return `inline-flex cursor-pointer items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors
    disabled:cursor-not-allowed disabled:opacity-50 ${BUTTON_STYLES[variant]} ${className}`;
}

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof BUTTON_STYLES }) {
  return <button type="button" className={buttonClass(variant, className)} {...props} />;
}

/** A quiet bin icon for removing one row of a table; turns red on hover. `label` names what goes. */
export function RemoveButton({ label, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { label: string }) {
  return (
    <button type="button" aria-label={label} title={label}
      className="cursor-pointer rounded-md p-1.5 text-slate-500 transition-colors hover:bg-red-50 hover:text-red-700 disabled:cursor-not-allowed disabled:opacity-50"
      {...props}>
      <svg aria-hidden="true" viewBox="0 0 16 16" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M2.5 4h11M6.5 4V2.5h3V4M4 4l.6 9a1 1 0 0 0 1 .9h4.8a1 1 0 0 0 1-.9L12 4M6.75 6.75v4.5M9.25 6.75v4.5" />
      </svg>
    </button>
  );
}

/** Earned against required, as a thin emerald bar (emerald = confirmed, as everywhere else). */
export function ProgressBar({ value, max, className = "mt-2" }: { value: number; max: number; className?: string }) {
  const percent = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className={`h-1.5 overflow-hidden rounded-full bg-slate-100 ${className}`} role="presentation">
      <div className="h-full rounded-full bg-emerald-700" style={{ width: `${percent}%` }} />
    </div>
  );
}

/** "Unsaved changes" marker for a card or row whose edits have not been saved yet. */
export function UnsavedNote() {
  return <span className="text-xs font-medium text-amber-800">Unsaved changes</span>;
}

export function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {hint && <div className="mt-1 text-xs text-slate-500">{hint}</div>}
    </div>
  );
}

export function Field({ label, children, className = "" }: { label: string; children: ReactNode; className?: string }) {
  return (
    <label className={`flex flex-col gap-1 text-sm text-slate-600 ${className}`}>
      {label}
      {children}
    </label>
  );
}

export function ErrorMessage({ message }: { message?: string }) {
  if (!message) return null;
  return <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">{message}</div>;
}

/** Shown while a page's data loads; its error, with a way to try again, if loading failed. */
export function Loading({ error }: { error?: string }) {
  if (!error) return <p className="text-sm text-slate-600" role="status">Loading…</p>;
  return (
    <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800" role="alert">
      <p>{error}</p>
      <button type="button" className="mt-2 cursor-pointer font-medium underline underline-offset-2" onClick={() => window.location.reload()}>
        Try again
      </button>
    </div>
  );
}

const BADGE_TONES = {
  green: "bg-emerald-100 text-emerald-800",
  amber: "bg-amber-100 text-amber-800",
  indigo: "bg-indigo-100 text-indigo-800",
  red: "bg-red-100 text-red-800",
  slate: "bg-slate-100 text-slate-600",
};

export function Badge({ tone = "slate", children }: { tone?: keyof typeof BADGE_TONES; children: ReactNode }) {
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${BADGE_TONES[tone]}`}>{children}</span>;
}

const BASIS_TONE = { confirmed: "green", provisional: "amber", predicted: "indigo" } as const;

/** A grade with a badge saying whether it is confirmed, provisional or only predicted. */
export function GradeWithBasis({ grade, basis }: { grade: string | null; basis: GradeBasis }) {
  if (!grade || !basis) return <span className="text-slate-400">—</span>;
  return (
    <span className="inline-flex items-center gap-2">
      <span className="font-semibold">{grade}</span>
      <Badge tone={BASIS_TONE[basis]}>{basis}</Badge>
    </span>
  );
}

export const tableClass = "w-full text-left text-sm [&_td]:px-2 [&_td]:py-1.5 [&_th]:px-2 [&_th]:py-2 [&_th]:font-medium [&_th]:text-slate-500 [&_tbody_tr]:border-t [&_tbody_tr]:border-slate-100";
