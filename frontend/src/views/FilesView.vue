<script setup lang="ts">
import { computed, ref, watch } from "vue";
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

const showFolder = ref(false);
const showDoc = ref(false);
const folderName = ref("");
const docName = ref("");
const docFormat = ref("docx");
const shareNode = ref<NodeItem | null>(null);
const deleteNode = ref<NodeItem | null>(null);
const dragOver = ref(false);
const fileInput = ref<HTMLInputElement | null>(null);

const mode = computed(() => (props.shared ? "shared" : props.id ? "folder" : "root"));
const parentId = computed(() => props.id ?? null);
const title = computed(() => {
  if (mode.value === "shared") return t("files.sharedTitle");
  if (mode.value === "folder") return current.value?.name ?? "…";
  return t("files.title");
});
const canCreate = computed(() => {
  if (mode.value === "shared") return false;
  if (mode.value === "root") return true;
  return current.value?.my_role === "owner" || current.value?.my_role === "editor";
});

const fmt = new Intl.DateTimeFormat(locale.value as string, { dateStyle: "medium" });
function fdate(s: string) {
  try { return fmt.format(new Date(s)); } catch { return s; }
}

async function load() {
  loading.value = true;
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

function openNode(n: NodeItem) {
  if (n.type === "folder") router.push({ name: "folder", params: { id: n.id } });
  else router.push({ name: "editor", params: { id: n.id } });
}
async function createFolder() {
  await nodesApi.createFolder(folderName.value, parentId.value);
  showFolder.value = false;
  folderName.value = "";
  toast.push(t("toast.created"));
  load();
}
async function createDoc() {
  await nodesApi.createFile(docName.value || "Untitled", docFormat.value, parentId.value);
  showDoc.value = false;
  docName.value = "";
  toast.push(t("toast.created"));
  load();
}
async function onFiles(files: FileList | null) {
  if (!files?.length) return;
  for (const f of Array.from(files)) {
    try {
      await nodesApi.upload(f, parentId.value);
      toast.push(t("toast.uploaded"));
    } catch {
      toast.push(t("toast.unsupported"), "danger");
    }
  }
  load();
}
function onDrop(e: DragEvent) {
  dragOver.value = false;
  if (canCreate.value) onFiles(e.dataTransfer?.files ?? null);
}
function download(n: NodeItem) {
  const a = document.createElement("a");
  a.href = nodesApi.downloadUrl(n.id);
  a.download = n.name;
  document.body.appendChild(a);
  a.click();
  a.remove();
}
async function doDelete() {
  if (!deleteNode.value) return;
  await nodesApi.remove(deleteNode.value.id);
  deleteNode.value = null;
  toast.push(t("toast.deleted"));
  load();
}

const formatOptions = computed(() =>
  formats.value.map((f) => ({
    value: f.format,
    label: t(`create.format${f.format[0].toUpperCase()}${f.format.slice(1)}`),
  })),
);
</script>

<template>
  <AppShell>
    <div
      class="page"
      :class="{ drag: dragOver }"
      @dragover.prevent="dragOver = canCreate"
      @dragleave="dragOver = false"
      @drop.prevent="onDrop"
    >
      <header class="head glass">
        <div class="title">
          <button v-if="mode === 'folder'" class="back" @click="router.back()" aria-label="Back">
            <Icon name="arrow_back" :size="20" />
          </button>
          <h1 class="t-display">{{ title }}</h1>
        </div>
        <div v-if="canCreate" class="actions">
          <BaseButton size="sm" @click="showFolder = true"><Icon name="create_new_folder" :size="18" />{{ t("files.newFolder") }}</BaseButton>
          <BaseButton size="sm" @click="fileInput?.click()"><Icon name="upload" :size="18" />{{ t("files.uploadFile") }}</BaseButton>
          <BaseButton size="sm" variant="primary" @click="showDoc = true"><Icon name="add" :size="18" />{{ t("files.newDocument") }}</BaseButton>
          <input ref="fileInput" type="file" hidden multiple @change="onFiles(($event.target as HTMLInputElement).files)" />
        </div>
      </header>

      <div class="body glass">
        <div v-if="loading" class="center"><Spinner :size="26" /></div>

        <EmptyState
          v-else-if="!items.length"
          :title="mode === 'shared' ? t('files.emptyShared') : t('files.empty')"
          :hint="mode === 'shared' ? undefined : t('files.emptyHint')"
          :icon="mode === 'shared' ? 'group' : 'folder_open'"
        >
          <BaseButton v-if="canCreate" variant="primary" @click="showDoc = true">
            <Icon name="add" :size="18" />{{ t("files.newDocument") }}
          </BaseButton>
        </EmptyState>

        <div v-else class="list">
          <div class="lhead">
            <span>{{ t("files.colName") }}</span>
            <span class="col-owner">{{ t("files.colOwner") }}</span>
            <span class="col-mod">{{ t("files.colModified") }}</span>
            <span class="col-act" />
          </div>
          <div v-for="n in items" :key="n.id" class="rowitem" @click="openNode(n)">
            <div class="cell-name">
              <FileIcon :type="n.type" :format="n.co_format" :size="22" />
              <span class="nm">{{ n.name }}</span>
              <Badge v-if="n.my_role && n.my_role !== 'owner'" :tone="n.my_role">{{ t(`roles.${n.my_role}`) }}</Badge>
            </div>
            <div class="col-owner cell-owner">
              <Avatar :name="n.created_by === auth.user?.id ? (auth.user?.full_name || '') : '•'" :id="n.created_by" :size="24" />
            </div>
            <div class="col-mod t-muted t-small">{{ fdate(n.updated_at) }}</div>
            <div class="col-act acts" @click.stop>
              <button v-if="n.type === 'file'" :title="t('common.download')" @click="download(n)"><Icon name="download" :size="18" /></button>
              <button :title="t('common.share')" @click="shareNode = n"><Icon name="group_add" :size="18" /></button>
              <button v-if="n.my_role === 'owner'" class="del" :title="t('common.delete')" @click="deleteNode = n"><Icon name="delete" :size="18" /></button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="dragOver" class="dropmask">
        <Icon name="cloud_upload" :size="36" /><span>{{ t("files.dropHere") }}</span>
      </div>
    </div>

    <BaseModal :open="showFolder" :title="t('create.folderTitle')" @close="showFolder = false">
      <BaseInput v-model="folderName" :label="t('create.folderName')" icon="folder" @keyup.enter="createFolder" />
      <template #footer>
        <BaseButton variant="ghost" @click="showFolder = false">{{ t("common.cancel") }}</BaseButton>
        <BaseButton variant="primary" :disabled="!folderName" @click="createFolder">{{ t("common.create") }}</BaseButton>
      </template>
    </BaseModal>

    <BaseModal :open="showDoc" :title="t('create.docTitle')" @close="showDoc = false">
      <div class="dform">
        <BaseInput v-model="docName" :label="t('create.docName')" icon="description" />
        <BaseSelect v-model="docFormat" :label="t('create.format')" :options="formatOptions" />
      </div>
      <template #footer>
        <BaseButton variant="ghost" @click="showDoc = false">{{ t("common.cancel") }}</BaseButton>
        <BaseButton variant="primary" :disabled="!docName" @click="createDoc">{{ t("common.create") }}</BaseButton>
      </template>
    </BaseModal>

    <BaseModal :open="!!deleteNode" :title="t('confirm.deleteTitle', { name: deleteNode?.name })" @close="deleteNode = null">
      <p class="t-muted">{{ t(deleteNode?.type === "folder" ? "confirm.deleteBodyFolder" : "confirm.deleteBodyFile") }}</p>
      <template #footer>
        <BaseButton variant="ghost" @click="deleteNode = null">{{ t("common.cancel") }}</BaseButton>
        <BaseButton variant="danger" @click="doDelete">{{ t("confirm.deleteConfirm") }}</BaseButton>
      </template>
    </BaseModal>

    <ShareDrawer :open="!!shareNode" :node="shareNode" @close="shareNode = null" />
  </AppShell>
</template>

<style scoped>
.page { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 6px; position: relative; }
.head {
  flex: 0 0 auto;
  border-radius: var(--r-lg);
  padding: var(--s-4) var(--s-5);
  display: flex; align-items: center; justify-content: space-between; gap: var(--s-4); flex-wrap: wrap;
}
.title { display: flex; align-items: center; gap: var(--s-2); }
.back {
  border: none; background: transparent; cursor: pointer; color: var(--ink-2);
  width: 34px; height: 34px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm);
}
.back:hover { background: rgba(20, 32, 56, 0.06); }
.actions { display: flex; gap: var(--s-2); flex-wrap: wrap; }

