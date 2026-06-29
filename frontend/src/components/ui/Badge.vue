<script setup lang="ts">
defineProps<{ tone?: "owner" | "editor" | "reader" | "neutral" | "success" | "danger" | "warn" }>();
</script>

<template>
  <span class="badge" :class="`t-${tone || 'neutral'}`"><slot /></span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px var(--s-2);
  border-radius: var(--r-full);
  font-size: 11.5px;
  font-weight: 600;
  line-height: 16px;
  white-space: nowrap;
}
.t-owner { background: var(--accent-soft); color: var(--accent-ink); }
.t-editor { background: rgba(31, 138, 91, 0.12); color: var(--pos); }
.t-reader { background: rgba(20, 32, 56, 0.07); color: var(--ink-2); }
.t-neutral { background: rgba(20, 32, 56, 0.07); color: var(--ink-2); }
.t-success { background: rgba(31, 138, 91, 0.12); color: var(--pos); }
.t-danger { background: rgba(210, 63, 63, 0.1); color: var(--neg); }
.t-warn { background: rgba(194, 65, 12, 0.1); color: var(--warn); }
</style>
