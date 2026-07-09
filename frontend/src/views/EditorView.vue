<script setup lang="ts">
import { nextTick, onMounted, ref, watch, onBeforeUnmount } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { editor as editorApi, nodes as nodesApi } from "@/api/client";
import type { EditorSession, NodeItem } from "@/api/types";
import { useAuth } from "@/stores/auth";
import FileIcon from "@/components/ui/FileIcon.vue";
import Badge from "@/components/ui/Badge.vue";
import Spinner from "@/components/ui/Spinner.vue";
import Icon from "@/components/ui/Icon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import Avatar from "@/components/ui/Avatar.vue";
import ShareDrawer from "@/components/ShareDrawer.vue";

// Liquid-Glass editor shell (per the "Collabora Liquid Glass" mockup, rebranded PrivateOffice): a collapsible
// left rail (app nav) + a top bar (document title, sync status, Share) wrapping the embedded editor iframe.
// Green accent (the app's default Liquid Glass tokens). The iframe's own chrome is themed by the editor's
// glass/glass2 CSS via the ?po_design gate.
const props = defineProps<{ id: string }>();
const { t } = useI18n();
const router = useRouter();
const auth = useAuth();

const node = ref<NodeItem | null>(null);
const session = ref<EditorSession | null>(null);
const frame = ref<HTMLIFrameElement | null>(null);
const error = ref(false);
const showShare = ref(false);
const menu = ref(false);
const collapsed = ref(localStorage.getItem("po.editorRail.collapsed") === "1");
watch(collapsed, (v) => localStorage.setItem("po.editorRail.collapsed", v ? "1" : "0"));

const canShare = () => node.value?.my_role === "owner" || (!node.value?.my_role && !!node.value);

onMounted(async () => {
  try {
    [node.value, session.value] = await Promise.all([
      nodesApi.get(props.id),
      editorApi.session(props.id),
    ]);
    await nextTick();
    submitForm();
  } catch {
    error.value = true;
  }
});

