<script setup lang="ts">
import { useToast } from "@/stores/toast";
import Icon from "./Icon.vue";

const toast = useToast();
const iconFor = (tone: string) =>
  tone === "danger" ? "error" : tone === "neutral" ? "info" : "check_circle";
</script>

<template>
  <Teleport to="body">
    <div class="host" aria-live="polite">
      <TransitionGroup name="t">
        <div v-for="t in toast.items" :key="t.id" class="toast glass" :class="`tone-${t.tone}`">
          <Icon :name="iconFor(t.tone)" :size="18" class="ic" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.host {
  position: fixed;
  top: var(--s-4);
  inset-inline-end: var(--s-4);
  display: flex;
  flex-direction: column;
  gap: var(--s-2);
  z-index: 200;
}
.toast {
  display: flex;
  align-items: center;
  gap: var(--s-2);
  border-radius: var(--r-md);
  padding: var(--s-3) var(--s-4);
  font-size: 13.5px;
  min-width: 220px;
  max-width: 360px;
  color: var(--ink);
}
.toast .ic { flex: none; }
.tone-success .ic { color: var(--pos); }
.tone-danger .ic { color: var(--neg); }
.tone-neutral .ic { color: var(--accent); }
.t-enter-active, .t-leave-active { transition: all 0.2s ease; }
.t-enter-from, .t-leave-to { opacity: 0; transform: translateY(-8px); }
@media (max-width: 560px) {
  .host { inset-inline: var(--s-4); top: var(--s-4); align-items: center; }
}
</style>
