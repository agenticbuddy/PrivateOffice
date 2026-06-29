<script setup lang="ts">
defineProps<{ size?: number }>();
</script>

<template>
  <span class="sp" :style="{ width: `${size || 22}px`, height: `${size || 22}px` }" />
</template>

<style scoped>
.sp {
  display: inline-block;
  border: 2.5px solid var(--accent-soft);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: r 0.7s linear infinite;
}
@keyframes r { to { transform: rotate(360deg); } }
</style>
