<script setup lang="ts">
defineProps<{ tabs: { key: string; label: string }[]; modelValue: string }>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();
</script>

<template>
  <div class="tabs" role="tablist">
    <button
      v-for="t in tabs"
      :key="t.key"
      class="tab"
      :class="{ active: t.key === modelValue }"
      role="tab"
      :aria-selected="t.key === modelValue"
      @click="$emit('update:modelValue', t.key)"
    >
      {{ t.label }}
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: var(--s-1);
  border-bottom: 1px solid var(--line);
  overflow-x: auto;
}
.tab {
  flex: 0 0 auto;
  border: none;
  background: transparent;
  padding: var(--s-2) var(--s-3) var(--s-3);
  font-size: 13.5px;
  font-weight: 500;
  color: var(--ink-2);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
  border-radius: var(--r-sm) var(--r-sm) 0 0;
  white-space: nowrap;
}
.tab.active { color: var(--ink); font-weight: 700; border-bottom-color: var(--accent); }
.tab:hover:not(.active) { color: var(--ink); background: rgba(20, 32, 56, 0.04); }
</style>
