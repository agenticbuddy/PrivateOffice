<script setup lang="ts">
import { computed, ref } from "vue";
import { useI18n } from "vue-i18n";
import Icon from "./Icon.vue";

const props = defineProps<{
  modelValue: string;
  label?: string;
  type?: string;
  placeholder?: string;
  hint?: string;
  error?: string;
  autocomplete?: string;
  icon?: string;
}>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();

const { t } = useI18n();
const revealed = ref(false);
const isPassword = computed(() => (props.type ?? "text") === "password");
const effectiveType = computed(() =>
  isPassword.value && revealed.value ? "text" : props.type || "text",
);
</script>

<template>
  <label class="field">
    <span v-if="label" class="lbl">{{ label }}</span>
    <div class="wrap" :class="{ err: error }">
      <Icon v-if="icon" :name="icon" :size="18" class="lead" />
      <input
        class="inp"
        :class="{ 'has-lead': icon, 'has-toggle': isPassword }"
        :type="effectiveType"
        :placeholder="placeholder"
        :autocomplete="autocomplete"
        :value="modelValue"
        @input="$emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      />
      <button
        v-if="isPassword"
        type="button"
        class="reveal"
        :aria-label="revealed ? t('common.hidePassword') : t('common.showPassword')"
        :title="revealed ? t('common.hidePassword') : t('common.showPassword')"
        @click="revealed = !revealed"
      >
        <Icon :name="revealed ? 'visibility_off' : 'visibility'" :size="18" />
      </button>
    </div>
    <span v-if="error" class="msg err-msg">{{ error }}</span>
    <span v-else-if="hint" class="msg">{{ hint }}</span>
  </label>
</template>

<style scoped>
.field { display: flex; flex-direction: column; gap: var(--s-2); }
.lbl { font-size: 12.5px; font-weight: 600; color: var(--ink-2); }
.wrap {
  position: relative;
  display: flex;
  align-items: center;
  height: 38px;
  border: 1px solid var(--line);
  border-radius: var(--r-md);
  background: rgba(255, 255, 255, 0.6);
  transition: border-color 0.13s ease, box-shadow 0.13s ease, background 0.13s ease;
}
.wrap:focus-within { border-color: var(--accent); background: #fff; box-shadow: 0 0 0 3px var(--accent-soft); }
.wrap.err { border-color: var(--neg); }
.lead { color: var(--ink-3); margin-inline-start: var(--s-3); }
.inp {
  flex: 1;
  min-width: 0;
  height: 100%;
  padding: 0 var(--s-3);
  border: none;
  background: transparent;
  color: var(--ink);
  font-size: 13.5px;
  outline: none;
}
.inp.has-lead { padding-inline-start: var(--s-2); }
.inp.has-toggle { padding-inline-end: 2px; }
.reveal {
  width: 30px; height: 30px;
  margin-inline-end: 4px;
  display: inline-flex; align-items: center; justify-content: center;
  border: none; background: transparent; color: var(--ink-3); cursor: pointer;
  border-radius: var(--r-sm); flex: none;
}
.reveal:hover { color: var(--ink-2); background: rgba(20, 32, 56, 0.06); }
.msg { font-size: 11.5px; color: var(--ink-3); }
.err-msg { color: var(--neg); }
</style>
