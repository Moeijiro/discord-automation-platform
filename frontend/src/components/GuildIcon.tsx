import { cn } from "@/lib/utils";

interface GuildIconProps {
  name: string;
  url: string | null;
  size?: "sm" | "md";
}

/** Discord's own fallback: the server's initials on a flat tile. */
export function GuildIcon({ name, url, size = "md" }: GuildIconProps) {
  const dimensions = size === "sm" ? "h-8 w-8 text-[11px]" : "h-10 w-10 text-xs";
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join("")
    .toUpperCase();

  if (url) {
    return <img src={url} alt="" className={cn(dimensions, "rounded-lg object-cover")} />;
  }
  return (
    <span
      aria-hidden
      className={cn(
        dimensions,
        "flex items-center justify-center rounded-lg border border-[var(--color-border-strong)]",
        "bg-[var(--color-surface-raised)] font-semibold text-[var(--color-ink-muted)]",
      )}
    >
      {initials}
    </span>
  );
}
