// The app's icon set: 16px grid, 1.5px rounded strokes, drawn to match each other.
// Icons are decorative (aria-hidden); the control around them carries the accessible name.
import type { ReactNode } from "react";

function Icon({ children, className = "h-4 w-4" }: { children: ReactNode; className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 16 16" className={`shrink-0 ${className}`} fill="none" stroke="currentColor"
      strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

type IconProps = { className?: string };

export const DashboardIcon = (p: IconProps) => (
  <Icon {...p}><rect x="2" y="2" width="5" height="6" rx="1" /><rect x="9" y="2" width="5" height="3.5" rx="1" />
    <rect x="9" y="7.5" width="5" height="6.5" rx="1" /><rect x="2" y="10" width="5" height="4" rx="1" /></Icon>
);

export const SemestersIcon = (p: IconProps) => (
  <Icon {...p}><path d="M8 2 14 5 8 8 2 5Z" /><path d="M2 8l6 3 6-3" /><path d="M2 11l6 3 6-3" /></Icon>
);

export const HistoryIcon = (p: IconProps) => (
  <Icon {...p}><path d="M2.5 8a5.5 5.5 0 1 0 1.6-3.9" /><path d="M2.5 2.5v2.2h2.2" /><path d="M8 5v3.2l2 1.3" /></Icon>
);

export const CreditsIcon = (p: IconProps) => (
  <Icon {...p}><path d="M2.5 13.5h11" /><path d="M4 13.5V9" /><path d="M8 13.5V5.5" /><path d="M12 13.5V2.5" /></Icon>
);

export const ImportExportIcon = (p: IconProps) => (
  <Icon {...p}><path d="M5 13V3M2.5 5.5 5 3l2.5 2.5" /><path d="M11 3v10M8.5 10.5 11 13l2.5-2.5" /></Icon>
);

export const SettingsIcon = (p: IconProps) => (
  <Icon {...p}><circle cx="8" cy="8" r="2" />
    <path d="M8 1.75v1.5M8 12.75v1.5M1.75 8h1.5M12.75 8h1.5M3.6 3.6l1.05 1.05M11.35 11.35l1.05 1.05M3.6 12.4l1.05-1.05M11.35 4.65l1.05-1.05" />
    <circle cx="8" cy="8" r="4.25" /></Icon>
);

export const ChevronLeftIcon = (p: IconProps) => <Icon {...p}><path d="M10 3.5 5.5 8 10 12.5" /></Icon>;
export const ChevronRightIcon = (p: IconProps) => <Icon {...p}><path d="M6 3.5 10.5 8 6 12.5" /></Icon>;

export const CollapseSidebarIcon = (p: IconProps) => (
  <Icon {...p}><rect x="2" y="2.5" width="12" height="11" rx="1.5" /><path d="M6 2.5v11" /><path d="M10.5 6.25 8.75 8l1.75 1.75" /></Icon>
);

export const ExpandSidebarIcon = (p: IconProps) => (
  <Icon {...p}><rect x="2" y="2.5" width="12" height="11" rx="1.5" /><path d="M6 2.5v11" /><path d="M9 6.25 10.75 8 9 9.75" /></Icon>
);

export const LogOutIcon = (p: IconProps) => (
  <Icon {...p}><path d="M6 13.5H3.5a1 1 0 0 1-1-1v-9a1 1 0 0 1 1-1H6" /><path d="M10.5 11 13.5 8l-3-3M13.5 8H6" /></Icon>
);

export const MenuIcon = (p: IconProps) => <Icon {...p}><path d="M2.5 4.5h11M2.5 8h11M2.5 11.5h11" /></Icon>;
export const CloseIcon = (p: IconProps) => <Icon {...p}><path d="M3.5 3.5l9 9M12.5 3.5l-9 9" /></Icon>;
