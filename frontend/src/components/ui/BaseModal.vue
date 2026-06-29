<script setup lang="ts">
import { watch } from "vue";
import Icon from "./Icon.vue";

const props = defineProps<{ open: boolean; title?: string }>();
const emit = defineEmits<{ (e: "close"): void }>();

watch(
  () => props.open,
  (o) => {
    document.body.style.overflow = o ? "hidden" : "";
  },
);
function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") emit("close");
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="overlay" @click.self="emit('close')" @keydown="onKey" tabindex="-1">
        <div class="modal" role="dialog" aria-modal="true">
          <header v-if="title" class="head">
            <h2 class="t-h1">{{ title }}</h2>
            <button class="x" @click="emit('close')" aria-label="Close"><Icon name="close" :size="20" /></button>
          </header>
          <div class="body"><slot /></div>
          <footer v-if="$slots.footer" class="foot"><slot name="footer" /></footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.overlay {
  position: fixed; inset: 0;
  background: rgba(17, 32, 63, 0.34);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  display: flex; align-items: center; justify-content: center;
  padding: var(--s-4); z-index: 100;
}
.modal {
  width: 100%; max-width: 460px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  border: 1px solid var(--glass-bd);
  border-radius: var(--r-xl);
  box-shadow: var(--glass-sh), inset 0 1px 0 var(--glass-hi);
  display: flex; flex-direction: column;
  max-height: 90vh; overflow: hidden;
}
.head {
  display: flex; align-items: center; justify-content: space-between;
  padding: var(--s-4) var(--s-5); border-bottom: 1px solid var(--line);
}
.x {
  border: none; background: transparent; color: var(--ink-3); cursor: pointer;
  display: flex; width: 30px; height: 30px; align-items: center; justify-content: center; border-radius: var(--r-sm);
}
.x:hover { background: rgba(20, 32, 56, 0.06); color: var(--ink); }
.body { padding: var(--s-5); overflow: auto; }
.foot {
  display: flex; justify-content: flex-end; gap: var(--s-2);
  padding: var(--s-4) var(--s-5); border-top: 1px solid var(--line);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.18s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.fade-enter-active .modal, .fade-leave-active .modal { transition: transform 0.18s ease; }
.fade-enter-from .modal, .fade-leave-to .modal { transform: scale(0.97); }
@media (max-width: 560px) {
  .overlay { align-items: flex-end; padding: 0; }
  .modal { max-width: 100%; border-radius: var(--r-xl) var(--r-xl) 0 0; }
}
</style>
