<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ name: string; id?: string; size?: number }>();

const PALETTE = [
  "#4c6fff", "#1fb57a", "#f5a623", "#e5484d", "#7c5cfc",
  "#0aa2c0", "#d6409f", "#e8590c", "#2f9e44", "#1098ad",
];

const initials = computed(() => {
  const parts = props.name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "?";
});

const color = computed(() => {
  const seed = props.id ?? props.name;
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
});

const px = computed(() => `${props.size ?? 32}px`);
const font = computed(() => `${Math.round((props.size ?? 32) * 0.4)}px`);
</script>

<template>
  <span
    class="avatar"
    :style="{ width: px, height: px, background: color, fontSize: font }"
    :title="name"
  >{{ initials }}</span>
</template>

<style scoped>
.avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--r-full);
  color: #fff;
  font-weight: 600;
  flex: none;
  user-select: none;
}
</style>
