import { createRouter, createWebHistory } from "vue-router";
import { useAuth } from "@/stores/auth";

const routes = [
  { path: "/login", name: "login", component: () => import("@/views/LoginView.vue"), meta: { public: true } },
  // The file list IS the home page (no separate dashboard). "/" renders FilesView.
  { path: "/", name: "files", component: () => import("@/views/FilesView.vue") },
  { path: "/folder/:id", name: "folder", component: () => import("@/views/FilesView.vue"), props: true },
  { path: "/shared", name: "shared", component: () => import("@/views/FilesView.vue"), props: { shared: true } },
  { path: "/file/:id", name: "editor", component: () => import("@/views/EditorView.vue"), props: true },
  { path: "/profile", name: "profile", component: () => import("@/views/ProfileView.vue") },
  // Admin is gated by nginx BasicAuth at the HTTP layer, not by an app session,
  // so these routes are public to the SPA router.
  { path: "/admin", name: "admin", component: () => import("@/views/AdminView.vue"), meta: { public: true } },
  { path: "/admin/users/:id", name: "admin-user", component: () => import("@/views/AdminUserView.vue"), props: true, meta: { public: true } },
  { path: "/:pathMatch(.*)*", redirect: "/" },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to) => {
  const store = useAuth();
  if (!store.ready) await store.fetchMe();
  if (!to.meta.public && !store.user) {
    return { name: "login", query: to.fullPath !== "/" ? { redirect: to.fullPath } : {} };
  }
  if (to.name === "login" && store.user && !to.query.magic) {
    return { name: "files" };
  }
  return true;
});
