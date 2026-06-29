<script setup lang="ts">
defineProps<{
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md";
  block?: boolean;
  loading?: boolean;
  disabled?: boolean;
  type?: "button" | "submit";
}>();
</script>

<template>
  <button
    :type="type || 'button'"
    class="btn"
    :class="[`v-${variant || 'secondary'}`, `s-${size || 'md'}`, { block, loading }]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="spin" aria-hidden="true" />
    <slot />
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--s-2);
  border: 1px solid transparent;
  border-radius: var(--r-md);
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.13s ease, border-color 0.13s ease, color 0.13s ease,
    filter 0.13s ease, transform 0.13s ease;
}
.s-md { height: 38px; padding: 0 var(--s-4); font-size: 13px; }
.s-sm { height: 32px; padding: 0 var(--s-3); font-size: 12.5px; }
.block { width: 100%; }
.btn:disabled { opacity: 0.55; cursor: not-allowed; }

.v-primary {
  background: var(--accent-grad);
  color: #fff;
  box-shadow: 0 4px 13px rgba(10, 127, 94, 0.3);
}
.v-primary:hover:not(:disabled) { filter: brightness(1.06); transform: translateY(-1px); }

.v-secondary {
  background: var(--glass-fill);
  color: var(--ink);
  border-color: var(--line);
}
.v-secondary:hover:not(:disabled) { background: rgba(255, 255, 255, 0.75); }

.v-ghost { background: transparent; color: var(--ink-2); }
.v-ghost:hover:not(:disabled) { background: rgba(20, 32, 56, 0.06); color: var(--ink); }

.v-danger { background: var(--neg); color: #fff; box-shadow: 0 4px 13px rgba(210, 63, 63, 0.28); }
.v-danger:hover:not(:disabled) { filter: brightness(1.04); }

.spin {
  width: 14px; height: 14px;
  border: 2px solid currentColor; border-top-color: transparent;
  border-radius: 50%; animation: r 0.7s linear infinite;
}
@keyframes r { to { transform: rotate(360deg); } }
</style>
