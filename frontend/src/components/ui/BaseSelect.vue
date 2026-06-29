<script setup lang="ts">
import Icon from "./Icon.vue";

defineProps<{
  modelValue: string;
  label?: string;
  options: { value: string; label: string }[];
}>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();
</script>

<template>
  <label class="field">
    <span v-if="label" class="lbl">{{ label }}</span>
    <div class="wrap">
      <select
        class="sel"
        :value="modelValue"
        @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
      <Icon name="expand_more" :size="18" class="chev" />
    </div>
  </label>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: var(--s-2); }
.lbl { font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.wrap { position: relative; }
.sel {
  width: 100%;
  height: 38px;
  padding: 0;
  padding-inline: var(--s-3) var(--s-5);
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: rgba(255, 255, 255, 0.6);
  color: var(--ink);
  font-size: 13.5px;
  appearance: none;
  cursor: pointer;
}
.sel:focus { border-color: var(--accent); outline: none; box-shadow: 0 0 0 3px var(--accent-soft); background: #fff; }
.chev {
  position: absolute;
  inset-inline-end: var(--s-2);
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink-3);
  pointer-events: none;
}
</style>
