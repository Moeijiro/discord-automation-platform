import { useState } from "react";
import { Link } from "react-router-dom";
import { ChevronRight, RefreshCw, ServerCog } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { useAuth } from "@/context/auth-context";
import { PageHeader } from "@/components/PageHeader";
import { GuildIcon } from "@/components/GuildIcon";
import { Badge, StatusDot } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState, ErrorNote, Spinner } from "@/components/ui/Feedback";
import type { GuildSummary } from "@/lib/types";

export function Dashboard() {
  const { user } = useAuth();
  const { data, error, loading, reload } = useAsync(() => api.guilds(), []);
  const [syncing, setSyncing] = useState(false);

  const resync = async () => {
    setSyncing(true);
    try {
      await api.refreshGuilds();
      reload();
    } finally {
      setSyncing(false);
    }
  };

  return (
    <>
      <PageHeader
        title={`Welcome back, ${user?.display_name ?? ""}`}
        description="Servers Discord reports for your account. Manage Server permission is required to configure automation."
        actions={
          <Button onClick={resync} loading={syncing} size="sm">
            <RefreshCw className="h-3.5 w-3.5" />
            Re-sync
          </Button>
        }
      />

      {error ? <ErrorNote message={error} /> : null}
      {loading ? <Spinner label="Loading servers" /> : null}

      {data && data.length === 0 ? (
        <Card>
          <EmptyState
            icon={<ServerCog className="h-6 w-6" />}
            title="No servers found"
            hint="Discord reported no servers for this account. Re-sync after joining one."
          />
        </Card>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2">
        {data?.map((guild) => <GuildCard key={guild.id} guild={guild} />)}
      </div>
    </>
  );
}

function GuildCard({ guild }: { guild: GuildSummary }) {
  const body = (
    <Card className="h-full transition-colors hover:border-[var(--color-border-strong)]">
      <div className="flex items-start gap-3 px-4 py-4">
        <GuildIcon name={guild.name} url={guild.icon_url} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium">{guild.name}</p>
            {guild.is_owner ? <Badge tone="accent">Owner</Badge> : null}
          </div>
          <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[var(--color-ink-muted)]">
            <StatusDot tone={guild.bot_present ? "positive" : "warning"} />
            {guild.bot_present ? "Bot connected" : "Bot not in server"}
          </p>
          {!guild.manageable ? (
            <p className="mt-2 text-[11px] text-[var(--color-ink-subtle)]">
              Needs Manage Server to configure
            </p>
          ) : null}
        </div>
        {guild.manageable ? (
          <ChevronRight className="h-4 w-4 shrink-0 text-[var(--color-ink-subtle)]" />
        ) : null}
      </div>
    </Card>
  );

  return guild.manageable ? (
    <Link to={`/dashboard/server/${guild.id}`} className="block">
      {body}
    </Link>
  ) : (
    <div className="opacity-60">{body}</div>
  );
}
