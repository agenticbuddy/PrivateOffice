<script setup lang="ts">
import { computed, ref, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { nodes as nodesApi } from "@/api/client";
import type { CreatableFormat, NodeItem } from "@/api/types";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";
import AppShell from "@/components/AppShell.vue";
import ShareDrawer from "@/components/ShareDrawer.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseModal from "@/components/ui/BaseModal.vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseSelect from "@/components/ui/BaseSelect.vue";
import FileIcon from "@/components/ui/FileIcon.vue";
import Avatar from "@/components/ui/Avatar.vue";
import Badge from "@/components/ui/Badge.vue";
import EmptyState from "@/components/ui/EmptyState.vue";
import Spinner from "@/components/ui/Spinner.vue";
import Icon from "@/components/ui/Icon.vue";

const props = defineProps<{ id?: string; shared?: boolean }>();
const { t, locale } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuth();
const toast = useToast();

const items = ref<NodeItem[]>([]);
const loading = ref(true);
const current = ref<NodeItem | null>(null);
const formats = ref<CreatableFormat[]>([]);
const sharedCount = ref(0);

const showFolder = ref(false);
const showDoc = ref(false);
const folderName = ref("");
const docName = ref("");
const docFormat = ref("docx");
const shareNode = ref<NodeItem | null>(null);
const deleteNode = ref<NodeItem | null>(null);
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const view = ref<"list" | "grid">((localStorage.getItem("po.files.view") as any) || "list");
watch(view, (v) => localStorage.setItem("po.files.view", v));
const azLetter = ref("");
const sortDir = ref<"asc" | "desc">("asc");
const lib = ref<"all" | "mine" | "starred">("all"); // library filter within the root list
const selected = ref<Set<string>>(new Set());
const starred = ref<Set<string>>(new Set(JSON.parse(localStorage.getItem("po.starred") || "[]")));
function toggleStar(id: string) {
  starred.value.has(id) ? starred.value.delete(id) : starred.value.add(id);
  starred.value = new Set(starred.value);
  localStorage.setItem("po.starred", JSON.stringify([...starred.value]));
}

const mode = computed(() => (props.shared ? "shared" : props.id ? "folder" : "root"));
const parentId = computed(() => props.id ?? null);
const title = computed(() => {
  if (mode.value === "shared") return t("files.sharedTitle");
  if (mode.value === "folder") return current.value?.name ?? "…";
  if (lib.value === "mine") return t("files.myFilesLib");
  if (lib.value === "starred") return t("files.starred");
  return t("files.title");
});
const canCreate = computed(() => {
  if (mode.value === "shared") return false;
  if (mode.value === "root") return true;
  return current.value?.my_role === "owner" || current.value?.my_role === "editor";
});
const isMine = (n: NodeItem) => n.created_by === auth.user?.id;

// counts for the sidebar LIBRARY
const allCount = computed(() => (mode.value === "shared" ? 0 : items.value.length));
const myCount = computed(() => items.value.filter(isMine).length);
const starCount = computed(() => items.value.filter((n) => starred.value.has(n.id)).length);

// RECENT: most-recently-updated files
const recent = computed(() =>
  [...items.value].filter((n) => n.type === "file").sort((a, b) => b.updated_at.localeCompare(a.updated_at)).slice(0, 6),
);
const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

// displayed = base list → library filter → A-Z → sort
const displayed = computed(() => {
  let out = items.value;
  if (mode.value === "root") {
    if (lib.value === "mine") out = out.filter(isMine);
    else if (lib.value === "starred") out = out.filter((n) => starred.value.has(n.id));
  }
  if (azLetter.value) out = out.filter((n) => (n.name[0] || "").toUpperCase() === azLetter.value);
  return [...out].sort((a, b) => {
    // folders first, then by name in the chosen direction
    if ((a.type === "folder") !== (b.type === "folder")) return a.type === "folder" ? -1 : 1;
    const c = a.name.localeCompare(b.name, locale.value as string);
    return sortDir.value === "asc" ? c : -c;
  });
});
const allChecked = computed(() => displayed.value.length > 0 && displayed.value.every((n) => selected.value.has(n.id)));
function toggleAll() {
  if (allChecked.value) displayed.value.forEach((n) => selected.value.delete(n.id));
  else displayed.value.forEach((n) => selected.value.add(n.id));
  selected.value = new Set(selected.value);
}
function toggleSel(id: string) {
  selected.value.has(id) ? selected.value.delete(id) : selected.value.add(id);
  selected.value = new Set(selected.value);
}

const fmt = new Intl.DateTimeFormat(locale.value as string, { dateStyle: "medium" });
function fdate(s: string) { try { return fmt.format(new Date(s)); } catch { return s; } }
function ftype(n: NodeItem) { return n.type === "folder" ? t("files.typeFolder") : (n.co_format || "").toUpperCase() || t("files.typeFile"); }
function fsize(n: NodeItem) {
  if (n.type === "folder" || n.size == null) return "—";
  const u = ["B", "KB", "MB", "GB"]; let s = n.size, i = 0;
  while (s >= 1024 && i < u.length - 1) { s /= 1024; i++; }
  return `${s < 10 && i > 0 ? s.toFixed(1) : Math.round(s)} ${u[i]}`;
}

async function load() {
  loading.value = true;
  selected.value = new Set();
  try {
    if (mode.value === "shared") {
      items.value = await nodesApi.sharedWithMe();
      current.value = null;
    } else {
      if (mode.value === "folder" && props.id) current.value = await nodesApi.get(props.id);
      else current.value = null;
      items.value = await nodesApi.list(parentId.value);
    }
    if (!formats.value.length) formats.value = (await nodesApi.formats()).creatable;
  } finally {
    loading.value = false;
  }
}
watch(() => [props.id, props.shared, route.fullPath], load, { immediate: true });
onMounted(async () => { try { sharedCount.value = (await nodesApi.sharedWithMe()).length; } catch { /* ignore */ } });

function goLib(l: "all" | "mine" | "starred") {
  lib.value = l; azLetter.value = "";
  if (mode.value !== "root") router.push({ name: "files" });
}
function openNode(n: NodeItem) {
  if (n.type === "folder") router.push({ name: "folder", params: { id: n.id } });
  else router.push({ name: "editor", params: { id: n.id } });
}
async function createFolder() { await nodesApi.createFolder(folderName.value, parentId.value); showFolder.value = false; folderName.value = ""; toast.push(t("toast.created")); load(); }
async function createDoc() { await nodesApi.createFile(docName.value || "Untitled", docFormat.value, parentId.value); showDoc.value = false; docName.value = ""; toast.push(t("toast.created")); load(); }
async function onFiles(files: FileList | null) {
  if (!files?.length) return;
  for (const f of Array.from(files)) {
    try { await nodesApi.upload(f, parentId.value); toast.push(t("toast.uploaded")); }
    catch { toast.push(t("toast.unsupported"), "danger"); }
  }
  load();
}
function onDrop(e: DragEvent) { dragOver.value = false; if (canCreate.value) onFiles(e.dataTransfer?.files ?? null); }
function download(n: NodeItem) { const a = document.createElement("a"); a.href = nodesApi.downloadUrl(n.id); a.download = n.name; document.body.appendChild(a); a.click(); a.remove(); }
async function doDelete() { if (!deleteNode.value) return; await nodesApi.remove(deleteNode.value.id); deleteNode.value = null; toast.push(t("toast.deleted")); load(); }

const formatOptions = computed(() => formats.value.map((f) => ({ value: f.format, label: t(`create.format${f.format[0].toUpperCase()}${f.format.slice(1)}`) })));
</script>

<template>
  <AppShell>
    <!-- SIDEBAR -->
    <template #sidebar>
      <div class="sbcol">
        <BaseButton class="createbtn" variant="primary" block :disabled="!canCreate" @click="showDoc = true">
          <Icon name="add" :size="18" />{{ t("files.createNew") }}<Icon name="expand_more" :size="16" class="cchev" />
        </BaseButton>

        <div class="sec-label">{{ t("files.library") }}</div>
        <button class="navrow" :class="{ active: mode !== 'shared' && lib === 'all' }" @click="goLib('all')">
          <Icon name="folder" :size="18" /><span>{{ t("files.allDocuments") }}</span><em>{{ allCount }}</em>
        </button>
        <button class="navrow" :class="{ active: mode === 'root' && lib === 'mine' }" @click="goLib('mine')">
          <Icon name="person" :size="18" /><span>{{ t("files.myFilesLib") }}</span><em>{{ myCount }}</em>
        </button>
        <button class="navrow" :class="{ active: mode === 'shared' }" @click="router.push({ name: 'shared' })">
          <Icon name="group" :size="18" /><span>{{ t("nav.sharedWithMe") }}</span><em>{{ sharedCount }}</em>
        </button>
        <button class="navrow" :class="{ active: mode === 'root' && lib === 'starred' }" @click="goLib('starred')">
          <Icon name="star" :size="18" /><span>{{ t("files.starred") }}</span><em>{{ starCount }}</em>
        </button>

        <div class="sec-label">{{ t("files.recent") }}</div>
        <button v-for="n in recent" :key="n.id" class="navrow recent" @click="openNode(n)" :title="n.name">
          <FileIcon :type="n.type" :format="n.co_format" :size="16" /><span class="rname">{{ n.name }}</span>
        </button>
        <div v-if="!recent.length" class="norecent t-faint t-small">{{ t("files.noRecent") }}</div>

        <div class="grow" />
        <button class="recyclebtn" @click="toast.push(t('files.noTrash'))"><Icon name="delete" :size="18" />{{ t("files.recycleBin") }}</button>
      </div>
    </template>

    <!-- MAIN -->
    <div class="page" :class="{ drag: dragOver }" @dragover.prevent="dragOver = canCreate" @dragleave="dragOver = false" @drop.prevent="onDrop">
      <div class="toolbar">
        <div class="crumbs">
          <button v-if="mode === 'folder'" class="iconbtn" @click="router.back()" :aria-label="t('editor.back')"><Icon name="arrow_back" :size="18" /></button>
          <h1 class="ttl">{{ title }}</h1>
        </div>
        <div class="tspacer" />
        <template v-if="selected.size">
          <span class="selinfo">{{ t("files.selectedOf", { n: selected.size, m: displayed.length }) }}</span>
          <BaseButton size="sm" variant="ghost" @click="selected = new Set()"><Icon name="close" :size="18" />{{ t("common.cancel") }}</BaseButton>
        </template>
        <template v-else-if="canCreate">
          <BaseButton size="sm" variant="ghost" @click="showFolder = true"><Icon name="create_new_folder" :size="18" />{{ t("files.newFolder") }}</BaseButton>
          <BaseButton size="sm" variant="ghost" @click="fileInput?.click()"><Icon name="upload" :size="18" />{{ t("files.uploadFile") }}</BaseButton>
          <BaseButton size="sm" variant="primary" @click="showDoc = true"><Icon name="add" :size="18" />{{ t("files.newDocument") }}</BaseButton>
          <input ref="fileInput" type="file" hidden multiple @change="onFiles(($event.target as HTMLInputElement).files)" />
        </template>
        <div class="viewtoggle">
          <button :class="{ on: view === 'list' }" :title="t('files.viewList')" @click="view = 'list'"><Icon name="list" :size="18" /></button>
          <button :class="{ on: view === 'grid' }" :title="t('files.viewGrid')" @click="view = 'grid'"><Icon name="grid_view" :size="18" /></button>
        </div>
      </div>

      <div class="azbar">
        <button class="az" :class="{ on: azLetter === '' }" @click="azLetter = ''">{{ t("files.azAll") }}</button>
        <button v-for="l in alphabet" :key="l" class="az" :class="{ on: azLetter === l }" @click="azLetter = azLetter === l ? '' : l">{{ l }}</button>
      </div>

      <div class="body">
        <div v-if="loading" class="center"><Spinner :size="26" /></div>
        <EmptyState v-else-if="!displayed.length" :title="mode === 'shared' ? t('files.emptyShared') : t('files.empty')" :hint="mode === 'shared' ? undefined : t('files.emptyHint')" :icon="mode === 'shared' ? 'group' : 'folder_open'">
          <BaseButton v-if="canCreate" variant="primary" @click="showDoc = true"><Icon name="add" :size="18" />{{ t("files.newDocument") }}</BaseButton>
        </EmptyState>

        <!-- LIST -->
        <div v-else-if="view === 'list'" class="list">
          <div class="lhead">
            <label class="chk"><input type="checkbox" :checked="allChecked" @change="toggleAll" /></label>
            <button class="sortname" @click="sortDir = sortDir === 'asc' ? 'desc' : 'asc'">{{ t("files.colName") }}<Icon :name="sortDir === 'asc' ? 'arrow_upward' : 'arrow_downward'" :size="14" /></button>
            <span class="col-type">{{ t("files.colType") }}</span>
            <span class="col-owner">{{ t("files.colOwner") }}</span>
            <span class="col-mod">{{ t("files.colModified") }}</span>
            <span class="col-size">{{ t("files.colSize") }}</span>
            <span class="col-share">{{ t("files.colSharing") }}</span>
            <span class="col-star" />
            <span class="col-act" />
          </div>
          <div v-for="n in displayed" :key="n.id" class="rowitem" :class="{ sel: selected.has(n.id) }" @click="openNode(n)">
            <label class="chk" @click.stop><input type="checkbox" :checked="selected.has(n.id)" @change="toggleSel(n.id)" /></label>
            <div class="cell-name">
              <FileIcon :type="n.type" :format="n.co_format" :size="22" />
              <span class="nm">{{ n.name }}</span>
            </div>
            <div class="col-type t-muted t-small">{{ ftype(n) }}</div>
            <div class="col-owner cell-owner"><Avatar :name="isMine(n) ? (auth.user?.full_name || '') : '•'" :id="n.created_by" :size="24" /></div>
            <div class="col-mod t-muted t-small">{{ fdate(n.updated_at) }}</div>
            <div class="col-size t-muted t-small">{{ fsize(n) }}</div>
            <div class="col-share">
              <Badge v-if="n.my_role && n.my_role !== 'owner'" :tone="n.my_role">{{ t(`roles.${n.my_role}`) }}</Badge>
              <span v-else class="t-faint t-small">{{ t("files.private") }}</span>
            </div>
            <div class="col-star" @click.stop>
              <button class="starbtn" :class="{ on: starred.has(n.id) }" :title="t('files.starred')" @click="toggleStar(n.id)"><Icon name="star" :size="18" :fill="starred.has(n.id)" /></button>
            </div>
            <div class="col-act acts" @click.stop>
              <button v-if="n.type === 'file'" :title="t('common.download')" @click="download(n)"><Icon name="download" :size="18" /></button>
              <button :title="t('common.share')" @click="shareNode = n"><Icon name="group_add" :size="18" /></button>
              <button v-if="n.my_role === 'owner'" class="del" :title="t('common.delete')" @click="deleteNode = n"><Icon name="delete" :size="18" /></button>
            </div>
          </div>
        </div>

        <!-- GRID -->
        <div v-else class="grid">
          <div v-for="n in displayed" :key="n.id" class="card" :class="{ sel: selected.has(n.id) }" @click="openNode(n)">
            <button class="starbtn cardstar" :class="{ on: starred.has(n.id) }" @click.stop="toggleStar(n.id)"><Icon name="star" :size="16" :fill="starred.has(n.id)" /></button>
            <div class="cicon"><FileIcon :type="n.type" :format="n.co_format" :size="34" /></div>
            <div class="cname">{{ n.name }}</div>
            <div class="cmeta t-faint t-small">{{ ftype(n) }} · {{ fsize(n) }}</div>
            <div class="cacts" @click.stop>
              <button :title="t('common.share')" @click="shareNode = n"><Icon name="group_add" :size="16" /></button>
              <button v-if="n.my_role === 'owner'" class="del" :title="t('common.delete')" @click="deleteNode = n"><Icon name="delete" :size="16" /></button>
            </div>
          </div>
        </div>
      </div>

      <footer class="statusbar">
        <span v-if="selected.size">{{ t("files.selectedOf", { n: selected.size, m: displayed.length }) }}</span>
        <span v-else class="t-faint">{{ t("files.itemsCount", { m: displayed.length }) }}</span>
      </footer>

      <div v-if="dragOver" class="dropmask"><Icon name="cloud_upload" :size="36" /><span>{{ t("files.dropHere") }}</span></div>
    </div>

    <BaseModal :open="showFolder" :title="t('create.folderTitle')" @close="showFolder = false">
      <BaseInput v-model="folderName" :label="t('create.folderName')" icon="folder" @keyup.enter="createFolder" />
      <template #footer><BaseButton variant="ghost" @click="showFolder = false">{{ t("common.cancel") }}</BaseButton><BaseButton variant="primary" :disabled="!folderName" @click="createFolder">{{ t("common.create") }}</BaseButton></template>
    </BaseModal>
    <BaseModal :open="showDoc" :title="t('create.docTitle')" @close="showDoc = false">
      <div class="dform"><BaseInput v-model="docName" :label="t('create.docName')" icon="description" /><BaseSelect v-model="docFormat" :label="t('create.format')" :options="formatOptions" /></div>
      <template #footer><BaseButton variant="ghost" @click="showDoc = false">{{ t("common.cancel") }}</BaseButton><BaseButton variant="primary" :disabled="!docName" @click="createDoc">{{ t("common.create") }}</BaseButton></template>
    </BaseModal>
    <BaseModal :open="!!deleteNode" :title="t('confirm.deleteTitle', { name: deleteNode?.name })" @close="deleteNode = null">
      <p class="t-muted">{{ t(deleteNode?.type === "folder" ? "confirm.deleteBodyFolder" : "confirm.deleteBodyFile") }}</p>
      <template #footer><BaseButton variant="ghost" @click="deleteNode = null">{{ t("common.cancel") }}</BaseButton><BaseButton variant="danger" @click="doDelete">{{ t("confirm.deleteConfirm") }}</BaseButton></template>
    </BaseModal>
    <ShareDrawer :open="!!shareNode" :node="shareNode" @close="shareNode = null" />
  </AppShell>
</template>

<style scoped>
/* ---- sidebar ---- */
.sbcol { display: flex; flex-direction: column; min-height: 100%; }
.createbtn { margin-bottom: var(--s-3); }
.cchev { margin-inline-start: auto; }
.sec-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--ink-3); padding: var(--s-3) var(--s-2) var(--s-1); }
.navrow { width: 100%; display: flex; align-items: center; gap: var(--s-2); padding: var(--s-2); border: none; background: transparent; border-radius: var(--r-md); cursor: pointer; color: var(--ink); font-size: 14px; font-weight: 500; text-align: start; }
.navrow span { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.navrow em { font-style: normal; color: var(--ink-3); font-size: 12.5px; font-weight: 600; }
.navrow:hover { background: rgba(37, 99, 217, 0.08); }
.navrow.active { background: var(--accent-soft); color: var(--accent-ink); font-weight: 700; }
.navrow.active em { color: var(--accent-ink); }
.navrow.recent { color: var(--accent-ink); }
.norecent { padding: var(--s-2); }
.grow { flex: 1; min-height: var(--s-4); }
.recyclebtn { margin-top: var(--s-3); width: 100%; display: flex; align-items: center; justify-content: center; gap: var(--s-2); padding: var(--s-2); border: 1px solid var(--line); background: rgba(255,255,255,0.5); border-radius: var(--r-md); cursor: pointer; color: var(--ink-2); font-size: 13px; font-weight: 600; }
.recyclebtn:hover { border-color: var(--accent); color: var(--accent-ink); }

/* ---- main ---- */
.page { flex: 1; min-height: 0; display: flex; flex-direction: column; position: relative; }
.toolbar { flex: 0 0 auto; display: flex; align-items: center; gap: var(--s-2); padding: var(--s-3) var(--s-4); border-bottom: 1px solid var(--line); }
.crumbs { display: flex; align-items: center; gap: var(--s-2); }
.ttl { font-size: 20px; font-weight: 700; color: var(--ink); }
.iconbtn { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.iconbtn:hover { background: rgba(20, 32, 56, 0.06); }
.tspacer { flex: 1; }
.selinfo { font-size: 13px; font-weight: 600; color: var(--accent-ink); }
.viewtoggle { display: flex; gap: 2px; margin-inline-start: var(--s-2); background: rgba(20, 32, 56, 0.05); border-radius: var(--r-md); padding: 2px; }
.viewtoggle button { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 32px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.viewtoggle button.on { background: #fff; color: var(--accent-ink); box-shadow: var(--shadow-1); }

.azbar { flex: 0 0 auto; display: flex; flex-wrap: wrap; gap: 2px; padding: var(--s-2) var(--s-4); border-bottom: 1px solid var(--line); }
.az { border: none; background: transparent; cursor: pointer; color: var(--ink-3); min-width: 22px; height: 24px; border-radius: var(--r-sm); font-size: 12px; font-weight: 600; }
.az:hover { background: rgba(37, 99, 217, 0.08); color: var(--accent-ink); }
.az.on { background: var(--accent); color: #fff; }

.body { flex: 1; min-height: 0; overflow: auto; }
.center { display: flex; justify-content: center; padding: var(--s-8); }

/* list */
.list { display: flex; flex-direction: column; }
.lhead, .rowitem { display: grid; grid-template-columns: 34px 1fr 96px 96px 130px 84px 96px 40px 108px; align-items: center; gap: var(--s-2); padding: var(--s-2) var(--s-4); }
.lhead { color: var(--ink-3); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--line); position: sticky; top: 0; background: rgba(255, 255, 255, 0.75); backdrop-filter: blur(8px); z-index: 1; }
.chk { display: flex; align-items: center; justify-content: center; }
.chk input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
.sortname { border: none; background: transparent; cursor: pointer; color: var(--ink-3); font: inherit; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; display: flex; align-items: center; gap: 2px; padding: 0; }
.sortname:hover { color: var(--accent-ink); }
.rowitem { border-bottom: 1px solid var(--line); cursor: pointer; }
.rowitem:last-child { border-bottom: none; }
.rowitem:hover { background: rgba(37, 99, 217, 0.05); }
.rowitem.sel { background: var(--accent-soft); }
.cell-name { display: flex; align-items: center; gap: var(--s-3); min-width: 0; }
.nm { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.starbtn { border: none; background: transparent; cursor: pointer; color: var(--ink-3); width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.starbtn:hover { background: rgba(217, 154, 10, 0.12); color: var(--folder); }
.starbtn.on { color: var(--folder); }
.acts { display: flex; gap: 2px; justify-content: flex-end; }
.acts button { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.acts button:hover { background: rgba(37, 99, 217, 0.1); color: var(--accent-ink); }
.acts .del:hover { background: rgba(210, 63, 63, 0.1); color: var(--neg); }

/* grid */
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(168px, 1fr)); gap: var(--s-3); padding: var(--s-4); }
.card { position: relative; display: flex; flex-direction: column; align-items: center; gap: var(--s-2); padding: var(--s-4) var(--s-3); border: 1px solid var(--line); border-radius: var(--r-lg); background: rgba(255, 255, 255, 0.5); cursor: pointer; text-align: center; }
.card:hover { border-color: var(--accent); box-shadow: var(--shadow-1); }
.card.sel { border-color: var(--accent); background: var(--accent-soft); }
.cardstar { position: absolute; top: 6px; inset-inline-start: 6px; }
.cicon { width: 56px; height: 56px; display: flex; align-items: center; justify-content: center; }
.cname { font-weight: 600; font-size: 13.5px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.cmeta { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.cacts { position: absolute; top: 6px; inset-inline-end: 6px; display: flex; gap: 2px; opacity: 0; transition: opacity 0.12s; }
.card:hover .cacts { opacity: 1; }
.cacts button { border: none; background: rgba(255, 255, 255, 0.85); cursor: pointer; color: var(--ink-2); width: 26px; height: 26px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.cacts .del:hover { color: var(--neg); }

.statusbar { flex: 0 0 auto; height: 34px; display: flex; align-items: center; padding: 0 var(--s-4); border-top: 1px solid var(--line); font-size: 12.5px; color: var(--ink-2); }
.dform { display: flex; flex-direction: column; gap: var(--s-4); }
.dropmask { position: absolute; inset: 0; border: 2px dashed var(--accent); border-radius: var(--r-xl); background: var(--accent-soft); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-2); font-weight: 700; color: var(--accent-ink); pointer-events: none; }

@media (max-width: 900px) {
  .lhead, .rowitem { grid-template-columns: 34px 1fr 40px 108px; }
  .col-type, .col-owner, .col-mod, .col-size, .col-share { display: none; }
  .azbar { display: none; }
}
</style>
