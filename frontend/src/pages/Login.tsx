import { useSearchParams, Navigate } from "react-router-dom";
import { KeyRound, ShieldCheck, Sparkles, Terminal } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { Badge } from "@/components/ui/Badge";
import { ErrorNote, Spinner } from "@/components/ui/Feedback";
import { loginUrl } from "@/lib/api";

const ERRORS: Record<string, string> = {
  access_denied: "You cancelled the Discord authorisation.",
  invalid_state: "That login link expired or did not originate here. Please try again.",
  missing_code: "Discord did not return an authorisation code.",
  discord_error: "Discord rejected the login. Check the application credentials.",
};

const POINTS = [
  { icon: ShieldCheck, text: "Permissions are checked against Discord on every request" },
  { icon: KeyRound, text: "OAuth tokens stay encrypted on the server, never in the browser" },
  { icon: Terminal, text: "Every automation writes an auditable event" },
];

export function Login() {
  const { user, mode, loading } = useAuth();
  const [params] = useSearchParams();
  const error = params.get("error");

  if (loading) return <Spinner label="Checking session" />;
  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="relative z-10 flex min-h-full items-center justify-center px-4 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <span className="mx-auto mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-[var(--color-accent)]">
            <Sparkles className="h-5 w-5 text-white" />
          </span>
          <h1 className="text-lg font-semibold tracking-tight">Discord Automation Platform</h1>
          <p className="mt-1.5 text-sm text-[var(--color-ink-muted)]">
            Verification, roles and welcome messages for your server — configured from one
            dashboard.
          </p>
        </div>

        {error ? (
          <div className="mb-4">
            <ErrorNote message={ERRORS[error] ?? "Login failed. Please try again."} />
          </div>
        ) : null}

        <a
          href={loginUrl}
          className="flex h-11 w-full items-center justify-center gap-2 rounded-lg bg-[var(--color-accent)] text-sm font-medium text-white transition-colors hover:bg-[#5c6ff5]"
        >
          <DiscordMark />
          Continue with Discord
        </a>

        {mode?.demo ? (
          <p className="mt-3 flex items-center justify-center gap-2 text-center text-[11px] text-[var(--color-ink-muted)]">
            <Badge tone="warning">Demo mode</Badge>
            signs you in as a mock account
          </p>
        ) : null}

        <ul className="mt-8 space-y-2.5 border-t border-[var(--color-border)] pt-6">
          {POINTS.map(({ icon: Icon, text }) => (
            <li key={text} className="flex items-start gap-2.5 text-xs text-[var(--color-ink-muted)]">
              <Icon className="mt-px h-3.5 w-3.5 shrink-0 text-[var(--color-ink-subtle)]" />
              {text}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

function DiscordMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor" aria-hidden>
      <path d="M20.3 4.4A19.8 19.8 0 0 0 15.4 3l-.3.5a18.3 18.3 0 0 1 4.3 1.4 15.4 15.4 0 0 0-13-.5l.3-.9A19.8 19.8 0 0 0 3.7 4.4C1 8.4.3 12.3.7 16.1A19.9 19.9 0 0 0 6.7 19l.9-1.3a13 13 0 0 1-2-1l.5-.4a14.2 14.2 0 0 0 11.8 0l.5.4c-.6.4-1.3.7-2 1l.9 1.3a19.9 19.9 0 0 0 6-2.9c.5-4.4-.7-8.3-3-11.7ZM8.5 13.8c-1.2 0-2.1-1-2.1-2.3s.9-2.3 2.1-2.3 2.2 1 2.2 2.3-1 2.3-2.2 2.3Zm7 0c-1.2 0-2.1-1-2.1-2.3s.9-2.3 2.1-2.3 2.2 1 2.2 2.3-1 2.3-2.2 2.3Z" />
    </svg>
  );
}
