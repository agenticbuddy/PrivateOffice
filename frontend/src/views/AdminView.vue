<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { admin } from "@/api/client";
import type { ActiveSession, ActivityEntry, AdminOverview, AdminUserSummary } from "@/api/types";
import { useToast } from "@/stores/toast";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseSelect from "@/components/ui/BaseSelect.vue";
import LanguagePicker from "@/components/ui/LanguagePicker.vue";
import Avatar from "@/components/ui/Avatar.vue";
import Badge from "@/components/ui/Badge.vue";
import Spinner from "@/components/ui/Spinner.vue";
import Tabs from "@/components/ui/Tabs.vue";
import Icon from "@/components/ui/Icon.vue";

const { t, locale } = useI18n();
const router = useRouter();
const toast = useToast();

const tab = ref("overview");
const overview = ref<AdminOverview | null>(null);
const online = ref<ActiveSession[]>([]);
const users = ref<AdminUserSummary[]>([]);
const feed = ref<ActivityEntry[]>([]);
const feedFilter = ref("");
const loading = ref(true);

const showNew = ref(false);
const email = ref("");
const fullName = ref("");
const newLocale = ref("en");
const saving = ref(false);

const tabs = computed(() => [
  { key: "overview", label: t("admin.tabOverview") },
  { key: "users", label: t("admin.tabUsers") },
  { key: "activity", label: t("admin.tabActivity") },
]);

const dt = new Intl.DateTimeFormat(locale.value as string, { dateStyle: "short", timeStyle: "short" });
const fdt = (s: string | null) => {
  if (!s) return "—";
  try { return dt.format(new Date(s)); } catch { return s; }
};
function fbytes(b: number): string {
  if (!b) return "0 B";
  const u = ["B", "KB", "MB", "GB"];
  const i = Math.min(u.length - 1, Math.floor(Math.log(b) / Math.log(1024)));
  return `${(b / 1024 ** i).toFixed(i ? 1 : 0)} ${u[i]}`;
}
const actionLabel = (a: string) => {
  const k = `actions.${a}`;
  const v = t(k);
  return v === k ? a : v;
};

const statCards = computed(() => {
  const o = overview.value;
  if (!o) return [];
  return [
    { icon: "wifi_tethering", label: t("admin.online"), value: o.online, accent: true },
    { icon: "group", label: t("admin.totalUsers"), value: o.users },
    { icon: "task_alt", label: t("admin.activeUsers"), value: o.active_users },
    { icon: "shield_person", label: t("admin.admins"), value: o.admins },
    { icon: "description", label: t("admin.statFiles"), value: o.files },
    { icon: "folder", label: t("admin.statFolders"), value: o.folders },
    { icon: "history", label: t("admin.statVersions"), value: o.versions },
    { icon: "hard_drive", label: t("admin.storage"), value: fbytes(o.current_bytes) },
    { icon: "ios_share", label: t("admin.shares"), value: o.shares },
    { icon: "login", label: t("admin.logins7d"), value: o.logins_7d },
  ];
});

const actionOptions = computed(() => [
  { value: "", label: t("admin.allActions") },
  ...["login", "logout", "password_set", "user_created", "magic_link_issued", "upload", "edit_save", "share", "delete"].map(
    (a) => ({ value: a, label: actionLabel(a) }),
  ),
]);

async function loadOverview() {
  [overview.value, online.value, feed.value] = await Promise.all([
    admin.overview(),
    admin.sessions(),
    admin.activity({ limit: 8 }),
  ]);
}
async function loadUsers() {
  users.value = await admin.users();
}
async function loadFeed() {
  feed.value = await admin.activity({ action: feedFilter.value || undefined, limit: 200 });
}

onMounted(async () => {
  try {
    await loadOverview();
  } finally {
    loading.value = false;
  }
});

watch(tab, async (v) => {
  if (v === "users" && !users.value.length) await loadUsers();
  if (v === "activity") await loadFeed();
});
watch(feedFilter, () => tab.value === "activity" && loadFeed());

