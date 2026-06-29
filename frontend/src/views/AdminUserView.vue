<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useI18n } from "vue-i18n";
import { admin } from "@/api/client";
import type { AdminUserDetail, AuditEntry, NodeItem } from "@/api/types";
import { useToast } from "@/stores/toast";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import LanguagePicker from "@/components/ui/LanguagePicker.vue";
import Avatar from "@/components/ui/Avatar.vue";
import Badge from "@/components/ui/Badge.vue";
import Tabs from "@/components/ui/Tabs.vue";
import FileIcon from "@/components/ui/FileIcon.vue";
import Icon from "@/components/ui/Icon.vue";

const props = defineProps<{ id: string }>();
const { t, locale } = useI18n();
const toast = useToast();

const user = ref<AdminUserDetail | null>(null);
const tab = ref("bio");
const fullName = ref("");
const bio = ref("");
const userLocale = ref("en");
const active = ref(true);
const password = ref("");
const magicUrl = ref("");
const userNodes = ref<NodeItem[]>([]);
const audit = ref<AuditEntry[]>([]);

const dt = new Intl.DateTimeFormat(locale.value as string, { dateStyle: "short", timeStyle: "short" });
const fdt = (s: string) => { try { return dt.format(new Date(s)); } catch { return s; } };
const actionLabel = (a: string) => { const k = `actions.${a}`; const v = t(k); return v === k ? a : v; };

async function load() {
  user.value = await admin.user(props.id);
  fullName.value = user.value.full_name;
  bio.value = user.value.bio ?? "";
  userLocale.value = user.value.locale;
  active.value = user.value.is_active;
}
onMounted(async () => {
  await load();
  userNodes.value = await admin.userNodes(props.id);
  audit.value = await admin.audit(props.id);
});

