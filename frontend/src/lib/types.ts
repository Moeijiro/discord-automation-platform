/** Mirrors the Pydantic schemas served by the FastAPI backend. */

export interface User {
  discord_id: string;
  username: string;
  global_name: string | null;
  avatar: string | null;
  display_name: string;
  avatar_url: string;
}

export interface GuildSummary {
  id: string;
  name: string;
  icon_url: string | null;
  bot_present: boolean;
  manageable: boolean;
  is_owner: boolean;
  permissions: string[];
}

export interface Role {
  id: string;
  name: string;
  color: number;
  position: number;
  managed: boolean;
}

export interface Channel {
  id: string;
  name: string;
}

export interface GuildSettings {
  verification_enabled: boolean;
  verified_role_id: string | null;
  welcome_enabled: boolean;
  welcome_channel_id: string | null;
  welcome_message: string;
  autorole_enabled: boolean;
  autorole_role_id: string | null;
}

export interface GuildDetail extends GuildSummary {
  member_count: number | null;
  presence_count: number | null;
  roles: Role[];
  channels: Channel[];
  settings: GuildSettings;
  stats: Record<string, number>;
}

export type EventType =
  | "verification_completed"
  | "role_added"
  | "role_removed"
  | "member_joined"
  | "welcome_sent"
  | "settings_updated"
  | "webhook_received"
  | "automation_failed";

export interface AutomationLog {
  id: number;
  event_type: EventType | string;
  actor_type: "user" | "bot" | "webhook" | "system";
  target_discord_id: string | null;
  target_label: string | null;
  message: string;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface LogPage {
  items: AutomationLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface ActionResult {
  ok: boolean;
  message: string;
  log: AutomationLog | null;
}

export interface ModeInfo {
  mode: "live" | "demo";
  demo: boolean;
  discord_configured: boolean;
}
