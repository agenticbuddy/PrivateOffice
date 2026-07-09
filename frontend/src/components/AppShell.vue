<script setup lang="ts">
import { computed, ref, watch, onMounted, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";
import { useNotifications } from "@/stores/notifications";
import type { NotificationItem } from "@/api/types";
import Avatar from "./ui/Avatar.vue";
import Icon from "./ui/Icon.vue";

// Enterprise-Style document centre shell (per the "Collabora Enterprise Style" mockup, rebranded
// PrivateOffice): a top bar (brand + search + user), a horizontal section nav, and a collapsible left
// sidebar filled by the page via the #sidebar slot. Blue accent is scoped to this shell only, so the
// document centre reads as the blue "Enterprise" surface while the editor keeps its green Liquid Glass.
const { t, locale } = useI18n();
const auth = useAuth();
const toast = useToast();
const notif = useNotifications();
const router = useRouter();
const route = useRoute();
const menu = ref(false);
const bell = ref(false); // notification panel open state

// ---- notifications: poll while the doc-centre header is mounted ----
onMounted(() => notif.startPolling());
onBeforeUnmount(() => notif.stopPolling());

// icon per notification type
const NOTIF_ICON: Record<string, string> = {
  view: "visibility", edit: "edit", share: "group_add", unshare: "person_remove",
};
// localized one-line message; "…viewed «doc» (3×)" when a view/edit was collapsed
function notifText(n: NotificationItem): string {
  const base = t(`notif.msg.${n.type}`, { actor: n.actor_name || "—", node: n.node_name || "—" });
  return n.count > 1 ? `${base} (${n.count}×)` : base;
}
// coarse relative time (just now / 5 min / 3 h / 2 d), localized
const rtf = new Intl.RelativeTimeFormat(locale.value as string, { numeric: "auto" });
function relTime(iso: string): string {
  const diff = (new Date(iso).getTime() - Date.now()) / 1000;
  const a = Math.abs(diff);
  if (a < 60) return t("notif.justNow");
  if (a < 3600) return rtf.format(Math.round(diff / 60), "minute");
  if (a < 86400) return rtf.format(Math.round(diff / 3600), "hour");
  return rtf.format(Math.round(diff / 86400), "day");
}
function openNotif(n: NotificationItem) {
  notif.markRead(n.id);
  bell.value = false;
  if (n.node_id) router.push({ name: "editor", params: { id: n.node_id } });
}
function toggleBell() {
  menu.value = false;
  bell.value = !bell.value;
  if (bell.value) notif.fetch(); // refresh on open
}
// top-bar search: on Enter, go to the file list filtered by the query (FilesView reads route.query.q).
const q = ref((route.query.q as string) || "");
function runSearch() { router.push({ name: "files", query: q.value ? { q: q.value } : {} }); }
// sidebar collapse persists across navigations (localStorage), per the user's "сворачиваемый/разворачиваемый"
const collapsed = ref(localStorage.getItem("po.sidebar.collapsed") === "1");
watch(collapsed, (v) => localStorage.setItem("po.sidebar.collapsed", v ? "1" : "0"));

// Section nav — matches the Enterprise Style mockup's rows (Home / Documents / Spreadsheets /
// Presentations / Shared with me / Templates / Trash / +), adapted to PrivateOffice: Home = all files,
// Documents/Spreadsheets/Presentations = files filtered by type (?type=doc|sheet|slide), Shared = /shared.
// Templates & Trash aren't features yet → a "coming soon" toast (kept for parity with the design).
const nav = computed(() => [
  { key: "home", icon: "home", label: t("nav.home"), to: { name: "files" } },
  { key: "documents", icon: "folder", label: t("nav.documents"), to: { name: "files", query: { type: "doc" } } },
  { key: "sheets", icon: "table_chart", label: t("nav.spreadsheets"), to: { name: "files", query: { type: "sheet" } } },
  { key: "slides", icon: "slideshow", label: t("nav.presentations"), to: { name: "files", query: { type: "slide" } } },
  { key: "shared", icon: "group", label: t("nav.sharedWithMe"), to: { name: "shared" } },
  { key: "templates", icon: "dashboard", label: t("nav.templates"), soon: true },
  { key: "trash", icon: "delete", label: t("nav.trash"), soon: true },
]);
function isActive(key: string) {
  const type = route.query.type as string | undefined;
  if (key === "home") return (route.name === "files" || route.name === "folder") && !type;
  if (key === "documents") return route.name === "files" && type === "doc";
  if (key === "sheets") return route.name === "files" && type === "sheet";
  if (key === "slides") return route.name === "files" && type === "slide";
  if (key === "shared") return route.name === "shared";
  return false;
}
function clickNav(n: any) { if (n.soon) { toast.push(t("common.comingSoon")); return; } go(n.to); }
// "+" creates a new document in the CURRENT context — stay in the folder (add ?new=1 to the current
// route). Only the read-only "Shared with me" view can't host new docs, so there fall back to root.
function newHere() {
  if (route.name === "shared") { router.push({ name: "files", query: { new: "1" } }); return; }
  router.push({ query: { ...route.query, new: "1" } });
}
async function logout() {
  menu.value = false;
  await auth.logout();
  router.push({ name: "login" });
}
function go(target: any) {
  menu.value = false;
  router.push(target);
}
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") menu.value = false;
}
watch(menu, (open) => {
  open ? document.addEventListener("keydown", onKey) : document.removeEventListener("keydown", onKey);
});
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="docshell" :class="{ collapsed }">
    <!-- TOP BAR: brand · search · status/user -->
    <header class="topbar">
      <button class="collapse" :title="t('nav.toggleSidebar')" @click="collapsed = !collapsed">
        <Icon name="menu" :size="20" />
      </button>
      <div class="brand" @click="go({ name: 'files' })">
        <div class="mark">P</div>
        <span class="bname"><strong>Private</strong>Office</span>
      </div>

      <div class="search">
        <Icon name="search" :size="18" class="sicon" />
        <input v-model="q" type="text" :placeholder="t('nav.searchPlaceholder')" @keyup.enter="runSearch" />
        <button v-if="q" class="clearq" :title="t('common.cancel')" @click="q=''; runSearch()"><Icon name="close" :size="16" /></button>
      </div>

      <div class="spacer" />

      <div class="synced"><Icon name="cloud_done" :size="18" /><span>{{ t("nav.allSynced") }}</span></div>
      <span class="tbsep" />

      <div class="bellwrap">
        <button class="tbicon" :class="{ active: bell }" :title="t('nav.notifications')" @click.stop="toggleBell">
          <Icon name="notifications" :size="20" />
          <span v-if="notif.unread" class="badge">{{ notif.unread > 9 ? "9+" : notif.unread }}</span>
        </button>
        <Transition name="pop">
          <div v-if="bell" class="notifpanel" @click.stop>
            <div class="notifhead">
              <strong>{{ t("notif.title") }}</strong>
              <button v-if="notif.unread" class="markall" @click="notif.markAllRead()">{{ t("notif.markAllRead") }}</button>
            </div>
            <div class="notiflist">
              <button v-for="n in notif.items" :key="n.id" class="notifitem" :class="{ unread: !n.read }" @click="openNotif(n)">
                <span class="ni-ic" :class="'ni-' + n.type"><Icon :name="NOTIF_ICON[n.type] || 'notifications'" :size="18" /></span>
                <span class="ni-body">
                  <span class="ni-text">{{ notifText(n) }}</span>
                  <span class="ni-time">{{ relTime(n.created_at) }}</span>
                </span>
                <span v-if="!n.read" class="ni-dot" />
              </button>
              <div v-if="!notif.items.length" class="notifempty">
                <Icon name="notifications_off" :size="28" /><span>{{ t("notif.empty") }}</span>
              </div>
            </div>
          </div>
        </Transition>
      </div>

      <button class="tbicon" :title="t('nav.profile')" @click="go({ name: 'profile' })"><Icon name="settings" :size="20" /></button>

      <div class="userwrap">
        <button class="userbtn" @click.stop="bell = false; menu = !menu" :title="auth.user?.full_name">
          <Avatar v-if="auth.user" :name="auth.user.full_name" :id="auth.user.id" :size="34" />
          <span class="uinfo">
            <strong>{{ auth.user?.full_name }}</strong>
            <span class="urole">{{ auth.user?.is_admin ? t("nav.admin") : auth.user?.email }}</span>
          </span>
          <Icon name="expand_more" :size="16" class="uchev" />
        </button>
        <Transition name="pop">
          <div v-if="menu" class="menu" @click.stop>
            <div class="muser">
              <strong>{{ auth.user?.full_name }}</strong>
              <span class="t-faint t-small">{{ auth.user?.email }}</span>
            </div>
            <button class="mitem" @click="go({ name: 'profile' })"><Icon name="person" :size="18" />{{ t("nav.profile") }}</button>
            <a v-if="auth.user?.is_admin" class="mitem" href="/admin"><Icon name="shield_person" :size="18" />{{ t("nav.admin") }}</a>
            <button class="mitem danger" @click="logout"><Icon name="logout" :size="18" />{{ t("nav.logout") }}</button>
          </div>
        </Transition>
      </div>
    </header>

    <!-- SECTION NAV (Home / Documents / Spreadsheets / Presentations / Shared / Templates / Trash / +) -->
    <nav class="tabs">
      <button
        v-for="n in nav"
        :key="n.key"
        class="tab"
        :class="{ active: isActive(n.key) }"
        @click="clickNav(n)"
      >
        <Icon :name="n.icon" :size="18" :fill="isActive(n.key)" /><span>{{ n.label }}</span>
      </button>
      <button class="tabadd" :title="t('files.newDocument')" @click="newHere">
        <Icon name="add" :size="20" />
      </button>
    </nav>

    <!-- BODY: sidebar · main -->
    <div class="body">
      <aside class="sidebar"><slot name="sidebar" /></aside>
      <main class="main"><slot /></main>
    </div>

    <div v-if="menu || bell" class="scrim" @click="menu = false; bell = false" />
  </div>
