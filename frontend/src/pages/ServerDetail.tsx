import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowRight, BadgeCheck, MessageSquare, Save, UserPlus, Wand2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAsync } from "@/hooks/useAsync";
import { PageHeader } from "@/components/PageHeader";
import { GuildIcon } from "@/components/GuildIcon";
import { LogTable } from "@/components/LogTable";
import { StatTile } from "@/components/StatTile";
import { Badge, StatusDot } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ErrorNote, Spinner } from "@/components/ui/Feedback";
import { Field, Select, Textarea, Toggle } from "@/components/ui/Field";
import type { GuildDetail, GuildSettings } from "@/lib/types";

export function ServerDetail() {
  const { guildId = "" } = useParams();
  const guild = useAsync(() => api.guild(guildId), [guildId]);
  const logs = useAsync(() => api.logs(guildId, { limit: 6 }), [guildId]);

  if (guild.loading) return <Spinner label="Loading server" />;
  if (guild.error) return <ErrorNote message={guild.error} />;
  if (!guild.data) return null;

  const detail = guild.data;
  const stats = detail.stats;

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            <GuildIcon name={detail.name} url={detail.icon_url} size="sm" />
            <span className="flex items-center gap-1.5 text-xs text-[var(--color-ink-muted)]">
              <StatusDot tone={detail.bot_present ? "positive" : "warning"} />
              {detail.bot_present ? "Bot connected" : "Bot not in server"}
            </span>
            {detail.is_owner ? <Badge tone="accent">Owner</Badge> : null}
          </>
        }
        title={detail.name}
        description="Automation configuration and recent activity for this server."
        actions={
          <Link to={`/dashboard/server/${guildId}/logs`}>
            <Button size="sm">
              View logs
              <ArrowRight className="h-3.5 w-3.5" />
            </Button>
          </Link>
        }
      />

      <div className="mb-4 grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatTile label="Members" value={detail.member_count?.toLocaleString() ?? "—"} />
        <StatTile label="Online" value={detail.presence_count?.toLocaleString() ?? "—"} />
        <StatTile label="Verifications" value={stats.verification_completed ?? 0} />
        <StatTile
          label="Role changes"
          value={(stats.role_added ?? 0) + (stats.role_removed ?? 0)}
        />
      </div>

      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <SettingsPanel guild={detail} onSaved={(next) => guild.setData({ ...detail, settings: next })} />
        </div>
        <div className="lg:col-span-2">
          <QuickActions guild={detail} onDone={() => { logs.reload(); guild.reload(); }} />
        </div>
      </div>

      <Card className="mt-4">
        <CardHeader
          title="Recent events"
          description="The six most recent entries from this server's audit trail."
          action={
            <Link
              to={`/dashboard/server/${guildId}/logs`}
              className="text-xs text-[var(--color-ink-muted)] hover:text-[var(--color-ink)]"
            >
              All events
            </Link>
          }
        />
        {logs.loading ? <Spinner /> : <LogTable logs={logs.data?.items ?? []} compact />}
      </Card>
    </>
  );
}

