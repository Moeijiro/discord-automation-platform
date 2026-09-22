import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { Activity, LayoutGrid, LogOut, Settings as SettingsIcon, Zap } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Servers", icon: LayoutGrid, end: true },
  { to: "/settings", label: "Settings", icon: SettingsIcon, end: false },
];

/** Sidebar + top bar. Every authenticated page renders inside this. */
export function AppShell() {
  const { user, mode, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="relative z-10 flex min-h-full flex-col md:flex-row">
      <aside className="flex shrink-0 flex-col gap-6 border-b border-[var(--color-border)] bg-[var(--color-surface)]/60 px-4 py-4 md:w-60 md:border-b-0 md:border-r md:py-6">
        <div className="flex items-center gap-2.5">
          <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--color-accent)]">
            <Zap className="h-4 w-4 text-white" />
          </span>
          <div className="leading-tight">
            <p className="text-sm font-semibold tracking-tight">Automation</p>
            <p className="text-[11px] text-[var(--color-ink-subtle)]">Discord platform</p>
          </div>
        </div>

        <nav className="flex gap-1 md:flex-1 md:flex-col">
          {NAV.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-[var(--color-surface-raised)] text-[var(--color-ink)]"
                    : "text-[var(--color-ink-muted)] hover:bg-[var(--color-surface-raised)]/60 hover:text-[var(--color-ink)]",
                )
              }
            >
              <Icon className="h-4 w-4" />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-2.5 rounded-lg border border-[var(--color-border)] px-3 py-2 md:flex">
          <img
            src={user?.avatar_url}
            alt=""
            className="h-7 w-7 rounded-full border border-[var(--color-border-strong)]"
          />
          <div className="min-w-0 flex-1 leading-tight">
            <p className="truncate text-xs font-medium">{user?.display_name}</p>
            <p className="truncate text-[11px] text-[var(--color-ink-subtle)]">
              @{user?.username}
            </p>
          </div>
          <button
            onClick={async () => {
              await logout();
              navigate("/login");
            }}
            aria-label="Sign out"
            className="rounded-md p-1.5 text-[var(--color-ink-subtle)] transition-colors hover:bg-[var(--color-surface-raised)] hover:text-[var(--color-ink)]"
          >
            <LogOut className="h-3.5 w-3.5" />
          </button>
        </div>
      </aside>

      <main className="min-w-0 flex-1">
        {mode?.demo ? <DemoBanner /> : null}
        <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 md:py-10">
          <Outlet />
        </div>
      </main>
    </div>
  );
}

/** Demo mode is never implied -- it is stated on every page. */
function DemoBanner() {
  return (
    <div className="flex flex-wrap items-center gap-2 border-b border-[#5a4520]/50 bg-[#1a1409] px-4 py-2 text-xs text-[var(--color-warning)] sm:px-6">
      <Activity className="h-3.5 w-3.5" />
      <span className="font-medium">Demo mode</span>
      <span className="text-[var(--color-ink-muted)]">
        Servers, roles and channels are mock data. Nothing reaches Discord — actions you
        take are still recorded in the real audit trail.
      </span>
      <Badge tone="warning" className="ml-auto">
        no credentials configured
      </Badge>
    </div>
  );
}
