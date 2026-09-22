import { Bot, Globe, ShieldCheck, User as UserIcon } from "lucide-react";
import { Badge, type Tone } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/Feedback";
import { absoluteTime, eventLabel, relativeTime } from "@/lib/utils";
import type { AutomationLog } from "@/lib/types";

const TONES: Record<string, Tone> = {
  verification_completed: "positive",
  role_added: "accent",
  role_removed: "neutral",
  member_joined: "accent",
  welcome_sent: "positive",
  settings_updated: "neutral",
  webhook_received: "warning",
  automation_failed: "danger",
};

const ACTORS: Record<string, typeof Bot> = {
  user: UserIcon,
  bot: Bot,
  webhook: Globe,
  system: ShieldCheck,
};

interface LogTableProps {
  logs: AutomationLog[];
  compact?: boolean;
}

/** The audit trail, rendered the same way on the overview and the logs page. */
export function LogTable({ logs, compact = false }: LogTableProps) {
  if (logs.length === 0) {
    return (
      <EmptyState
        title="No events yet"
        hint="Automation events appear here as soon as something happens in this server."
      />
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[34rem] border-collapse text-sm">
        <thead>
          <tr className="text-left text-[11px] uppercase tracking-wide text-[var(--color-ink-subtle)]">
            <th className="px-5 py-2.5 font-medium">Event</th>
            <th className="px-5 py-2.5 font-medium">Details</th>
            {compact ? null : <th className="px-5 py-2.5 font-medium">Actor</th>}
            <th className="px-5 py-2.5 text-right font-medium">When</th>
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => {
            const ActorIcon = ACTORS[log.actor_type] ?? ShieldCheck;
            return (
              <tr
                key={log.id}
                className="border-t border-[var(--color-border)] align-top transition-colors hover:bg-[var(--color-surface-raised)]/40"
              >
                <td className="px-5 py-3">
                  <Badge tone={TONES[log.event_type] ?? "neutral"}>
                    {eventLabel(log.event_type)}
                  </Badge>
                </td>
                <td className="px-5 py-3 text-[var(--color-ink)]">
                  <p className="leading-snug">{log.message}</p>
                  {log.target_discord_id ? (
                    <p className="mt-0.5 font-mono text-[11px] text-[var(--color-ink-subtle)]">
                      {log.target_discord_id}
                    </p>
                  ) : null}
                </td>
                {compact ? null : (
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1.5 text-xs text-[var(--color-ink-muted)]">
                      <ActorIcon className="h-3.5 w-3.5" />
                      {log.actor_type}
                    </span>
                  </td>
                )}
                <td
                  className="whitespace-nowrap px-5 py-3 text-right text-xs text-[var(--color-ink-muted)]"
                  title={absoluteTime(log.created_at)}
                >
                  {relativeTime(log.created_at)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
