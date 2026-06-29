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
</script>

<template>
  <Teleport to="body">
    <Transition name="slide">
      <div v-if="open" class="overlay" @click.self="emit('close')">
        <aside class="drawer" role="dialog" aria-modal="true">
          <header class="head">
            <h2 class="t-h1">{{ title }}</h2>
            <button class="x" @click="emit('close')" aria-label="Close"><Icon name="close" :size="20" /></button>
          </header>
          <div class="body"><slot /></div>
        </aside>
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
  display: flex; justify-content: flex-end; z-index: 100;
}
.drawer {
  width: 420px; max-width: 100%; height: 100%;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  border-inline-start: 1px solid var(--glass-bd);
  display: flex; flex-direction: column;
  box-shadow: var(--glass-sh);
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
.body { padding: var(--s-5); overflow: auto; flex: 1; }
.slide-enter-active, .slide-leave-active { transition: opacity 0.2s ease; }
.slide-enter-active .drawer, .slide-leave-active .drawer { transition: transform 0.2s ease; }
.slide-enter-from, .slide-leave-to { opacity: 0; }
.slide-enter-from .drawer, .slide-leave-to .drawer { transform: translateX(100%); }
[dir="rtl"] .slide-enter-from .drawer, [dir="rtl"] .slide-leave-to .drawer { transform: translateX(-100%); }
@media (max-width: 560px) {
  .drawer { width: 100%; }
}
</style>
