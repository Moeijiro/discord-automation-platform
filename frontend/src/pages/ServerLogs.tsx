import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, ScrollText } from "lucide-react";
import { api } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { LogTable } from "@/components/LogTable";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorNote, Spinner } from "@/components/ui/Feedback";
import { Select } from "@/components/ui/Field";
import { EVENT_LABELS } from "@/lib/utils";

const PAGE_SIZE = 25;

export function ServerLogs() {
  const { guildId = "" } = useParams();
  const [eventType, setEventType] = useState("");
  const [offset, setOffset] = useState(0);

  const { data, error, loading } = useAsync(
    () => api.logs(guildId, { limit: PAGE_SIZE, offset, event_type: eventType || undefined }),
    [guildId, offset, eventType],
  );

  const total = data?.total ?? 0;
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <>
      <PageHeader
        eyebrow={
          <Link
            to={`/dashboard/server/${guildId}`}
            className="flex items-center gap-1.5 text-xs text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Back to server
          </Link>
        }
        title="Audit log"
        description="Every automation event recorded for this server, newest first."
        actions={
          <Select
            aria-label="Filter by event type"
            className="w-48"
            value={eventType}
            onChange={(event) => {
              setEventType(event.target.value);
              setOffset(0);
            }}
          >
            <option value="">All event types</option>
            {Object.entries(EVENT_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        }
      />

      {error ? <ErrorNote message={error} /> : null}

      <Card>
        <CardHeader
          title={`${total} event${total === 1 ? "" : "s"}`}
          description={eventType ? `Filtered by ${EVENT_LABELS[eventType] ?? eventType}.` : undefined}
          icon={<ScrollText className="h-4 w-4" />}
        />
        {loading ? <Spinner /> : <LogTable logs={data?.items ?? []} />}
      </Card>

      {pages > 1 ? (
        <div className="mt-4 flex items-center justify-between text-xs text-[var(--color-ink-muted)]">
          <span>
            Page {page} of {pages}
          </span>
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            >
              Previous
            </Button>
            <Button
              size="sm"
              disabled={offset + PAGE_SIZE >= total}
              onClick={() => setOffset(offset + PAGE_SIZE)}
            >
              Next
            </Button>
          </div>
        </div>
      ) : null}
    </>
  );
}
