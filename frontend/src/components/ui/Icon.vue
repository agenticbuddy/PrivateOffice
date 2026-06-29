<script setup lang="ts">
// Material Symbols Rounded icon. Usage: <Icon name="search" :size="20" />
defineProps<{ name: string; size?: number; fill?: boolean; color?: string }>();
</script>

<template>
  <span
    class="ms"
    :class="{ fill }"
    :style="{ fontSize: `${size || 20}px`, color }"
    aria-hidden="true"
  >{{ name }}</span>
</template>
