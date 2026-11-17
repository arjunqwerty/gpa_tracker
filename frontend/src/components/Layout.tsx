// The frame around every logged-in page: a collapsible sidebar on wider screens, a top bar with a
// menu on phones. The sidebar's collapsed state is remembered in this browser.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import {
  CloseIcon, CollapseSidebarIcon, CreditsIcon, DashboardIcon, ExpandSidebarIcon, HistoryIcon, ImportExportIcon, LogOutIcon, MenuIcon,
  SemestersIcon, SettingsIcon,
} from "./icons";

const NAVIGATION = [
  { to: "/", label: "Dashboard", icon: DashboardIcon },
  { to: "/semesters", label: "Semesters", icon: SemestersIcon, alsoActiveFor: "/courses" }, // a course lives under its semester
  { to: "/history", label: "Grade history", icon: HistoryIcon },
  { to: "/credits", label: "Credits", icon: CreditsIcon },
  { to: "/import-export", label: "Import & export", icon: ImportExportIcon },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const STORAGE_KEY = "sidebar-collapsed";

/** Remembered choice, or collapsed by default on tablet widths where space is tight. */
function initiallyCollapsed(): boolean {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored != null) return stored === "true";
  } catch {
    // storage blocked (private window): fall through to the default
  }
  return window.innerWidth < 1024;
}

/** Label beside the icon when expanded; a tooltip on hover or keyboard focus when collapsed. */
function ItemLabel({ collapsed, children }: { collapsed: boolean; children: ReactNode }) {
  return collapsed ? (
    <span
      className="pointer-events-none absolute left-full z-30 ml-3 whitespace-nowrap rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white opacity-0 shadow-md transition-opacity duration-150 group-hover:opacity-100 group-focus-visible:opacity-100">
      {children}
    </span>
  ) : (
    <span className="truncate">{children}</span>
  );
}

function Navigation({ collapsed = false, onNavigate }: { collapsed?: boolean; onNavigate?: () => void }) {
  const { pathname } = useLocation();
  return (
    <ul className="space-y-1">
      {NAVIGATION.map(({ to, label, icon: Icon, alsoActiveFor }) => (
        <li key={to}>
          <NavLink
            to={to}
            end={to === "/"}
            onClick={onNavigate}
            className={({ isActive }) =>
              `group relative flex items-center gap-3 rounded-md px-3 py-2.5 text-sm transition-colors md:py-2 ${
                isActive || (alsoActiveFor && pathname.startsWith(alsoActiveFor))
                  ? "bg-indigo-50 font-medium text-indigo-700"
                  : "text-slate-600 hover:bg-slate-100 hover:text-slate-900"
              }`
            }
          >
            <Icon />
            <ItemLabel collapsed={collapsed}>{label}</ItemLabel>
          </NavLink>
        </li>
      ))}
    </ul>
  );
}

function AccountBox({ collapsed = false }: { collapsed?: boolean }) {
  const { account, setAccount } = useAuth();
  const logout = () => api.post("/api/auth/logout").finally(() => setAccount(null));
  const initial = account?.full_name.trim().charAt(0).toUpperCase() || "?";
  const logoutLabel = collapsed ? `Log out ${account?.full_name ?? ""}`.trim() : "Log out";

  return (
    <div className={`border-t border-slate-200 pt-4 text-sm ${collapsed ? "flex flex-col items-center gap-2" : "px-3"}`}>
      {collapsed ? (
        <span aria-hidden="true" title={`${account?.full_name} · ${account?.email}`}
          className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-100 font-semibold text-indigo-800">{initial}</span>
      ) : (
        <>
          <div className="truncate font-medium text-slate-700">{account?.full_name}</div>
          <div className="truncate text-xs text-slate-600">{account?.email}</div>
        </>
      )}
      <button type="button" onClick={logout}
        className={`group relative flex cursor-pointer items-center gap-2 rounded-md text-indigo-700 hover:text-indigo-900 ${collapsed ? "p-2 hover:bg-slate-100" : "mt-2 hover:underline"}`}>
        <LogOutIcon />
        <ItemLabel collapsed={collapsed}>{logoutLabel}</ItemLabel>
      </button>
    </div>
  );
}

