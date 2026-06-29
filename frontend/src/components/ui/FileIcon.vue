<script setup lang="ts">
import { computed } from "vue";
import Icon from "./Icon.vue";

const props = defineProps<{ type: "folder" | "file"; format?: string | null; size?: number }>();

const DOC = ["docx", "doc", "odt", "rtf", "txt"];
const SHEET = ["xlsx", "xls", "ods", "csv"];
const SLIDE = ["pptx", "ppt", "odp"];

const kind = computed(() => {
  if (props.type === "folder") return "folder";
  const f = (props.format || "").toLowerCase();
  if (SHEET.includes(f)) return "sheet";
  if (SLIDE.includes(f)) return "slide";
  if (DOC.includes(f)) return "doc";
  return "other";
});

const icon = computed(
  () =>
    ({ folder: "folder", sheet: "table_chart", slide: "co_present", doc: "description", other: "draft" })[
      kind.value
    ],
);
const color = computed(
  () =>
    ({
      folder: "var(--folder)",
      sheet: "var(--sheet)",
      slide: "var(--slide)",
      doc: "var(--doc)",
      other: "var(--ink-3)",
    })[kind.value],
);
</script>

<template>
  <Icon :name="icon" :size="size || 22" :color="color" :fill="type === 'folder'" />
</template>
