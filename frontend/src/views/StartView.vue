<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { nodes as nodesApi } from "@/api/client";
import type { NodeItem } from "@/api/types";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";
import AppShell from "@/components/AppShell.vue";
import Icon from "@/components/ui/Icon.vue";
import FileIcon from "@/components/ui/FileIcon.vue";
import Spinner from "@/components/ui/Spinner.vue";
import EmptyState from "@/components/ui/EmptyState.vue";

const { t, locale } = useI18n();
const router = useRouter();
const auth = useAuth();
const toast = useToast();

const recent = ref<NodeItem[]>([]);
const results = ref<NodeItem[]>([]);
const query = ref("");
const loading = ref(true);
const searching = ref(false);
let searchTimer: number | undefined;

const firstName = computed(() => (auth.user?.full_name || "").split(/\s+/)[0] || "");
const fmt = new Intl.DateTimeFormat(locale.value as string, { dateStyle: "medium" });
const fdate = (s: string) => {
  try { return fmt.format(new Date(s)); } catch { return s; }
};

const cards = computed(() => [
  { format: "docx", icon: "description", color: "var(--doc)", title: t("create.formatDocx") },
  { format: "xlsx", icon: "table_chart", color: "var(--sheet)", title: t("create.formatXlsx") },
  { format: "pptx", icon: "co_present", color: "var(--slide)", title: t("create.formatPptx") },
]);

onMounted(async () => {
  try {
    recent.value = await nodesApi.recent(12);
  } finally {
    loading.value = false;
  }
});

watch(query, (q) => {
  window.clearTimeout(searchTimer);
  if (!q.trim()) {
    results.value = [];
    return;
  }
  searching.value = true;
  searchTimer = window.setTimeout(async () => {
    try {
      results.value = await nodesApi.search(q.trim());
    } finally {
      searching.value = false;
    }
  }, 250);
});

async function createDoc(format: string) {
  const node = await nodesApi.createFile("Untitled", format, null);
  toast.push(t("toast.created"));
  router.push({ name: "editor", params: { id: node.id } });
}
function open(n: NodeItem) {
  router.push({ name: "editor", params: { id: n.id } });
}
const showSearch = computed(() => query.value.trim().length > 0);
</script>

<template>
  <AppShell>
    <div class="page">
      <header class="head glass">
        <div class="hello">
          <h1 class="t-display">{{ t("start.greeting", { name: firstName }) }}</h1>
        </div>
        <div class="search">
          <Icon name="search" :size="20" class="sicon" />
          <input v-model="query" class="sinput" :placeholder="t('start.search')" />
          <Spinner v-if="searching" :size="16" />
        </div>
      </header>

      <!-- SEARCH RESULTS -->
      <section v-if="showSearch" class="block">
        <h2 class="t-h2 sechead">{{ t("common.search") }}</h2>
        <EmptyState v-if="!searching && !results.length" :title="t('start.noResults')" icon="search_off" />
        <div v-else class="grid">
          <button v-for="n in results" :key="n.id" class="filecard glass" @click="open(n)">
            <div class="thumb" :data-kind="n.co_format"><FileIcon :type="n.type" :format="n.co_format" :size="26" /></div>
            <div class="finfo">
              <div class="fname">{{ n.name }}</div>
              <div class="fmeta t-faint">{{ fdate(n.updated_at) }}</div>
            </div>
          </button>
        </div>
      </section>

      <template v-else>
        <!-- CREATE CARDS -->
        <section class="block">
          <h2 class="t-h2 sechead">{{ t("start.startSomething") }}</h2>
          <div class="cards">
            <button v-for="c in cards" :key="c.format" class="card glass" @click="createDoc(c.format)">
              <span class="cicon" :style="{ color: c.color }"><Icon :name="c.icon" :size="30" /></span>
              <span class="ctitle">{{ c.title }}</span>
            </button>
          </div>
        </section>

        <!-- RECENT -->
        <section class="block">
          <div class="sechead-row">
            <h2 class="t-h2">{{ t("start.recent") }}</h2>
            <button class="seeall" @click="router.push({ name: 'files' })">
              {{ t("start.openMyFiles") }}<Icon name="chevron_right" :size="16" />
            </button>
          </div>
          <div v-if="loading" class="center"><Spinner :size="26" /></div>
          <EmptyState
            v-else-if="!recent.length"
            :title="t('files.empty')"
            :hint="t('files.emptyHint')"
            icon="draft"
          />
          <div v-else class="grid">
            <button v-for="n in recent" :key="n.id" class="filecard glass" @click="open(n)">
              <div class="thumb" :data-kind="n.co_format"><FileIcon :type="n.type" :format="n.co_format" :size="26" /></div>
              <div class="finfo">
                <div class="fname">{{ n.name }}</div>
                <div class="fmeta t-faint">{{ fdate(n.updated_at) }}</div>
              </div>
            </button>
          </div>
        </section>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.page { flex: 1; min-height: 0; overflow: auto; display: flex; flex-direction: column; gap: 6px; }
.head {
  border-radius: var(--r-lg);
  padding: var(--s-5);
  display: flex; align-items: center; justify-content: space-between; gap: var(--s-4); flex-wrap: wrap;
}
.search {
  display: flex; align-items: center; gap: var(--s-2);
  height: 40px; padding: 0 var(--s-3); min-width: 260px; flex: 1; max-width: 420px;
  border: 1px solid var(--line); border-radius: var(--r-md); background: rgba(255, 255, 255, 0.6);
}
.search:focus-within { border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-soft); background: #fff; }
.sicon { color: var(--ink-3); }
.sinput { flex: 1; min-width: 0; border: none; background: transparent; outline: none; font-size: 14px; color: var(--ink); }

.block { padding: 0 var(--s-2); }
.sechead { margin-bottom: var(--s-3); }
.sechead-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--s-3); }
.seeall { display: inline-flex; align-items: center; gap: 2px; border: none; background: transparent; cursor: pointer; color: var(--accent-ink); font-weight: 600; font-size: 13px; }

.cards { display: flex; gap: var(--s-3); flex-wrap: wrap; }
.card {
  display: flex; flex-direction: column; gap: var(--s-3);
  width: 190px; padding: var(--s-4); border-radius: var(--r-lg); cursor: pointer; text-align: start;
  transition: transform 0.13s ease;
}
.card:hover { transform: translateY(-2px); }
.ctitle { font-weight: 700; font-size: 14px; }

.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: var(--s-3); }
.filecard { border-radius: var(--r-lg); overflow: hidden; cursor: pointer; padding: 0; text-align: start; transition: transform 0.13s ease; }
.filecard:hover { transform: translateY(-2px); }
.thumb {
  height: 96px; display: flex; align-items: center; justify-content: center;
  background: repeating-linear-gradient(135deg, rgba(255,255,255,0.5), rgba(255,255,255,0.5) 9px, rgba(20,32,56,0.03) 9px, rgba(20,32,56,0.03) 18px);
}
.finfo { padding: var(--s-3); display: flex; flex-direction: column; gap: 2px; }
.fname { font-size: 13px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fmeta { font-size: 11.5px; }
.center { display: flex; justify-content: center; padding: var(--s-6); }
</style>