export default function Layout() {
  const [collapsed, setCollapsed] = useState(initiallyCollapsed);
  const [menuOpen, setMenuOpen] = useState(false);
  const main = useRef<HTMLElement>(null);
  const { pathname } = useLocation();

  // After moving to another page, put focus at the start of the content so keyboard and
  // screen-reader users continue from there (not from the link they used).
  const lastPath = useRef(pathname);
  useEffect(() => {
    if (lastPath.current === pathname) return; // first load, or a re-run of the same page
    lastPath.current = pathname;
    main.current?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [pathname]);

  const toggle = () => {
    setCollapsed(!collapsed);
    try {
      localStorage.setItem(STORAGE_KEY, String(!collapsed));
    } catch {
      // not remembered, but the toggle still works for this visit
    }
  };

  // Escape closes the phone menu.
  useEffect(() => {
    if (!menuOpen) return;
    const close = (event: KeyboardEvent) => event.key === "Escape" && setMenuOpen(false);
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 md:flex">
      <a href="#content"
        className="sr-only z-50 rounded-md bg-white px-3 py-2 text-sm font-medium text-indigo-700 shadow-md focus:not-sr-only focus:fixed focus:left-3 focus:top-3">
        Skip to content
      </a>
      {/* Tablets and wider: the sidebar, collapsible to icons */}
      <aside id="sidebar"
        className={`sticky top-0 hidden h-screen shrink-0 flex-col border-r border-slate-200 bg-white py-5 transition-[width] duration-200 ease-out motion-reduce:transition-none md:flex ${
          collapsed ? "w-16 px-2" : "w-56 px-3"
        }`}>
        <div className={`mb-6 flex items-center ${collapsed ? "flex-col gap-3" : "justify-between pl-3"}`}>
          {collapsed
            ? <span aria-hidden="true" title="CGPA Tracker" className="flex h-8 w-8 items-center justify-center rounded-md bg-indigo-700 text-sm font-bold text-white">C</span>
            : <span className="truncate text-lg font-bold text-indigo-700">CGPA Tracker</span>}
          <button type="button" onClick={toggle} aria-expanded={!collapsed} aria-controls="sidebar"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="cursor-pointer rounded-md p-2 text-slate-500 transition-colors hover:bg-slate-100 hover:text-slate-900">
            {collapsed ? <ExpandSidebarIcon /> : <CollapseSidebarIcon />}
          </button>
        </div>
        <nav aria-label="Main">
          <Navigation collapsed={collapsed} />
        </nav>
        <div className="mt-auto"><AccountBox collapsed={collapsed} /></div>
      </aside>

      {/* Phones: a top bar with a menu */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white md:hidden">
        <div className="flex items-center justify-between px-4 py-3">
          <span className="text-lg font-bold text-indigo-700">CGPA Tracker</span>
          <button type="button" aria-expanded={menuOpen} aria-controls="mobile-menu" onClick={() => setMenuOpen(!menuOpen)}
            className="flex min-h-11 cursor-pointer items-center gap-2 rounded-md border border-slate-300 px-3 text-sm text-slate-700 hover:bg-slate-50">
            {menuOpen ? <CloseIcon /> : <MenuIcon />}
            Menu
          </button>
        </div>
        {menuOpen && (
          <nav id="mobile-menu" aria-label="Main" className="px-3 pb-4">
            <Navigation onNavigate={() => setMenuOpen(false)} />
            <div className="pt-3"><AccountBox /></div>
          </nav>
        )}
      </header>

      {/* Collapsing the sidebar gives the content the space back. */}
      <main id="content" ref={main} tabIndex={-1}
        className={`mx-auto w-full min-w-0 px-4 py-6 outline-none md:px-8 md:py-8 ${collapsed ? "max-w-7xl" : "max-w-6xl"}`}>
        <Outlet />
      </main>
    </div>
  );
}
