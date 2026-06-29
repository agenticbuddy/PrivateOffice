<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { editor as editorApi, nodes as nodesApi } from "@/api/client";
import type { EditorSession, NodeItem } from "@/api/types";
import FileIcon from "@/components/ui/FileIcon.vue";
import Badge from "@/components/ui/Badge.vue";
import Spinner from "@/components/ui/Spinner.vue";
import Icon from "@/components/ui/Icon.vue";
import BaseButton from "@/components/ui/BaseButton.vue";

const props = defineProps<{ id: string }>();
const { t } = useI18n();
const router = useRouter();

const node = ref<NodeItem | null>(null);
const session = ref<EditorSession | null>(null);
const frame = ref<HTMLIFrameElement | null>(null);
const error = ref(false);

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

// The glass theme gate (data-po) is applied at parse time inside the editor by its own
// po-toggle.js (driven by the ?po_design param the session URL carries), so the theme is
// correct on first paint — the parent does not patch the editor DOM at runtime.

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
</script>

<template>
  <div class="editor">
    <header class="bar glass">
      <button class="back" @click="router.push({ name: 'files' })">
        <Icon name="arrow_back" :size="18" /><span>{{ t("editor.back") }}</span>
      </button>
      <div class="sep" />
      <div class="doc">
        <FileIcon v-if="node" :type="node.type" :format="node.co_format" :size="20" />
        <span class="nm">{{ node?.name }}</span>
        <Badge v-if="session && !session.can_write" tone="reader">{{ t("editor.readonly") }}</Badge>
      </div>
      <div class="spacer" />
    </header>

    <div class="stage glass">
      <div v-if="!session && !error" class="center">
        <Spinner :size="28" /><span class="t-muted">{{ t("editor.loading") }}</span>
      </div>
      <div v-else-if="error" class="center err">
        <Icon name="error" :size="34" />
        <span class="t-muted">{{ t("editor.failed") }}</span>
        <BaseButton variant="primary" @click="router.push({ name: 'files' })">
          {{ t("editor.back") }}
        </BaseButton>
      </div>
      <iframe
        ref="frame"
        name="coframe"
        class="coframe"
        :class="{ ready: !!session }"
        allow="clipboard-read; clipboard-write"
        title="PrivateOffice editor"
      />
    </div>
  </div>
</template>

<style scoped>
.editor { height: 100%; display: flex; flex-direction: column; padding: 6px; gap: 6px; }
.bar {
  flex: 0 0 auto;
  display: flex; align-items: center; gap: var(--s-3);
  height: 46px; padding: 0 var(--s-3);
  border-radius: var(--r-lg);
}
.back {
  display: inline-flex; align-items: center; gap: var(--s-1);
  border: none; background: transparent; cursor: pointer; color: var(--ink-2);
  font-weight: 600; font-size: 13px; padding: var(--s-2); border-radius: var(--r-sm);
}
.back:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.sep { width: 1px; height: 22px; background: var(--line); }
.doc { display: flex; align-items: center; gap: var(--s-2); min-width: 0; }
.nm { font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.spacer { flex: 1; }
.stage { flex: 1; position: relative; min-height: 0; border-radius: var(--r-lg); overflow: hidden; background: var(--canvas); }
.center { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: var(--s-3); }
.coframe { width: 100%; height: 100%; border: 0; opacity: 0; transition: opacity 0.3s ease; }
.coframe.ready { opacity: 1; }
</style>
