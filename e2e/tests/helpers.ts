import { request as pwRequest, type APIRequestContext } from "@playwright/test";

const BASE = process.env.BASE_URL || "http://localhost:8088";

export function uniqEmail(prefix: string): string {
  return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 1e6)}@example.com`;
}

export async function adminCtx(): Promise<APIRequestContext> {
  return pwRequest.newContext({
    baseURL: BASE,
    httpCredentials: { username: "admin", password: "123" },
  });
}

export async function createUser(email: string, fullName: string, locale = "en") {
  const ctx = await adminCtx();
  const res = await ctx.post("/admin/api/users", {
    data: { email, full_name: fullName, locale },
  });
  const user = await res.json();
  await ctx.dispose();
  return user as { id: string; email: string };
}

export async function setUserPassword(userId: string, password: string) {
  const ctx = await adminCtx();
  await ctx.post(`/admin/api/users/${userId}/password`, { data: { password } });
  await ctx.dispose();
}

/** Logged-in API context for a user (cookie stored in the context). */
export async function userCtx(email: string, password: string): Promise<APIRequestContext> {
  const ctx = await pwRequest.newContext({ baseURL: BASE });
  await ctx.post("/api/auth/login", { data: { email, password } });
  return ctx;
}

export async function createFolderApi(ctx: APIRequestContext, name: string) {
  const res = await ctx.post("/api/nodes/folder", { data: { name, parent_id: null } });
  return res.json();
}

/** Provision a user with a password in one call. */
export async function provisionUser(prefix: string, name: string, password = "test1234", locale = "en") {
  const email = uniqEmail(prefix);
  const u = await createUser(email, name, locale);
  await setUserPassword(u.id, password);
  return { id: u.id, email, password, name };
}
