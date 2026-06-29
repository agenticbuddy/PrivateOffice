<script setup lang="ts">
import Icon from "./Icon.vue";

defineProps<{ title: string; hint?: string; icon?: string }>();
</script>

<template>
  <div class="empty">
    <div class="art glass" aria-hidden="true">
      <Icon :name="icon || 'folder_open'" :size="34" />
    </div>
    <h3 class="t-h2">{{ title }}</h3>
    <p v-if="hint" class="t-muted t-small">{{ hint }}</p>
    <div class="cta"><slot /></div>
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--s-3);
  text-align: center;
  padding: var(--s-8) var(--s-4);
  color: var(--ink);
}
.art {
  width: 72px; height: 72px;
  border-radius: var(--r-xl);
  display: flex; align-items: center; justify-content: center;
  color: var(--accent);
  margin-bottom: var(--s-1);
}
.cta { margin-top: var(--s-2); }
</style>
