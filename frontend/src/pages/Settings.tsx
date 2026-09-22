import { useNavigate } from "react-router-dom";
import { KeyRound, LogOut, Radio, Webhook } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { PageHeader } from "@/components/PageHeader";
import { Badge, StatusDot } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";

const WEBHOOK_SNIPPET = `BODY='{"event":"deployment","guild_id":"<guild id>","message":"v1.4.0 shipped"}'
SIG="sha256=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -r | cut -d' ' -f1)"

curl -X POST http://localhost:8000/api/webhooks/custom \\
  -H "Content-Type: application/json" \\
  -H "X-Signature: $SIG" \\
  -d "$BODY"`;

export function Settings() {
  const { user, mode, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <>
      <PageHeader
        title="Settings"
        description="Your connected account and how this instance is configured."
      />

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader title="Connected account" icon={<KeyRound className="h-4 w-4" />} />
          <CardBody className="space-y-4">
            <div className="flex items-center gap-3">
              <img
                src={user?.avatar_url}
                alt=""
                className="h-10 w-10 rounded-full border border-[var(--color-border-strong)]"
              />
              <div className="min-w-0">
                <p className="truncate text-sm font-medium">{user?.display_name}</p>
                <p className="truncate font-mono text-[11px] text-[var(--color-ink-subtle)]">
                  {user?.discord_id}
                </p>
              </div>
            </div>
            <p className="text-xs leading-relaxed text-[var(--color-ink-muted)]">
              Your Discord access token is encrypted and stored server side. The browser holds
              only an HttpOnly session cookie, which this button clears.
            </p>
            <Button
              variant="danger"
              size="sm"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              <LogOut className="h-3.5 w-3.5" />
              Sign out
            </Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader title="Instance" icon={<Radio className="h-4 w-4" />} />
          <CardBody className="space-y-3 text-xs">
            <Row label="Data source">
              <span className="flex items-center gap-1.5">
                <StatusDot tone={mode?.demo ? "warning" : "positive"} />
                {mode?.demo ? "Demo (mock Discord data)" : "Live Discord API"}
              </span>
            </Row>
            <Row label="Discord credentials">
              <Badge tone={mode?.discord_configured ? "positive" : "neutral"}>
                {mode?.discord_configured ? "configured" : "not configured"}
              </Badge>
            </Row>
            <Row label="Session">
              <span>HttpOnly cookie, signed (JWT)</span>
            </Row>
            <p className="pt-1 leading-relaxed text-[var(--color-ink-muted)]">
              Demo mode is refused when the backend runs with ENVIRONMENT=production, so mock
              data can never be served as real activity.
            </p>
          </CardBody>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title="Webhook integration"
            description="Signed events from CI, monitoring or a game server land in the audit trail."
            icon={<Webhook className="h-4 w-4" />}
          />
          <CardBody>
            <pre className="overflow-x-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3 font-mono text-[11px] leading-relaxed text-[var(--color-ink-muted)]">
              {WEBHOOK_SNIPPET}
            </pre>
          </CardBody>
        </Card>
      </div>
    </>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-[var(--color-border)] pb-2.5 last:border-0">
      <span className="text-[var(--color-ink-subtle)]">{label}</span>
      <span className="text-right text-[var(--color-ink)]">{children}</span>
    </div>
  );
}
