export type Design = "glass" | "glass2" | "classic";

export interface User {
  id: string;
  email: string;
  full_name: string;
  locale: string;
  design: Design;
  bio: string | null;
  is_admin: boolean;
  is_active: boolean;
  has_password: boolean;
}

export type NodeType = "folder" | "file";
export type Role = "owner" | "editor" | "reader";

export interface NodeItem {
  id: string;
  type: NodeType;
  name: string;
  parent_id: string | null;
  co_format: string | null;
  mime: string | null;
  size: number | null;
  created_by: string;
  creator_locale: string | null;
  updated_at: string;
  my_role: Role | null;
}

export interface ShareItem {
  user_id: string;
  role: Role;
  full_name: string;
  email: string;
}

export interface DirectoryUser {
  id: string;
  full_name: string;
  email: string;
}

export interface EditorSession {
  iframe_url: string;
  access_token: string;
  access_token_ttl: number;
  lang: string;
  can_write: boolean;
}

export interface CreatableFormat {
  format: string;
  mime: string;
  category: string;
}

export type NotificationType = "view" | "edit" | "share" | "unshare";

export interface NotificationItem {
  id: number;
  type: NotificationType;
  actor_id: string | null;
  actor_name: string | null;
  node_id: string | null;
  node_name: string | null;
  role: Role | null;
  count: number;
  read: boolean;
  created_at: string;
}

export interface NotificationList {
  items: NotificationItem[];
  unread: number;
}

export interface VersionItem {
  id: string;
  size: number;
  author_id: string | null;
  created_at: string;
}

// admin
export interface AdminUserSummary extends User {
  files: number;
  folders: number;
}

export interface AdminUserDetail extends User {
  created_at: string;
  stats: { files: number; folders: number; shared_out: number; versions: number };
}

export interface AuditEntry {
  action: string;
  node_id: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

export interface AdminOverview {
  users: number;
  active_users: number;
  admins: number;
  with_password: number;
  files: number;
  folders: number;
  versions: number;
  shares: number;
  current_bytes: number;
  online: number;
  logins_7d: number;
}

export interface ActiveSession {
  user_id: string;
  full_name: string;
  email: string;
  since: string | null;
  sessions: number;
}

export interface ActivityEntry {
  id: number;
  action: string;
  actor_id: string | null;
  actor_name: string | null;
  actor_email: string | null;
  node_id: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}