async function saveBio() {
  await admin.patchUser(props.id, { full_name: fullName.value, bio: bio.value, locale: userLocale.value, is_active: active.value });
  toast.push(t("profile.saved"));
  load();
}
async function genLink() {
  magicUrl.value = (await admin.magicLink(props.id)).url;
}
async function copyLink() {
  await navigator.clipboard.writeText(magicUrl.value);
  toast.push(t("admin.linkCopied"));
}
async function setPw() {
  if (!password.value) return;
  try {
    await admin.setPassword(props.id, password.value);
    password.value = "";
    toast.push(t("profile.saved"));
    load();
  } catch {
    toast.push(t("toast.error"), "danger");
  }
}
function downloadNode(n: NodeItem) {
  const a = document.createElement("a");
  a.href = admin.downloadNodeUrl(n.id);
  a.download = n.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
async function delNode(n: NodeItem) {
  await admin.deleteNode(props.id, n.id);
  toast.push(t("toast.deleted"));
  userNodes.value = await admin.userNodes(props.id);
  load();
}
</script>

<template>
  <div class="admin">
    <header class="topbar glass">
      <a class="back" href="/admin"><Icon name="arrow_back" :size="16" />{{ t("admin.users") }}</a>
      <div class="spacer" />
      <a class="exit" href="/"><Icon name="home" :size="16" />{{ t("app.name") }}</a>
    </header>

    <div class="wrap" v-if="user">
      <header class="head glass">
        <Avatar :name="user.full_name" :id="user.id" :size="56" />
        <div class="hmeta">
          <h1 class="t-display">{{ user.full_name }}</h1>
          <p class="t-muted">{{ user.email }}</p>
        </div>
        <Badge v-if="user.is_admin" tone="owner">admin</Badge>
        <Badge :tone="user.is_active ? 'success' : 'danger'">{{ user.is_active ? t("admin.active") : t("admin.inactive") }}</Badge>
      </header>

      <Tabs v-model="tab" :tabs="[{ key: 'bio', label: t('admin.tabBio') }, { key: 'stats', label: t('admin.tabStats') }, { key: 'history', label: t('admin.tabHistory') }]" />

      <!-- BIO -->
      <section v-if="tab === 'bio'" class="pane">
        <div class="card glass">
          <BaseInput v-model="fullName" :label="t('admin.fullName')" icon="person" />
          <label class="field">
            <span class="lbl">{{ t("admin.bio") }}</span>
            <textarea v-model="bio" class="ta" rows="3" />
          </label>
          <LanguagePicker v-model="userLocale" :label="t('admin.language')" />
          <label class="check"><input type="checkbox" v-model="active" /> {{ t("admin.active") }}</label>
          <div><BaseButton variant="primary" @click="saveBio"><Icon name="save" :size="18" />{{ t("common.save") }}</BaseButton></div>
        </div>

        <div class="card glass">
          <div class="cardhead"><Icon name="link" :size="18" /><h2 class="t-h2">{{ t("admin.magicLink") }}</h2></div>
          <div class="row-actions">
            <BaseButton size="sm" @click="genLink"><Icon name="bolt" :size="16" />{{ t("admin.generateLink") }}</BaseButton>
            <input v-if="magicUrl" :value="magicUrl" readonly class="linkbox" />
            <BaseButton v-if="magicUrl" size="sm" @click="copyLink"><Icon name="content_copy" :size="16" />{{ t("admin.copyLink") }}</BaseButton>
          </div>
        </div>

        <div class="card glass">
          <div class="cardhead"><Icon name="lock" :size="18" /><h2 class="t-h2">{{ t("admin.setPassword") }}</h2></div>
          <div class="row-actions">
            <BaseInput v-model="password" type="password" icon="key" />
            <BaseButton variant="primary" :disabled="!password" @click="setPw">{{ t("common.save") }}</BaseButton>
          </div>
        </div>
      </section>

      <!-- STATS -->
      <section v-else-if="tab === 'stats'" class="pane">
        <div class="stats">
          <div class="stat glass"><span class="num">{{ user.stats.files }}</span><span class="t-muted t-small">{{ t("admin.statFiles") }}</span></div>
          <div class="stat glass"><span class="num">{{ user.stats.folders }}</span><span class="t-muted t-small">{{ t("admin.statFolders") }}</span></div>
          <div class="stat glass"><span class="num">{{ user.stats.shared_out }}</span><span class="t-muted t-small">{{ t("admin.statShared") }}</span></div>
          <div class="stat glass"><span class="num">{{ user.stats.versions }}</span><span class="t-muted t-small">{{ t("admin.statVersions") }}</span></div>
        </div>
        <div class="card glass">
          <div class="cardhead"><Icon name="folder" :size="18" /><h2 class="t-h2">{{ t("admin.nodes") }}</h2></div>
          <p v-if="!userNodes.length" class="t-faint t-small">{{ t("admin.noNodes") }}</p>
          <div v-for="n in userNodes" :key="n.id" class="node">
            <FileIcon :type="n.type" :format="n.co_format" :size="20" />
            <span class="nm">{{ n.name }}</span>
            <div class="spacer" />
            <button v-if="n.type === 'file'" class="iconbtn" :title="t('admin.viewFile')" @click="downloadNode(n)"><Icon name="download" :size="18" /></button>
            <button class="iconbtn del" :title="t('admin.deleteNode')" @click="delNode(n)"><Icon name="delete" :size="18" /></button>
          </div>
        </div>
      </section>

      <!-- HISTORY -->
      <section v-else class="pane">
        <div class="card glass">
          <p v-if="!audit.length" class="t-faint t-small">{{ t("admin.noHistory") }}</p>
          <div v-for="(a, i) in audit" :key="i" class="hrow">
            <Badge tone="neutral">{{ actionLabel(a.action) }}</Badge>
            <span class="t-muted t-small htime">{{ fdt(a.created_at) }}</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.admin { min-height: 100%; padding: 6px; display: flex; flex-direction: column; gap: 6px; }
.topbar { border-radius: var(--r-lg); height: 50px; display: flex; align-items: center; padding: 0 var(--s-4); }
.back, .exit { display: inline-flex; align-items: center; gap: 4px; font-weight: 600; color: var(--accent-ink); }
.spacer { flex: 1; }
.wrap { flex: 1; min-height: 0; overflow: auto; padding: var(--s-2) var(--s-3); display: flex; flex-direction: column; gap: var(--s-4); max-width: 800px; width: 100%; margin: 0 auto; }
.head { border-radius: var(--r-lg); padding: var(--s-4) var(--s-5); display: flex; align-items: center; gap: var(--s-3); }
.hmeta { flex: 1; min-width: 0; }
.pane { display: flex; flex-direction: column; gap: var(--s-3); }
.card { border-radius: var(--r-lg); padding: var(--s-5); display: flex; flex-direction: column; gap: var(--s-3); }
.cardhead { display: flex; align-items: center; gap: var(--s-2); color: var(--accent-ink); }
.cardhead h2 { color: var(--ink); }
.field { display: flex; flex-direction: column; gap: var(--s-2); }
.lbl { font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.ta { border: 1px solid var(--line); border-radius: var(--r-md); padding: var(--s-3); font-family: inherit; font-size: 13.5px; resize: vertical; background: rgba(255,255,255,0.6); color: var(--ink); }
.ta:focus { outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); }
.check { display: flex; align-items: center; gap: var(--s-2); font-size: 13.5px; }
.row-actions { display: flex; gap: var(--s-3); align-items: flex-end; flex-wrap: wrap; }
.row-actions :deep(.field) { flex: 1; }
.linkbox { flex: 1; min-width: 200px; height: 36px; border: 1px solid var(--line); border-radius: var(--r-md); padding: 0 var(--s-3); font-size: 12px; background: rgba(20,32,56,0.04); color: var(--ink-2); }
.stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: var(--s-3); }
.stat { border-radius: var(--r-lg); padding: var(--s-4); display: flex; flex-direction: column; gap: var(--s-1); align-items: center; }
.num { font-size: 26px; font-weight: 700; }
.node { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; border-bottom: 1px solid var(--line); }
.node:last-child { border-bottom: none; }
.nm { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.iconbtn { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.iconbtn:hover { background: rgba(20, 32, 56, 0.08); color: var(--ink); }
.iconbtn.del:hover { background: rgba(210, 63, 63, 0.1); color: var(--neg); }
.hrow { display: flex; align-items: center; gap: var(--s-3); padding: var(--s-2) 0; border-bottom: 1px solid var(--line); }
.hrow:last-child { border-bottom: none; }
.htime { margin-inline-start: auto; }
@media (max-width: 560px) { .stats { grid-template-columns: repeat(2, 1fr); } }
</style>
