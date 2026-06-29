<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/stores/auth";
import Avatar from "./ui/Avatar.vue";
import Icon from "./ui/Icon.vue";

const { t } = useI18n();
const auth = useAuth();
const router = useRouter();
const route = useRoute();
const menu = ref(false);

const nav = computed(() => [
  { name: "start", to: { name: "start" }, icon: "space_dashboard", label: t("nav.home") },
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

// Esc-to-close: the trigger button keeps focus, so a template @keydown.esc on the
// non-focusable menu/scrim would never fire — listen at the document level instead,
// only while the menu is open (mirrors BaseModal's e.key === "Escape" idiom).
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") menu.value = false;
}
watch(menu, (open) => {
  open ? document.addEventListener("keydown", onKey) : document.removeEventListener("keydown", onKey);
});
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="shell">
    <!-- LEFT RAIL -->
    <nav class="rail glass">
      <div class="logo" @click="go({ name: 'start' })">P</div>
      <button
        v-for="n in nav"
        :key="n.name"
        class="railbtn"
        :class="{ active: isActive(n.name) }"
        :title="n.label"
        @click="go(n.to)"
      >
        <Icon :name="n.icon" :size="22" :fill="isActive(n.name)" />
        <span class="rlabel">{{ n.label }}</span>
      </button>

      <div class="grow" />

      <div class="userwrap">
        <button class="userbtn" @click="menu = !menu" :title="auth.user?.full_name">
          <Avatar v-if="auth.user" :name="auth.user.full_name" :id="auth.user.id" :size="34" />
        </button>
        <Transition name="pop">
          <div v-if="menu" class="menu glass" @click.stop>
            <div class="muser">
              <strong>{{ auth.user?.full_name }}</strong>
              <span class="t-faint t-small">{{ auth.user?.email }}</span>
            </div>
            <button class="mitem" @click="go({ name: 'profile' })">
              <Icon name="person" :size="18" />{{ t("nav.profile") }}
            </button>
            <a v-if="auth.user?.is_admin" class="mitem" href="/admin">
              <Icon name="shield_person" :size="18" />{{ t("nav.admin") }}
            </a>
            <button class="mitem danger" @click="logout">
              <Icon name="logout" :size="18" />{{ t("nav.logout") }}
            </button>
          </div>
        </Transition>
      </div>
    </nav>

    <!-- SCRIM for menu -->
    <div v-if="menu" class="scrim" @click="menu = false" />

    <!-- MAIN -->
    <main class="main"><slot /></main>
  </div>
</template>

<style scoped>
.shell { height: 100%; display: flex; padding: 6px; gap: 6px; min-height: 0; }

.rail {
  flex: 0 0 var(--rail-w);
  border-radius: var(--r-lg);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 6px;
  /* own stacking context above the content so the user menu is never covered by
     the (backdrop-filtered) content panels that come later in the DOM */
  position: relative;
  z-index: 50;
}
.logo {
  width: 38px; height: 38px; border-radius: var(--r-md);
  background: var(--accent-grad); color: #fff; font-weight: 800; font-size: 16px;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  box-shadow: 0 4px 12px rgba(10, 127, 94, 0.34); margin-bottom: 6px; flex: none;
}
.railbtn {
  width: 100%; min-height: 48px; padding: 6px 2px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;
  border: none; background: transparent; border-radius: var(--r-md);
  cursor: pointer; color: var(--ink-2); flex: none;
  transition: background 0.12s ease, color 0.12s ease;
}
.railbtn:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.railbtn.active { background: var(--accent-soft); color: var(--accent-ink); }
/* Wrap to at most 2 centred lines so wide labels ("Shared with me" in EN/RU/AR/…)
   stay fully readable instead of single-line ellipsis. break-word lets the rare
   unbreakable long token wrap rather than clip. */
.rlabel {
  font-size: 9.5px; font-weight: 600; letter-spacing: 0.01em;
  text-align: center; line-height: 1.15; overflow-wrap: break-word;
  white-space: normal; overflow: hidden;
  display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2;
}
.grow { flex: 1; }

.userwrap { position: relative; flex: none; }
.userbtn { border: none; background: transparent; padding: 2px; cursor: pointer; border-radius: var(--r-full); display: flex; }
.menu {
  position: absolute;
  inset-inline-start: calc(100% + 8px);
  bottom: 0;
  min-width: 210px;
  border-radius: var(--r-lg);
  padding: var(--s-2);
  display: flex; flex-direction: column; gap: 2px;
  z-index: 60;
}
.muser { padding: var(--s-2) var(--s-3) var(--s-3); display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid var(--line); margin-bottom: var(--s-1); }
.mitem {
  display: flex; align-items: center; gap: var(--s-2);
  text-align: start; border: none; background: transparent;
  padding: var(--s-2) var(--s-3); border-radius: var(--r-sm);
  font-size: 13.5px; cursor: pointer; color: var(--ink); text-decoration: none;
}
.mitem:hover { background: rgba(20, 32, 56, 0.06); }
.mitem.danger { color: var(--neg); }
.scrim { position: fixed; inset: 0; z-index: 40; }

.main { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; }

.pop-enter-active, .pop-leave-active { transition: all 0.12s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: translateY(6px); }

/* mobile: rail becomes a bottom bar */
@media (max-width: 720px) {
  .shell { flex-direction: column-reverse; padding: 4px; gap: 4px; }
  .rail {
    flex: 0 0 auto; min-height: 56px; flex-direction: row; width: 100%; padding: 4px 8px;
    justify-content: space-around; align-items: center;
  }
  .logo { display: none; }
  /* bottom bar: items share the (ample) phone width so labels fit on 1–2 lines;
     min-height lets the bar grow a touch rather than clip the 2nd line */
  .railbtn { flex: 1 1 0; max-width: 120px; min-height: 46px; }
  .grow { display: none; }
  .menu { inset-inline-start: auto; inset-inline-end: 0; bottom: calc(100% + 8px); }
}
</style>
