<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { directory, shares } from "@/api/client";
import type { DirectoryUser, NodeItem, Role, ShareItem } from "@/api/types";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";
import BaseDrawer from "./ui/BaseDrawer.vue";
import BaseSelect from "./ui/BaseSelect.vue";
import Avatar from "./ui/Avatar.vue";
import Badge from "./ui/Badge.vue";

const props = defineProps<{ open: boolean; node: NodeItem | null }>();
const emit = defineEmits<{ (e: "close"): void }>();

const { t } = useI18n();
const auth = useAuth();
const toast = useToast();

const list = ref<ShareItem[]>([]);
const people = ref<DirectoryUser[]>([]);
const query = ref("");

const canManage = computed(() => props.node?.my_role === "owner");
const roleOptions = computed(() => [
  { value: "owner", label: t("roles.owner") },
  { value: "editor", label: t("roles.editor") },
  { value: "reader", label: t("roles.reader") },
]);

const candidates = computed(() => {
  const taken = new Set(list.value.map((s) => s.user_id));
  const q = query.value.toLowerCase();
  return people.value
    .filter((u) => u.id !== auth.user?.id && !taken.has(u.id))
    .filter((u) => !q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q))
    .slice(0, 6);
});

async function load() {
  if (!props.node) return;
  [list.value, people.value] = await Promise.all([
    shares.list(props.node.id),
    directory.users(),
  ]);
}

watch(() => props.open, (o) => o && load());

async function add(u: DirectoryUser) {
  if (!props.node) return;
  await shares.upsert(props.node.id, u.id, "reader");
  query.value = "";
  toast.push(t("toast.shared"));
  await load();
}
async function changeRole(s: ShareItem, role: Role) {
  if (!props.node) return;
  await shares.upsert(props.node.id, s.user_id, role);
  toast.push(t("toast.shared"));
  await load();
}
async function remove(s: ShareItem) {
  if (!props.node) return;
  await shares.remove(props.node.id, s.user_id);
  toast.push(t("toast.shared"));
  await load();
}
</script>

<template>
  <BaseDrawer :open="open" :title="t('share.title', { name: node?.name })" @close="emit('close')">
    <div v-if="canManage" class="add">
      <label class="t-caption t-muted">{{ t("share.addPeople") }}</label>
      <input v-model="query" class="search" :placeholder="t('share.searchUser')" />
      <div v-if="query && candidates.length" class="results">
        <button v-for="u in candidates" :key="u.id" class="result" @click="add(u)">
          <Avatar :name="u.full_name" :id="u.id" :size="28" />
          <span class="meta"><strong>{{ u.full_name }}</strong><span class="t-faint t-small">{{ u.email }}</span></span>
        </button>
      </div>
    </div>

    <div class="current">
      <label class="t-caption t-muted">{{ t("share.current") }}</label>
      <p v-if="!list.length" class="t-faint t-small">{{ t("share.noShares") }}</p>
      <div v-for="s in list" :key="s.user_id" class="row">
        <Avatar :name="s.full_name" :id="s.user_id" :size="32" />
        <span class="meta"><strong>{{ s.full_name }}</strong><span class="t-faint t-small">{{ s.email }}</span></span>
        <div class="ctrl">
          <BaseSelect
            v-if="canManage"
            :model-value="s.role"
            :options="roleOptions"
            @update:model-value="(r) => changeRole(s, r as Role)"
          />
          <Badge v-else :tone="s.role">{{ t(`roles.${s.role}`) }}</Badge>
          <button v-if="canManage" class="rm" :title="t('share.removeAccess')" @click="remove(s)">✕</button>
        </div>
      </div>
    </div>
  </BaseDrawer>
</template>

<style scoped>
.add { display: flex; flex-direction: column; gap: var(--s-2); margin-bottom: var(--s-5); }
.search {
  height: 40px; padding: 0 var(--s-3);
  border: 1px solid var(--line); border-radius: var(--r-md);
  background: var(--surface); color: var(--text); font-size: 14px;
}
.results { display: flex; flex-direction: column; gap: 2px; margin-top: var(--s-1); }
.result, .row { display: flex; align-items: center; gap: var(--s-3); }
.result { border: none; background: transparent; padding: var(--s-2); border-radius: var(--r-md); cursor: pointer; text-align: start; }
.result:hover { background: var(--surface-2); }
.meta { display: flex; flex-direction: column; line-height: 1.2; flex: 1; min-width: 0; }
.meta strong { font-size: 14px; }
.current { display: flex; flex-direction: column; gap: var(--s-3); }
.row { padding: var(--s-1) 0; }
.ctrl { display: flex; align-items: center; gap: var(--s-2); }
.ctrl :deep(.field) { width: 130px; }
.rm { border: none; background: transparent; color: var(--text-faint); cursor: pointer; font-size: 14px; }
.rm:hover { color: var(--danger); }
</style>
