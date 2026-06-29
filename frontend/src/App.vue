<script setup lang="ts">
import { watch } from "vue";
import { RouterView, useRoute } from "vue-router";
import ToastHost from "./components/ui/ToastHost.vue";
import { applyLocale } from "./i18n";

// Honor ?lang=<code> anywhere — used by the language sweep to preview the UI in any
// locale without authenticating.
const route = useRoute();
watch(
  () => route.query.lang,
  (lang) => {
    if (typeof lang === "string" && lang) applyLocale(lang);
  },
  { immediate: true },
);
</script>

<template>
  <!-- Global liquid-glass backdrop (gradient + ambient blobs) -->
  <div class="lg-bg" aria-hidden="true">
    <div class="grad"></div>
    <div class="blob b1"></div>
    <div class="blob b2"></div>
    <div class="blob b3"></div>
  </div>
  <div class="app-layer">
    <RouterView />
  </div>
  <ToastHost />
</template>

<style scoped>
.app-layer { position: relative; z-index: 1; height: 100%; }
</style>