async function create() {
  saving.value = true;
  try {
    await admin.createUser(email.value, fullName.value, newLocale.value);
    showNew.value = false;
    email.value = "";
    fullName.value = "";
    toast.push(t("toast.created"));
    loadUsers();
  } catch {
    toast.push(t("toast.error"), "danger");
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="admin">
    <header class="topbar glass">
      <div class="brand"><span class="logo">P</span><strong>{{ t("admin.title") }}</strong></div>
      <div class="spacer" />
      <a class="exit" href="/"><Icon name="arrow_back" :size="16" />{{ t("app.name") }}</a>
    </header>

    <div class="wrap">
      <Tabs v-model="tab" :tabs="tabs" />

      <div v-if="loading" class="center"><Spinner :size="28" /></div>

      <!-- OVERVIEW -->
      <template v-else-if="tab === 'overview'">
        <div class="stats">
          <div v-for="s in statCards" :key="s.label" class="stat glass" :class="{ accent: s.accent }">
            <Icon :name="s.icon" :size="22" class="sicon" />
            <span class="snum">{{ s.value }}</span>
            <span class="slabel t-faint">{{ s.label }}</span>
          </div>
        </div>

        <div class="cols">
          <section class="panel glass">
            <div class="phead"><Icon name="wifi_tethering" :size="18" /><h2 class="t-h2">{{ t("admin.whoOnline") }}</h2></div>
            <p v-if="!online.length" class="t-faint t-small">{{ t("admin.noOnline") }}</p>
            <div v-for="s in online" :key="s.user_id" class="orow" @click="router.push({ name: 'admin-user', params: { id: s.user_id } })">
              <Avatar :name="s.full_name" :id="s.user_id" :size="32" />
              <div class="ometa"><strong>{{ s.full_name }}</strong><span class="t-faint t-small">{{ t("admin.since", { time: fdt(s.since) }) }}</span></div>
              <span class="dot" />
            </div>
          </section>

          <section class="panel glass">
            <div class="phead"><Icon name="history" :size="18" /><h2 class="t-h2">{{ t("admin.recentActivity") }}</h2></div>
            <div v-for="a in feed" :key="a.id" class="arow">
              <Badge tone="neutral">{{ actionLabel(a.action) }}</Badge>
              <span class="aname">{{ a.actor_name || "—" }}</span>
              <span class="t-faint t-small atime">{{ fdt(a.created_at) }}</span>
            </div>
          </section>
        </div>
      </template>

      <!-- USERS -->
      <template v-else-if="tab === 'users'">
        <div class="usershead">
          <BaseButton variant="primary" @click="showNew = true"><Icon name="person_add" :size="18" />{{ t("admin.newUser") }}</BaseButton>
        </div>
        <div class="list glass">
          <div class="lhead">
            <span>{{ t("common.fullName") }}</span>
            <span class="c-lang">{{ t("common.language") }}</span>
            <span class="c-files">{{ t("admin.statFiles") }}</span>
            <span class="c-pw">{{ t("common.password") }}</span>
            <span class="c-st">{{ t("admin.active") }}</span>
          </div>
          <div v-for="u in users" :key="u.id" class="urow" @click="router.push({ name: 'admin-user', params: { id: u.id } })">
            <div class="cell-name">
              <Avatar :name="u.full_name" :id="u.id" :size="32" />
              <span class="meta"><strong>{{ u.full_name }}</strong><span class="t-faint t-small">{{ u.email }}</span></span>
              <Badge v-if="u.is_admin" tone="owner">admin</Badge>
            </div>
            <div class="c-lang t-muted t-small">{{ u.locale }}</div>
            <div class="c-files t-muted t-small">{{ u.files }} / {{ u.folders }}</div>
            <div class="c-pw"><Badge :tone="u.has_password ? 'success' : 'neutral'">{{ u.has_password ? t("admin.hasPassword") : t("admin.noPassword") }}</Badge></div>
            <div class="c-st"><Badge :tone="u.is_active ? 'success' : 'danger'">{{ u.is_active ? t("admin.active") : t("admin.inactive") }}</Badge></div>
          </div>
        </div>
      </template>

      <!-- ACTIVITY -->
      <template v-else>
        <div class="actbar">
          <BaseSelect v-model="feedFilter" :options="actionOptions" />
        </div>
        <div class="list glass">
          <div class="lhead lh-act">
            <span>{{ t("admin.action") }}</span>
            <span>{{ t("admin.actor") }}</span>
            <span class="c-when">{{ t("admin.when") }}</span>
          </div>
          <p v-if="!feed.length" class="empty t-faint t-small">{{ t("admin.noActivity") }}</p>
          <div v-for="a in feed" :key="a.id" class="actrow">
            <div><Badge tone="neutral">{{ actionLabel(a.action) }}</Badge></div>
            <div class="actor">
              <Avatar v-if="a.actor_id" :name="a.actor_name || '?'" :id="a.actor_id" :size="24" />
              <span class="t-small">{{ a.actor_name || "—" }}</span>
            </div>
            <div class="c-when t-faint t-small">{{ fdt(a.created_at) }}</div>
          </div>
        </div>
      </template>
    </div>

    <BaseModal :open="showNew" :title="t('admin.newUser')" @close="showNew = false">
      <div class="nform">
        <BaseInput v-model="email" :label="t('admin.email')" type="email" icon="mail" />
        <BaseInput v-model="fullName" :label="t('admin.fullName')" icon="person" />
        <LanguagePicker v-model="newLocale" :label="t('admin.language')" />
      </div>
      <template #footer>
        <BaseButton variant="ghost" @click="showNew = false">{{ t("common.cancel") }}</BaseButton>
        <BaseButton variant="primary" :loading="saving" :disabled="!email || !fullName" @click="create">{{ t("admin.createUser") }}</BaseButton>
      </template>
    </BaseModal>
  </div>
</template>

<style scoped>
.admin { min-height: 100%; padding: 6px; display: flex; flex-direction: column; gap: 6px; }
.topbar {
  border-radius: var(--r-lg);
  height: 50px; display: flex; align-items: center; gap: var(--s-3); padding: 0 var(--s-4);
}
.brand { display: flex; align-items: center; gap: var(--s-2); }
.logo { width: 30px; height: 30px; border-radius: var(--r-sm); background: var(--accent-grad); color: #fff; font-weight: 800; display: flex; align-items: center; justify-content: center; }
.spacer { flex: 1; }
.exit { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; color: var(--accent-ink); }
.wrap { flex: 1; min-height: 0; overflow: auto; padding: var(--s-2) var(--s-3); display: flex; flex-direction: column; gap: var(--s-4); max-width: var(--content-max); width: 100%; margin: 0 auto; }
.center { display: flex; justify-content: center; padding: var(--s-8); }

.stats { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: var(--s-3); }
.stat { border-radius: var(--r-lg); padding: var(--s-4); display: flex; flex-direction: column; gap: var(--s-1); }
.stat .sicon { color: var(--ink-3); }
.stat.accent { background: var(--accent-soft) !important; border-color: var(--accent-soft); }
.stat.accent .sicon { color: var(--accent); }
.stat.accent .slabel { color: var(--ink-2); }
.snum { font-size: 24px; font-weight: 700; line-height: 1.1; }
.slabel { font-size: 12px; }

.cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--s-3); }
.panel { border-radius: var(--r-lg); padding: var(--s-4); }
.phead { display: flex; align-items: center; gap: var(--s-2); color: var(--accent-ink); margin-bottom: var(--s-3); }
.phead h2 { color: var(--ink); }
.orow { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; cursor: pointer; border-radius: var(--r-sm); }
.orow:hover { background: rgba(20, 32, 56, 0.04); }
.ometa { display: flex; flex-direction: column; flex: 1; min-width: 0; }
.dot { width: 8px; height: 8px; border-radius: 50%; background: var(--pos); flex: none; }
.arow { display: flex; align-items: center; gap: var(--s-2); padding: var(--s-2) 0; border-bottom: 1px solid var(--line); }
.arow:last-child { border-bottom: none; }
.aname { font-size: 13px; flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.atime { flex: none; }

.usershead { display: flex; justify-content: flex-end; }
.actbar { display: flex; }
.actbar :deep(.field) { width: 220px; }
.list { border-radius: var(--r-lg); overflow: hidden; }
.lhead, .urow { display: grid; grid-template-columns: 1fr 90px 90px 130px 90px; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); }
.lhead { color: var(--ink-3); font-size: 11px; font-weight: 700; text-transform: uppercase; border-bottom: 1px solid var(--line); }
.urow { border-bottom: 1px solid var(--line); cursor: pointer; }
.urow:last-child { border-bottom: none; }
.urow:hover { background: rgba(20, 32, 56, 0.04); }
.cell-name { display: flex; align-items: center; gap: var(--s-3); min-width: 0; }
.meta { display: flex; flex-direction: column; min-width: 0; }
.lh-act, .actrow { grid-template-columns: 200px 1fr 160px; }
.actrow { display: grid; align-items: center; gap: var(--s-3); padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--line); }
.actrow:last-child { border-bottom: none; }
.actor { display: flex; align-items: center; gap: var(--s-2); min-width: 0; }
.empty { padding: var(--s-5); text-align: center; }
.nform { display: flex; flex-direction: column; gap: var(--s-4); }

@media (max-width: 820px) {
  .cols { grid-template-columns: 1fr; }
}
@media (max-width: 720px) {
  .lhead { display: none; }
  .urow { grid-template-columns: 1fr auto; }
  .c-lang, .c-files, .c-pw { display: none; }
  .lh-act, .actrow { grid-template-columns: 1fr auto; }
  .actrow .c-when { display: none; }
}
</style>