// The glass theme gate (data-po) is applied at parse time inside the editor by its own po-toggle.js (driven
// by the ?po_design param the session URL carries), so the theme is correct on first paint.
function submitForm() {
  const s = session.value;
  if (!s || !frame.value) return;
  const form = document.createElement("form");
  form.action = s.iframe_url;
  form.method = "post";
  form.target = "coframe";
  for (const [name, value] of [
    ["access_token", s.access_token],
    ["access_token_ttl", String(s.access_token_ttl)],
  ]) {
    const input = document.createElement("input");
    input.type = "hidden";
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
  document.body.removeChild(form);
}

function go(target: any) { menu.value = false; router.push(target); }
async function logout() { menu.value = false; await auth.logout(); router.push({ name: "login" }); }
function onKey(e: KeyboardEvent) { if (e.key === "Escape") menu.value = false; }
watch(menu, (open) => { open ? document.addEventListener("keydown", onKey) : document.removeEventListener("keydown", onKey); });
onBeforeUnmount(() => document.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="edshell" :class="{ collapsed }">
    <!-- LEFT RAIL -->
    <nav class="edrail">
      <div class="logo" @click="go({ name: 'start' })">P</div>
      <button class="railbtn" :title="t('editor.back')" @click="go({ name: 'files' })">
        <Icon name="folder" :size="22" /><span class="rlabel">{{ t("nav.myFiles") }}</span>
      </button>
      <button class="railbtn" :title="t('nav.home')" @click="go({ name: 'start' })">
        <Icon name="home" :size="22" /><span class="rlabel">{{ t("nav.home") }}</span>
      </button>
      <div class="grow" />
      <button class="railbtn" :title="t('nav.profile')" @click="go({ name: 'profile' })">
        <Icon name="settings" :size="22" /><span class="rlabel">{{ t("nav.profile") }}</span>
      </button>
      <div class="userwrap">
        <button class="userbtn" @click="menu = !menu" :title="auth.user?.full_name">
          <Avatar v-if="auth.user" :name="auth.user.full_name" :id="auth.user.id" :size="34" />
        </button>
        <Transition name="pop">
          <div v-if="menu" class="menu" @click.stop>
            <div class="muser"><strong>{{ auth.user?.full_name }}</strong><span class="t-faint t-small">{{ auth.user?.email }}</span></div>
            <button class="mitem" @click="go({ name: 'profile' })"><Icon name="person" :size="18" />{{ t("nav.profile") }}</button>
            <button class="mitem danger" @click="logout"><Icon name="logout" :size="18" />{{ t("nav.logout") }}</button>
          </div>
        </Transition>
      </div>
    </nav>
    <div v-if="menu" class="scrim" @click="menu = false" />

    <div class="col">
      <!-- TOP BAR -->
      <header class="bar">
        <button class="collapse" :title="t('nav.toggleSidebar')" @click="collapsed = !collapsed"><Icon name="menu" :size="20" /></button>
        <button class="back" @click="go({ name: 'files' })" :title="t('editor.back')"><Icon name="arrow_back" :size="18" /></button>
        <div class="doc">
          <FileIcon v-if="node" :type="node.type" :format="node.co_format" :size="22" />
          <div class="dmeta">
            <span class="nm">{{ node?.name }}</span>
            <span v-if="session" class="sync"><Icon name="cloud_done" :size="14" />{{ t("editor.synced") }}</span>
          </div>
          <Badge v-if="session && !session.can_write" tone="reader">{{ t("editor.readonly") }}</Badge>
        </div>
        <div class="spacer" />
        <a v-if="node?.type === 'file'" class="tbicon" :href="'/api/nodes/' + node.id + '/download'" :title="t('common.download')"><Icon name="download" :size="20" /></a>
        <div v-if="auth.user" class="collab"><Avatar :name="auth.user.full_name" :id="auth.user.id" :size="30" /></div>
        <BaseButton v-if="canShare()" size="sm" variant="primary" @click="showShare = true">
          <Icon name="group_add" :size="18" />{{ t("common.share") }}
        </BaseButton>
      </header>

      <!-- STAGE -->
      <div class="stage">
        <div v-if="!session && !error" class="center"><Spinner :size="28" /><span class="t-muted">{{ t("editor.loading") }}</span></div>
        <div v-else-if="error" class="center err">
          <Icon name="error" :size="34" /><span class="t-muted">{{ t("editor.failed") }}</span>
          <BaseButton variant="primary" @click="go({ name: 'files' })">{{ t("editor.back") }}</BaseButton>
        </div>
        <iframe ref="frame" name="coframe" class="coframe" :class="{ ready: !!session }" allow="clipboard-read; clipboard-write" title="PrivateOffice editor" />
      </div>
    </div>

    <ShareDrawer :open="showShare" :node="node" @close="showShare = false" />
  </div>
</template>

<style scoped>
.edshell {
  height: 100%; display: flex; padding: 6px; gap: 6px; min-height: 0;
  background:
    radial-gradient(46vw 46vw at 12% -10%, rgba(160, 226, 197, 0.42), transparent 68%),
    radial-gradient(40vw 40vw at 98% 112%, rgba(191, 240, 223, 0.40), transparent 70%),
    linear-gradient(158deg, #e8f4ee 0%, #eef3f0 55%, #eaf6f1 100%);
}

/* ---- left rail (green, collapsible) ---- */
.edrail {
  flex: 0 0 var(--rail-w); border-radius: var(--r-lg);
  background: rgba(255, 255, 255, 0.6); -webkit-backdrop-filter: blur(var(--glass-blur)); backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-bd);
  display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 6px;
  position: relative; z-index: 50; transition: flex-basis 0.18s ease, opacity 0.14s ease;
}
.edshell.collapsed .edrail { flex-basis: 0; padding: 0; border-width: 0; opacity: 0; overflow: hidden; }
.logo { width: 38px; height: 38px; border-radius: var(--r-md); background: var(--accent-grad); color: #fff; font-weight: 800; font-size: 16px; display: flex; align-items: center; justify-content: center; cursor: pointer; box-shadow: 0 4px 12px rgba(10, 127, 94, 0.34); margin-bottom: 6px; flex: none; }
.railbtn { width: 100%; min-height: 48px; padding: 6px 2px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px; border: none; background: transparent; border-radius: var(--r-md); cursor: pointer; color: var(--ink-2); flex: none; }
.railbtn:hover { background: var(--accent-soft); color: var(--accent-ink); }
.rlabel { font-size: 9.5px; font-weight: 600; text-align: center; line-height: 1.15; }
.grow { flex: 1; }
.userwrap { position: relative; flex: none; }
.userbtn { border: none; background: transparent; padding: 2px; cursor: pointer; border-radius: var(--r-full); display: flex; }
.menu { position: absolute; inset-inline-start: calc(100% + 8px); bottom: 0; min-width: 210px; background: rgba(255,255,255,0.92); -webkit-backdrop-filter: blur(16px); backdrop-filter: blur(16px); border: 1px solid var(--glass-bd); border-radius: var(--r-lg); box-shadow: var(--shadow-2); padding: var(--s-2); display: flex; flex-direction: column; gap: 2px; z-index: 60; }
.muser { padding: var(--s-2) var(--s-3) var(--s-3); display: flex; flex-direction: column; gap: 2px; border-bottom: 1px solid var(--line); margin-bottom: var(--s-1); }
.mitem { display: flex; align-items: center; gap: var(--s-2); text-align: start; border: none; background: transparent; padding: var(--s-2) var(--s-3); border-radius: var(--r-sm); font-size: 13.5px; cursor: pointer; color: var(--ink); }
.mitem:hover { background: var(--accent-soft); color: var(--accent-ink); }
.mitem.danger { color: var(--neg); }
.scrim { position: fixed; inset: 0; z-index: 40; }

/* ---- column ---- */
.col { flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 6px; }

/* ---- top bar ---- */
.bar {
  flex: 0 0 auto; height: 56px; display: flex; align-items: center; gap: var(--s-2); padding: 0 var(--s-3);
  border-radius: var(--r-lg);
  background: rgba(255, 255, 255, 0.6); -webkit-backdrop-filter: blur(var(--glass-blur)); backdrop-filter: blur(var(--glass-blur));
  border: 1px solid var(--glass-bd);
}
.collapse, .back { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); flex: none; }
.collapse:hover, .back:hover { background: var(--accent-soft); color: var(--accent-ink); }
.doc { display: flex; align-items: center; gap: var(--s-2); min-width: 0; }
.dmeta { display: flex; flex-direction: column; gap: 0; min-width: 0; }
.nm { font-weight: 700; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sync { display: flex; align-items: center; gap: 3px; font-size: 11.5px; color: var(--accent); font-weight: 600; }
.spacer { flex: 1; }
.tbicon { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 36px; height: 36px; border-radius: var(--r-full); display: flex; align-items: center; justify-content: center; text-decoration: none; }
.tbicon:hover { background: var(--accent-soft); color: var(--accent-ink); }
.collab { display: flex; margin-inline: var(--s-1) var(--s-2); }

/* ---- stage / iframe ---- */
.stage { flex: 1; min-height: 0; position: relative; border-radius: var(--r-lg); overflow: hidden; border: 1px solid var(--glass-bd); background: rgba(255, 255, 255, 0.4); }
.center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-3); }
.center.err { color: var(--neg); }
.coframe { width: 100%; height: 100%; border: none; opacity: 0; transition: opacity 0.25s ease; }
.coframe.ready { opacity: 1; }

@media (max-width: 720px) {
  .edshell { flex-direction: column; padding: 4px; gap: 4px; }
  .edrail { flex: 0 0 auto; min-height: 52px; flex-direction: row; width: 100%; justify-content: space-around; }
  .edshell.collapsed .edrail { display: none; }
  .logo { display: none; }
  .grow { display: none; }
  .rlabel { display: none; }
  .menu { inset-inline-start: auto; inset-inline-end: 0; bottom: calc(100% + 8px); }
}
</style>
