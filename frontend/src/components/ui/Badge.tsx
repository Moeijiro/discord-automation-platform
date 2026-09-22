import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

export type Tone = "neutral" | "accent" | "positive" | "warning" | "danger";

const TONES: Record<Tone, string> = {
  neutral: "border-[var(--color-border-strong)] bg-[var(--color-surface-raised)] text-[var(--color-ink-muted)]",
  accent: "border-[#3a428a] bg-[#191c35] text-[#a6b0ff]",
  positive: "border-[#1f5240] bg-[#0f2620] text-[var(--color-positive)]",
  warning: "border-[#5a4520] bg-[#241c0f] text-[var(--color-warning)]",
  danger: "border-[#4a2630] bg-[#241419] text-[var(--color-danger)]",
};

interface BadgeProps {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}

export function Badge({ children, tone = "neutral", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-md border px-2 py-0.5 text-[11px] font-medium",
        TONES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

/** A small coloured dot; pairs with text to show connection state. */
export function StatusDot({ tone = "neutral" }: { tone?: Tone }) {
  const color: Record<Tone, string> = {
    neutral: "bg-[var(--color-ink-subtle)]",
    accent: "bg-[var(--color-accent)]",
    positive: "bg-[var(--color-positive)]",
    warning: "bg-[var(--color-warning)]",
    danger: "bg-[var(--color-danger)]",
  };
  return (
    <span className={cn("inline-block h-1.5 w-1.5 shrink-0 rounded-full", color[tone])} />
  );
}
