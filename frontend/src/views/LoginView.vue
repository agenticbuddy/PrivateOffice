<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/stores/auth";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import LanguagePicker from "@/components/ui/LanguagePicker.vue";
import { applyLocale } from "@/i18n";

const { t, locale } = useI18n();
const auth = useAuth();
const route = useRoute();
const router = useRouter();

const email = ref("");
const password = ref("");
const error = ref("");
const busy = ref(false);
const uiLang = ref(locale.value as string);

function onLangChange(code: string) {
  uiLang.value = code;
  applyLocale(code);
}
function redirectTarget(): string {
  const r = route.query.redirect;
  return typeof r === "string" ? r : "/";
}
async function submit() {
  error.value = "";
  busy.value = true;
  try {
    await auth.login(email.value, password.value);
    router.push(redirectTarget());
  } catch {
    error.value = t("login.invalid");
  } finally {
    busy.value = false;
  }
}
onMounted(async () => {
  const magic = route.query.magic;
  if (typeof magic === "string") {
    busy.value = true;
    try {
      await auth.magic(magic);
      router.push("/");
      return;
    } catch {
      error.value = t("login.magicInvalid");
    } finally {
      busy.value = false;
    }
  }
});
</script>

<template>
  <div class="page">
    <div class="lang">
      <LanguagePicker :model-value="uiLang" @update:model-value="onLangChange" />
    </div>
    <div class="card glass">
      <div class="brand">
        <span class="logo">P</span>
        <div>
          <h1 class="t-h1">{{ t("app.name") }}</h1>
          <p class="t-muted t-small">{{ t("app.tagline") }}</p>
        </div>
      </div>

      <form class="form" @submit.prevent="submit">
        <BaseInput
          v-model="email"
          :label="t('login.email')"
          type="email"
          icon="mail"
          autocomplete="username"
          placeholder="you@example.com"
        />
        <BaseInput
          v-model="password"
          :label="t('login.password')"
          type="password"
          icon="lock"
          autocomplete="current-password"
        />
        <p v-if="error" class="err">{{ error }}</p>
        <BaseButton type="submit" variant="primary" block :loading="busy">
          {{ t("login.submit") }}
        </BaseButton>
      </form>
    </div>
  </div>
</template>

<style scoped>
.page {
  min-height: 100%;
  display: flex; align-items: center; justify-content: center;
  padding: var(--s-4); position: relative;
}
.lang { position: absolute; top: var(--s-4); inset-inline-end: var(--s-4); width: 200px; }
.card {
  width: 100%; max-width: 384px;
  border-radius: var(--r-xl);
  padding: var(--s-6);
}
.brand { display: flex; align-items: center; gap: var(--s-3); margin-bottom: var(--s-5); }
.logo {
  width: 44px; height: 44px; border-radius: var(--r-md);
  background: var(--accent-grad); color: #fff; font-weight: 800; font-size: 20px;
  display: inline-flex; align-items: center; justify-content: center; flex: none;
  box-shadow: 0 4px 12px rgba(10, 127, 94, 0.34);
}
.form { display: flex; flex-direction: column; gap: var(--s-4); }
.err { color: var(--neg); font-size: 13px; margin: 0; }
</style>
