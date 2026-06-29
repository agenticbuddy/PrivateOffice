// Typed API client. Same-origin; the session cookie is sent automatically.
import axios from "axios";
import type {
  ActiveSession,
  ActivityEntry,
  AdminOverview,
  AdminUserDetail,
  AdminUserSummary,
  AuditEntry,
  CreatableFormat,
  DirectoryUser,
  EditorSession,
  NodeItem,
  Role,
  ShareItem,
  User,
  VersionItem,
} from "./types";

const http = axios.create({ baseURL: "/", withCredentials: true });

// ---- auth ----
export const auth = {
  async me(): Promise<User> {
    return (await http.get("/api/auth/me")).data;
  },
  async login(email: string, password: string): Promise<User> {
    return (await http.post("/api/auth/login", { email, password })).data;
  },
  async magic(token: string): Promise<User> {
    return (await http.post(`/api/auth/magic/${token}`)).data;
  },
  async logout(): Promise<void> {
    await http.post("/api/auth/logout");
  },
  async setPassword(password: string): Promise<User> {
    return (await http.post("/api/auth/password", { password })).data;
  },
  async setLocale(locale: string): Promise<User> {
    return (await http.patch("/api/auth/me", { locale })).data;
  },
  async setDesign(design: string): Promise<User> {
    return (await http.patch("/api/auth/me", { design })).data;
  },
};

// ---- nodes ----
export const nodes = {
  async list(parent?: string | null): Promise<NodeItem[]> {
    return (await http.get("/api/nodes", { params: parent ? { parent } : {} })).data;
  },
  async sharedWithMe(): Promise<NodeItem[]> {
    return (await http.get("/api/nodes/shared-with-me")).data;
  },
  async recent(limit = 12): Promise<NodeItem[]> {
    return (await http.get("/api/nodes/recent", { params: { limit } })).data;
  },
  async search(q: string): Promise<NodeItem[]> {
    return (await http.get("/api/nodes/search", { params: { q } })).data;
  },
  async get(id: string): Promise<NodeItem> {
    return (await http.get(`/api/nodes/${id}`)).data;
  },
  async createFolder(name: string, parent_id: string | null): Promise<NodeItem> {
    return (await http.post("/api/nodes/folder", { name, parent_id })).data;
  },
  async createFile(name: string, format: string, parent_id: string | null): Promise<NodeItem> {
    return (await http.post("/api/nodes/file", { name, format, parent_id })).data;
  },
  async upload(file: File, parent_id: string | null): Promise<NodeItem> {
    const fd = new FormData();
    fd.append("file", file);
    if (parent_id) fd.append("parent_id", parent_id);
    return (await http.post("/api/nodes/upload", fd)).data;
  },
  async rename(id: string, name: string): Promise<NodeItem> {
    return (await http.patch(`/api/nodes/${id}`, { name })).data;
  },
  async remove(id: string): Promise<void> {
    await http.delete(`/api/nodes/${id}`);
  },
  downloadUrl(id: string): string {
    return `/api/nodes/${id}/download`;
  },
  async versions(id: string): Promise<VersionItem[]> {
    return (await http.get(`/api/nodes/${id}/versions`)).data;
  },
  async formats(): Promise<{ creatable: CreatableFormat[]; supported_ext: string[] }> {
    return (await http.get("/api/formats")).data;
  },
};

// ---- sharing ----
export const shares = {
  async list(nodeId: string): Promise<ShareItem[]> {
    return (await http.get(`/api/nodes/${nodeId}/shares`)).data;
  },
  async upsert(nodeId: string, user_id: string, role: Role): Promise<ShareItem> {
    return (await http.put(`/api/nodes/${nodeId}/shares`, { user_id, role })).data;
  },
  async remove(nodeId: string, userId: string): Promise<void> {
    await http.delete(`/api/nodes/${nodeId}/shares/${userId}`);
  },
};

export const directory = {
  async users(): Promise<DirectoryUser[]> {
    return (await http.get("/api/users")).data;
  },
};

export const editor = {
  async session(nodeId: string): Promise<EditorSession> {
    return (await http.get(`/api/editor/${nodeId}`)).data;
  },
};

// ---- admin (behind nginx BasicAuth) ----
export const admin = {
  async users(): Promise<AdminUserSummary[]> {
    return (await http.get("/admin/api/users")).data;
  },
  async createUser(email: string, full_name: string, locale: string): Promise<AdminUserSummary> {
    return (await http.post("/admin/api/users", { email, full_name, locale })).data;
  },
  async user(id: string): Promise<AdminUserDetail> {
    return (await http.get(`/admin/api/users/${id}`)).data;
  },
  async patchUser(id: string, patch: Partial<{ full_name: string; bio: string; locale: string; is_active: boolean }>): Promise<AdminUserDetail> {
    return (await http.patch(`/admin/api/users/${id}`, patch)).data;
  },
  async magicLink(id: string): Promise<{ url: string; expires_at: string }> {
    return (await http.post(`/admin/api/users/${id}/magic-link`)).data;
  },
  async setPassword(id: string, password: string): Promise<void> {
    await http.post(`/admin/api/users/${id}/password`, { password });
  },
  async userNodes(id: string): Promise<NodeItem[]> {
    return (await http.get(`/admin/api/users/${id}/nodes`)).data;
  },
  async deleteNode(userId: string, nodeId: string): Promise<void> {
    await http.delete(`/admin/api/users/${userId}/nodes/${nodeId}`);
  },
  async audit(id: string): Promise<AuditEntry[]> {
    return (await http.get(`/admin/api/users/${id}/audit`)).data;
  },
  async overview(): Promise<AdminOverview> {
    return (await http.get("/admin/api/overview")).data;
  },
  async sessions(): Promise<ActiveSession[]> {
    return (await http.get("/admin/api/sessions")).data;
  },
  async activity(params: { action?: string; user_id?: string; limit?: number } = {}): Promise<ActivityEntry[]> {
    return (await http.get("/admin/api/activity", { params })).data;
  },
  downloadNodeUrl(nodeId: string): string {
    return `/admin/api/nodes/${nodeId}/download`;
  },
};

export { http };