/** Verification, welcome and autorole configuration in one form. */
function SettingsPanel({
  guild,
  onSaved,
}: {
  guild: GuildDetail;
  onSaved: (settings: GuildSettings) => void;
}) {
  const [form, setForm] = useState<GuildSettings>(guild.settings);
  const [status, setStatus] = useState<{ error?: string; saved?: boolean }>({});
  const [saving, setSaving] = useState(false);

  const dirty = JSON.stringify(form) !== JSON.stringify(guild.settings);
  const patch = (changes: Partial<GuildSettings>) => {
    setForm((current) => ({ ...current, ...changes }));
    setStatus({});
  };

  const save = async () => {
    setSaving(true);
    try {
      const saved = await api.updateSettings(guild.id, form);
      onSaved(saved);
      setForm(saved);
      setStatus({ saved: true });
    } catch (error) {
      setStatus({ error: error instanceof ApiError ? error.message : String(error) });
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardHeader
        title="Automation"
        description="Changes apply to the bot immediately."
        icon={<Wand2 className="h-4 w-4" />}
        action={
          <Button variant="primary" size="sm" onClick={save} loading={saving} disabled={!dirty}>
            <Save className="h-3.5 w-3.5" />
            Save
          </Button>
        }
      />
      <CardBody className="space-y-6">
        {status.error ? <ErrorNote message={status.error} /> : null}
        {status.saved ? (
          <p className="text-xs text-[var(--color-positive)]">Settings saved.</p>
        ) : null}

        <div className="space-y-3">
          <Toggle
            label="Verification"
            description="Assign a role once a member completes verification."
            checked={form.verification_enabled}
            onChange={(value) => patch({ verification_enabled: value })}
          />
          <Field label="Verified role">
            <Select
              value={form.verified_role_id ?? ""}
              onChange={(event) => patch({ verified_role_id: event.target.value || null })}
            >
              <option value="">Not configured</option>
              {guild.roles.map((role) => (
                <option key={role.id} value={role.id} disabled={role.managed}>
                  {role.name}
                  {role.managed ? " (managed by an integration)" : ""}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <div className="space-y-3 border-t border-[var(--color-border)] pt-5">
          <Toggle
            label="Welcome message"
            description="Posted by the bot when a member joins."
            checked={form.welcome_enabled}
            onChange={(value) => patch({ welcome_enabled: value })}
          />
          <Field label="Welcome channel">
            <Select
              value={form.welcome_channel_id ?? ""}
              onChange={(event) => patch({ welcome_channel_id: event.target.value || null })}
            >
              <option value="">Not configured</option>
              {guild.channels.map((channel) => (
                <option key={channel.id} value={channel.id}>
                  #{channel.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Message"
            hint="Placeholders: {user} {username} {server} {member_count}"
          >
            <Textarea
              value={form.welcome_message}
              maxLength={2000}
              onChange={(event) => patch({ welcome_message: event.target.value })}
            />
          </Field>
        </div>

        <div className="space-y-3 border-t border-[var(--color-border)] pt-5">
          <Toggle
            label="Join autorole"
            description="Give every new member a role automatically."
            checked={form.autorole_enabled}
            onChange={(value) => patch({ autorole_enabled: value })}
          />
          <Field label="Autorole">
            <Select
              value={form.autorole_role_id ?? ""}
              onChange={(event) => patch({ autorole_role_id: event.target.value || null })}
            >
              <option value="">Not configured</option>
              {guild.roles.map((role) => (
                <option key={role.id} value={role.id} disabled={role.managed}>
                  {role.name}
                </option>
              ))}
            </Select>
          </Field>
        </div>
      </CardBody>
    </Card>
  );
}

/** Run an automation by hand -- the same endpoints the bot uses. */
function QuickActions({ guild, onDone }: { guild: GuildDetail; onDone: () => void }) {
  const [memberId, setMemberId] = useState("");
  const [roleId, setRoleId] = useState(guild.roles[0]?.id ?? "");
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<{ ok?: string; error?: string }>({});

  const run = async (key: string, action: () => Promise<{ message: string }>) => {
    setBusy(key);
    setResult({});
    try {
      const response = await action();
      setResult({ ok: response.message });
      onDone();
    } catch (error) {
      setResult({ error: error instanceof ApiError ? error.message : String(error) });
    } finally {
      setBusy(null);
    }
  };

  return (
    <Card className="h-full">
      <CardHeader
        title="Quick actions"
        description="Trigger an automation manually."
        icon={<MessageSquare className="h-4 w-4" />}
      />
      <CardBody className="space-y-5">
        {result.error ? <ErrorNote message={result.error} /> : null}
        {result.ok ? <p className="text-xs text-[var(--color-positive)]">{result.ok}</p> : null}

        <Button
          className="w-full"
          loading={busy === "verify"}
          onClick={() => run("verify", () => api.verify(guild.id))}
        >
          <BadgeCheck className="h-3.5 w-3.5" />
          Verify my account
        </Button>

        <div className="space-y-3 border-t border-[var(--color-border)] pt-5">
          <Field label="Member ID" hint="Right-click a member in Discord with developer mode on.">
            <input
              value={memberId}
              onChange={(event) => setMemberId(event.target.value)}
              placeholder="900000000000000042"
              inputMode="numeric"
              className="w-full rounded-lg border border-[var(--color-border-strong)] bg-[var(--color-canvas)] px-3 py-2 font-mono text-sm placeholder:text-[var(--color-ink-subtle)] focus:border-[var(--color-accent)] focus:outline-none"
            />
          </Field>
          <Field label="Role">
            <Select value={roleId} onChange={(event) => setRoleId(event.target.value)}>
              {guild.roles.map((role) => (
                <option key={role.id} value={role.id} disabled={role.managed}>
                  {role.name}
                </option>
              ))}
            </Select>
          </Field>
          <div className="flex gap-2">
            <Button
              className="flex-1"
              size="sm"
              loading={busy === "add"}
              disabled={!memberId || !roleId}
              onClick={() => run("add", () => api.roleAction(guild.id, "add", memberId, roleId))}
            >
              <UserPlus className="h-3.5 w-3.5" />
              Add role
            </Button>
            <Button
              className="flex-1"
              size="sm"
              variant="danger"
              loading={busy === "remove"}
              disabled={!memberId || !roleId}
              onClick={() => run("remove", () => api.roleAction(guild.id, "remove", memberId, roleId))}
            >
              Remove
            </Button>
          </div>
        </div>
      </CardBody>
    </Card>
  );
}
