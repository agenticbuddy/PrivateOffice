<script setup lang="ts">
import { LOCALES } from "@/i18n/locales";
import BaseSelect from "./BaseSelect.vue";

defineProps<{ modelValue: string; label?: string }>();
defineEmits<{ (e: "update:modelValue", v: string): void }>();

const options = LOCALES.map((l) => ({ value: l.code, label: l.native }));
</script>

<template>
  <BaseSelect
    :model-value="modelValue"
    :label="label"
    :options="options"
    @update:model-value="$emit('update:modelValue', $event)"
  />
</template>
