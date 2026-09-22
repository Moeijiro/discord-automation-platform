import type { ReactNode } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";

export function Spinner({ label = "Loading" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-12 text-sm text-[var(--color-ink-muted)]">
      <Loader2 className="h-4 w-4 animate-spin" />
      {label}
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-[#4a2630] bg-[#1a0f13] px-3 py-2 text-xs text-[var(--color-danger)]">
      <AlertTriangle className="mt-px h-3.5 w-3.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ title, hint, icon }: { title: string; hint?: string; icon?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-14 text-center">
      {icon ? <span className="text-[var(--color-ink-subtle)]">{icon}</span> : null}
      <p className="text-sm font-medium text-[var(--color-ink)]">{title}</p>
      {hint ? <p className="max-w-sm text-xs text-[var(--color-ink-muted)]">{hint}</p> : null}
    </div>
  );
}
