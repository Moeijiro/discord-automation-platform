import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className }: CardProps) {
  return (
    <section
      className={cn(
        "rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]/80",
        "shadow-[0_1px_0_0_rgba(255,255,255,0.03)_inset] backdrop-blur-sm",
        className,
      )}
    >
      {children}
    </section>
  );
}

interface CardHeaderProps {
  title: string;
  description?: string;
  action?: ReactNode;
  icon?: ReactNode;
}

export function CardHeader({ title, description, action, icon }: CardHeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4 border-b border-[var(--color-border)] px-5 py-4">
      <div className="flex items-start gap-3">
        {icon ? <span className="mt-0.5 text-[var(--color-ink-subtle)]">{icon}</span> : null}
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-[var(--color-ink)]">{title}</h2>
          {description ? (
            <p className="mt-1 text-xs leading-relaxed text-[var(--color-ink-muted)]">{description}</p>
          ) : null}
        </div>
      </div>
      {action}
    </header>
  );
}

export function CardBody({ children, className }: CardProps) {
  return <div className={cn("px-5 py-4", className)}>{children}</div>;
}