</template>

<style scoped>
/* Blue "Enterprise" accent scoped to the document centre; the rest of the app / editor stays green. */
.docshell {
  --accent: #2563d9;
  --accent-ink: #1d4fb8;
  --accent-soft: rgba(37, 99, 217, 0.12);
  --accent-grad: linear-gradient(140deg, #2563d9, #1d4fb8);
  height: 100%;
  display: flex;
  flex-direction: column;
  min-height: 0;
  background:
    radial-gradient(50vw 50vw at 100% -10%, rgba(185, 210, 255, 0.22), transparent 66%),
    radial-gradient(40vw 40vw at -6% 8%, rgba(216, 226, 255, 0.18), transparent 70%),
    linear-gradient(160deg, #f5f8fd 0%, #fafbfe 55%, #f5f8fd 100%);
}

/* ---- top bar ---- */
.topbar {
  flex: 0 0 auto; height: 60px;
  display: flex; align-items: center; gap: var(--s-3);
  padding: 0 var(--s-4);
}
.collapse {
  border: none; background: transparent; cursor: pointer; color: var(--ink-2);
  width: 36px; height: 36px; border-radius: var(--r-sm); display: flex; align-items: center; justify-content: center;
}
.collapse:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.brand { display: flex; align-items: center; gap: var(--s-2); cursor: pointer; user-select: none; }
.mark {
  width: 34px; height: 34px; border-radius: var(--r-md);
  background: var(--accent-grad); color: #fff; font-weight: 800; font-size: 16px;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 12px rgba(37, 99, 217, 0.34);
}
.bname { font-size: 18px; color: var(--ink); font-weight: 500; }
.bname strong { font-weight: 800; }

.search {
  flex: 0 1 460px; margin-inline-start: var(--s-4);
  display: flex; align-items: center; gap: var(--s-2);
  height: 40px; padding: 0 var(--s-3);
  background: rgba(255, 255, 255, 0.75); border: 1px solid var(--line);
  border-radius: var(--r-full);
}
.search:focus-within { border-color: var(--accent); background: #fff; }
.search .sicon { color: var(--ink-3); flex: none; }
.search input { border: none; background: transparent; outline: none; width: 100%; font: inherit; font-size: 14px; color: var(--ink); }
.clearq { border: none; background: transparent; cursor: pointer; color: var(--ink-3); display: flex; padding: 2px; border-radius: var(--r-full); flex: none; }
.clearq:hover { background: rgba(20, 32, 56, 0.08); color: var(--ink); }
.spacer { flex: 1; }
.synced { display: flex; align-items: center; gap: var(--s-1); color: var(--accent); font-size: 13px; font-weight: 600; margin-inline-end: var(--s-2); }
.tbsep { width: 1px; height: 24px; background: var(--line); margin-inline: var(--s-1); flex: none; }
.tbicon { position: relative; border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 38px; height: 38px; border-radius: var(--r-full); display: flex; align-items: center; justify-content: center; }
.tbicon:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.tbicon .dot { position: absolute; top: 8px; inset-inline-end: 9px; width: 7px; height: 7px; border-radius: 50%; background: var(--neg); border: 1.5px solid #fff; }
.tbicon.active { background: var(--accent-soft); color: var(--accent-ink); }

/* ---- notifications ---- */
.bellwrap { position: relative; display: flex; }
.badge {
  position: absolute; top: 3px; inset-inline-end: 3px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 8px; background: var(--neg); border: 1.5px solid #fff; color: #fff;
  font-size: 10px; font-weight: 800; line-height: 13px; display: flex; align-items: center; justify-content: center;
}
.notifpanel {
  position: absolute; inset-inline-end: 0; top: calc(100% + 8px); width: 360px; max-width: 92vw; z-index: 60;
  background: rgba(255, 255, 255, 0.95); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  border: 1px solid var(--glass-bd); border-radius: var(--r-lg); box-shadow: var(--shadow-2);
  overflow: hidden;
}
.notifhead { display: flex; align-items: center; justify-content: space-between; padding: var(--s-3) var(--s-3) var(--s-2); border-bottom: 1px solid var(--line); }
.notifhead strong { font-size: 14px; color: var(--ink); }
.markall { border: none; background: transparent; cursor: pointer; color: var(--accent-ink); font: inherit; font-size: 12.5px; font-weight: 600; padding: 2px 4px; border-radius: var(--r-sm); }
.markall:hover { background: var(--accent-soft); }
.notiflist { max-height: 60vh; overflow: auto; padding: var(--s-1); }
.notifitem { width: 100%; display: flex; align-items: flex-start; gap: var(--s-2); text-align: start; border: none; background: transparent; padding: var(--s-2); border-radius: var(--r-md); cursor: pointer; position: relative; }
.notifitem:hover { background: rgba(20, 32, 56, 0.05); }
.notifitem.unread { background: var(--accent-soft); }
.notifitem.unread:hover { background: rgba(37, 99, 217, 0.16); }
.ni-ic { flex: none; width: 32px; height: 32px; border-radius: var(--r-full); display: flex; align-items: center; justify-content: center; background: rgba(20, 32, 56, 0.06); color: var(--ink-2); }
.ni-view { background: rgba(37, 99, 217, 0.12); color: var(--accent-ink); }
.ni-edit { background: rgba(217, 154, 10, 0.14); color: #a9760a; }
.ni-share { background: rgba(35, 150, 90, 0.14); color: #1e8a52; }
.ni-unshare { background: rgba(210, 63, 63, 0.12); color: var(--neg); }
.ni-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ni-text { font-size: 13px; color: var(--ink); line-height: 1.3; }
.ni-time { font-size: 11.5px; color: var(--ink-3); }
.ni-dot { flex: none; align-self: center; width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }
.notifempty { display: flex; flex-direction: column; align-items: center; gap: var(--s-2); padding: var(--s-6) var(--s-4); color: var(--ink-3); font-size: 13px; }

.userwrap { position: relative; margin-inline-start: var(--s-1); }
.userbtn { border: none; background: transparent; padding: 3px 6px 3px 3px; cursor: pointer; border-radius: var(--r-full); display: flex; align-items: center; gap: var(--s-2); }
.userbtn:hover { background: rgba(20, 32, 56, 0.06); }
.uinfo { display: flex; flex-direction: column; align-items: flex-start; line-height: 1.15; }
.uinfo strong { font-size: 13.5px; color: var(--ink); font-weight: 700; }
.urole { font-size: 11.5px; color: var(--ink-3); max-width: 130px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.uchev { color: var(--ink-3); }
@media (max-width: 980px) { .uinfo, .uchev { display: none; } }
.menu {
  position: absolute; inset-inline-end: 0; top: calc(100% + 8px); min-width: 220px;
  background: rgba(255, 255, 255, 0.92); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px);
  border: 1px solid var(--glass-bd); border-radius: var(--r-lg); box-shadow: var(--shadow-2);
  padding: var(--s-2); display: flex; flex-direction: column; gap: 2px; z-index: 60;
}
.muser { padding: var(--s-2) var(--s-3) var(--s-3); display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid var(--line); margin-bottom: var(--s-1); }
.mitem { display: flex; align-items: center; gap: var(--s-2); text-align: start; border: none; background: transparent; padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); font-size: 13.5px; cursor: pointer; color: var(--ink); text-decoration: none; }
.mitem:hover { background: var(--accent-soft); color: var(--accent-ink); }
.mitem.danger { color: var(--neg); }
.mitem.danger:hover { background: rgba(210, 63, 63, 0.1); color: var(--neg); }
.scrim { position: fixed; inset: 0; z-index: 40; }

/* ---- section nav ---- */
.tabs { flex: 0 0 auto; display: flex; gap: var(--s-1); padding: 0 var(--s-4) var(--s-2); }
.tab {
  display: flex; align-items: center; gap: var(--s-2);
  height: 40px; padding: 0 var(--s-4);
  border: none; background: transparent; border-radius: var(--r-md);
  cursor: pointer; color: var(--ink-2); font-size: 14px; font-weight: 600;
}
.tab:hover { background: rgba(255, 255, 255, 0.6); color: var(--ink); }
.tab.active { background: rgba(255, 255, 255, 0.85); color: var(--accent-ink); box-shadow: var(--shadow-1); }
.tabadd {
  width: 40px; height: 40px; flex: none;
  border: none; background: transparent; border-radius: var(--r-md);
  cursor: pointer; color: var(--ink-3); display: flex; align-items: center; justify-content: center;
}
.tabadd:hover { background: rgba(255, 255, 255, 0.6); color: var(--accent-ink); }

/* ---- body ---- */
.body { flex: 1; min-height: 0; display: flex; gap: var(--s-3); padding: 0 var(--s-4) var(--s-4); }
.sidebar {
  flex: 0 0 var(--sidebar-w); min-width: 0;
  background: rgba(255, 255, 255, 0.66); -webkit-backdrop-filter: blur(var(--glass-blur)); backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-bd); border-radius: var(--r-xl);
  padding: var(--s-3); overflow: auto;
  transition: flex-basis 0.18s ease, opacity 0.14s ease;
}
.docshell.collapsed .sidebar { flex-basis: 0; padding: 0; border-width: 0; opacity: 0; overflow: hidden; }
.main {
  flex: 1; min-width: 0; min-height: 0;
  background: rgba(255, 255, 255, 0.72); -webkit-backdrop-filter: blur(var(--glass-blur)); backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-bd); border-radius: var(--r-xl);
  display: flex; flex-direction: column; overflow: hidden;
}

@media (max-width: 860px) {
  .search { flex-basis: 200px; }
  .bname { display: none; }
  .body { flex-direction: column; }
  .sidebar { flex: 0 0 auto; }
  .docshell.collapsed .sidebar { display: none; }
}

.pop-enter-active, .pop-leave-active { transition: all 0.12s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(-6px); }
</style>