.body { flex: 1; min-height: 0; border-radius: var(--r-lg); overflow: auto; }
.center { display: flex; justify-content: center; padding: var(--s-8); }

.list { display: flex; flex-direction: column; }
.lhead, .rowitem {
  display: grid;
  grid-template-columns: 1fr 120px 140px 116px;
  align-items: center;
  gap: var(--s-3);
  padding: var(--s-3) var(--s-5);
}
.lhead { color: var(--ink-3); font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; border-bottom: 1px solid var(--line); position: sticky; top: 0; background: rgba(255,255,255,0.5); backdrop-filter: blur(8px); z-index: 1; }
[data-design="classic"] .lhead { background: #fff; }
.rowitem { border-bottom: 1px solid var(--line); cursor: pointer; }
.rowitem:last-child { border-bottom: none; }
.rowitem:hover { background: rgba(20, 32, 56, 0.04); }
.cell-name { display: flex; align-items: center; gap: var(--s-3); min-width: 0; }
.nm { font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.acts { display: flex; gap: 2px; justify-content: flex-end; }
.acts button { border: none; background: transparent; cursor: pointer; color: var(--ink-2); width: 30px; height: 30px; display: flex; align-items: center; justify-content: center; border-radius: var(--r-sm); }
.acts button:hover { background: rgba(20, 32, 56, 0.08); color: var(--ink); }
.acts .del:hover { background: rgba(210, 63, 63, 0.1); color: var(--neg); }
.dform { display: flex; flex-direction: column; gap: var(--s-4); }
.dropmask {
  position: absolute; inset: 0;
  border: 2px dashed var(--accent);
  border-radius: var(--r-lg);
  background: var(--accent-soft);
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-2);
  font-weight: 700; color: var(--accent-ink); pointer-events: none;
}

@media (max-width: 720px) {
  .lhead { display: none; }
  .rowitem { grid-template-columns: 1fr auto; grid-template-areas: "name acts" "meta acts"; row-gap: 2px; }
  .cell-name { grid-area: name; }
  .col-owner { display: none; }
  .col-mod { grid-area: meta; }
  .acts { grid-area: acts; }
}
</style>
