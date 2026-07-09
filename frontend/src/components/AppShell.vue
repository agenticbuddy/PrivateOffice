<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/stores/auth";
import Avatar from "./ui/Avatar.vue";
import Icon from "./ui/Icon.vue";

// Enterprise-Style document centre shell (per the "Collabora Enterprise Style" mockup, rebranded
// PrivateOffice): a top bar (brand + search + user), a horizontal section nav, and a collapsible left
// sidebar filled by the page via the #sidebar slot. Blue accent is scoped to this shell only, so the
// document centre reads as the blue "Enterprise" surface while the editor keeps its green Liquid Glass.
const { t } = useI18n();
const auth = useAuth();
const router = useRouter();
const route = useRoute();
const menu = ref(false);
// top-bar search: on Enter, go to the file list filtered by the query (FilesView reads route.query.q).
const q = ref((route.query.q as string) || "");
function runSearch() { router.push({ name: "files", query: q.value ? { q: q.value } : {} }); }
// sidebar collapse persists across navigations (localStorage), per the user's "сворачиваемый/разворачиваемый"
const collapsed = ref(localStorage.getItem("po.sidebar.collapsed") === "1");
watch(collapsed, (v) => localStorage.setItem("po.sidebar.collapsed", v ? "1" : "0"));

// No "Home" — the file list IS the home page (per the design).
const nav = computed(() => [
  { name: "files", to: { name: "files" }, icon: "folder", label: t("nav.myFiles") },
  { name: "shared", to: { name: "shared" }, icon: "group", label: t("nav.sharedWithMe") },
]);
function isActive(name: string) {
  if (name === "files") return route.name === "files" || route.name === "folder";
  return route.name === name;
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
      <button class="tbicon" :title="t('nav.notifications')"><Icon name="notifications" :size="20" /><span class="dot" /></button>
      <button class="tbicon" :title="t('nav.profile')" @click="go({ name: 'profile' })"><Icon name="settings" :size="20" /></button>

      <div class="userwrap">
        <button class="userbtn" @click="menu = !menu" :title="auth.user?.full_name">
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

    <!-- SECTION NAV -->
    <nav class="tabs">
      <button
        v-for="n in nav"
        :key="n.name"
        class="tab"
        :class="{ active: isActive(n.name) }"
        @click="go(n.to)"
      >
        <Icon :name="n.icon" :size="18" :fill="isActive(n.name)" /><span>{{ n.label }}</span>
      </button>
    </nav>

    <!-- BODY: sidebar · main -->
    <div class="body">
      <aside class="sidebar"><slot name="sidebar" /></aside>
      <main class="main"><slot /></main>
    </div>

    <div v-if="menu" class="scrim" @click="menu = false" />
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
.tbicon { position: relative; border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 38px; height: 38px; border-radius: var(--r-full); display: flex; align-items: center; justify-content: center; }
.tbicon:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.tbicon .dot { position: absolute; top: 8px; inset-inline-end: 9px; width: 7px; height: 7px; border-radius: 50%; background: var(--neg); border: 1.5px solid #fff; }

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
