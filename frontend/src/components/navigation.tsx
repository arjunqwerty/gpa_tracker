// How people move between pages: breadcrumbs, back buttons, rows that open their page, and
// links styled as buttons.
//
// Two ideas of "up" are kept apart on purpose:
// - the breadcrumb shows where a page lives (Semesters › Semester › Course), always;
// - the back button returns to where you came from: a list passes its own location and name
//   along (see NavRow / useFromHere), and pages fall back to their structural parent.
import { createContext, useContext, useRef, type MouseEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ChevronLeftIcon, ChevronRightIcon } from "./icons";
import { buttonClass } from "./ui";

export interface Crumb {
  label: string;
  to?: string; // omitted for the current page
}

interface Origin {
  to: string;
  label: string;
}

/** Router state that tells the next page where the user came from, e.g. { from: Grade history }. */
export function useFromHere(label: string): { from: Origin } {
  const location = useLocation();
  return { from: { to: location.pathname + location.search, label } };
}

/** The page the user came from, if a list sent them here; the back button prefers it over the parent. */
export function useCameFrom(): Origin | undefined {
  return (useLocation().state as { from?: Origin } | null)?.from;
}

/**
 * Back button plus breadcrumb trail; the last crumb is the current page. On phones only the
 * back button shows, since the trail would push the page title below the fold.
 */
export function PageNav({ back, crumbs }: { back?: Origin; crumbs: Crumb[] }) {
  return (
    <div className="mb-4 flex min-w-0 flex-wrap items-center gap-x-4 gap-y-2">
      {back && (
        <Link to={back.to} className={buttonClass("secondary", "max-w-full pl-2")}>
          <ChevronLeftIcon />
          <span className="truncate">Back to {back.label}</span>
        </Link>
      )}
      <nav aria-label="Breadcrumb" className={`min-w-0 ${back ? "hidden sm:block" : ""}`}>
        <ol className="flex min-w-0 flex-wrap items-center gap-x-1.5 gap-y-1 text-sm">
          {crumbs.map((crumb, i) => (
            <li key={i} className="flex min-w-0 items-center gap-1.5">
              {i > 0 && <ChevronRightIcon className="h-3.5 w-3.5 text-slate-400" />}
              {crumb.to ? (
                <Link to={crumb.to}
                  className="block max-w-[12rem] truncate rounded-sm py-1 text-slate-600 underline-offset-4 hover:text-indigo-700 hover:underline active:text-indigo-900 sm:max-w-[16rem]">
                  {crumb.label}
                </Link>
              ) : (
                <span aria-current="page" className="block max-w-[14rem] truncate py-1 font-medium text-slate-900 sm:max-w-[24rem]">
                  {crumb.label}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </div>
  );
}

/** A link that is a standalone action, so it looks like a button (e.g. "See your dashboard"). */
export function ButtonLink({ to, variant = "secondary", children }: {
  to: string;
  variant?: Parameters<typeof buttonClass>[0];
  children: ReactNode;
}) {
  return <Link to={to} className={buttonClass(variant)}>{children}</Link>;
}

// --- Rows that open their page --------------------------------------------------------------

const RowContext = createContext<{ to: string; state: { from: Origin } } | null>(null);
const isControl = (target: EventTarget) => target instanceof Element && target.closest("button, input, select, textarea, label") != null;

/**
 * A table row that opens its page. With a mouse, a click selects the row and a double-click
 * opens it; on touch screens a tap opens it (double-tap zooms there). Its main cell holds a
 * RowLink, so keyboard users Tab to it and press Enter, screen readers hear a link, and
 * Ctrl/middle-click opens a new tab. Buttons inside the row keep working and never navigate.
 * `from` names the current page, so the opened page can offer "Back to <from>".
 */
export function NavRow({ to, from, children }: { to: string; from: string; children: ReactNode }) {
  const navigate = useNavigate();
  const state = useFromHere(from);
  const row = useRef<HTMLTableRowElement>(null);

  const open = (event: MouseEvent) => {
    if (isControl(event.target)) return;
    window.getSelection()?.removeAllRanges(); // a double-click also selects a word; undo that
    navigate(to, { state });
  };
  const click = (event: MouseEvent) => {
    if (isControl(event.target)) return;
    const onLink = event.target instanceof Element && event.target.closest(".row-link") != null;
    if ((event.nativeEvent as PointerEvent).pointerType === "touch") return onLink ? undefined : open(event); // the link opens itself
    row.current?.querySelector<HTMLAnchorElement>(".row-link")?.focus(); // select the row
  };

  return (
    <RowContext.Provider value={{ to, state }}>
      <tr ref={row} onDoubleClick={open} onClick={click}
        className="group cursor-pointer transition-colors hover:bg-slate-50 has-[.row-link:focus]:bg-indigo-50 has-[.row-link:focus-visible]:outline-2 has-[.row-link:focus-visible]:-outline-offset-2 has-[.row-link:focus-visible]:outline-solid has-[.row-link:focus-visible]:outline-indigo-600">
        {children}
      </tr>
    </RowContext.Provider>
  );
}

/** The row's name (semester label, course code), as a link that looks like plain text. */
export function RowLink({ children }: { children: ReactNode }) {
  const row = useContext(RowContext)!;
  // A plain left click only selects the row; double-click (handled by the row), Enter,
  // a tap, or Ctrl/Shift/middle-click open it.
  const click = (event: MouseEvent) => {
    const plainMouseClick = event.detail > 0 && event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey
      && (event.nativeEvent as PointerEvent).pointerType !== "touch";
    if (plainMouseClick) event.preventDefault();
  };
  return (
    <Link to={row.to} state={row.state} onClick={click}
      className="row-link font-medium text-slate-900 underline-offset-4 outline-none group-hover:underline">
      {children}
    </Link>
  );
}

/** The caption under a table of NavRows that says how to open a row, worded for the device. */
export function OpenRowHint() {
  return (
    <caption className="caption-bottom pt-3 text-left text-xs text-slate-600">
      <span className="pointer-coarse:hidden">Double-click a row to open it, or Tab to it and press Enter.</span>
      <span className="hidden pointer-coarse:inline">Tap a row to open it.</span>
    </caption>
  );
}
