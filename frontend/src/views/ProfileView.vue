<script setup lang="ts">
import { ref } from "vue";
import { useI18n } from "vue-i18n";
import { useAuth } from "@/stores/auth";
import { useToast } from "@/stores/toast";
import AppShell from "@/components/AppShell.vue";
import BaseButton from "@/components/ui/BaseButton.vue";
import BaseInput from "@/components/ui/BaseInput.vue";
import BaseSelect from "@/components/ui/BaseSelect.vue";
import LanguagePicker from "@/components/ui/LanguagePicker.vue";
import Avatar from "@/components/ui/Avatar.vue";
import Icon from "@/components/ui/Icon.vue";

const { t } = useI18n();
const auth = useAuth();
const toast = useToast();

const lang = ref(auth.user?.locale ?? "en");
const design = ref(auth.user?.design ?? "glass");
const password = ref("");
const savingPw = ref(false);

const designOptions = [
  { value: "glass", label: t("profile.designGlass") },
  { value: "glass2", label: t("profile.designGlass2") },
  { value: "classic", label: t("profile.designClassic") },
];

async function changeLang(code: string) {
  lang.value = code;
  try {
    await auth.setLocale(code);
    toast.push(t("profile.saved"));
  } catch {
    toast.push(t("toast.error"), "danger");
  }
}
async function changeDesign(code: string) {
  design.value = code;
  try {
    await auth.setDesign(code);
    toast.push(t("profile.saved"));
  } catch {
    toast.push(t("toast.error"), "danger");
  }
}
async function savePassword() {
  if (!password.value) return;
  savingPw.value = true;
  try {
    await auth.setPassword(password.value);
    password.value = "";
    toast.push(t("profile.saved"));
  } catch {
    toast.push(t("toast.error"), "danger");
  } finally {
    savingPw.value = false;
  }
}
</script>

<template>
  <AppShell>
    <div class="page">
      <header class="head glass">
        <Avatar v-if="auth.user" :name="auth.user.full_name" :id="auth.user.id" :size="56" />
        <div>
          <h1 class="t-display">{{ auth.user?.full_name }}</h1>
          <p class="t-muted">{{ auth.user?.email }}</p>
        </div>
      </header>

      <section class="card glass">
        <div class="cardhead"><Icon name="palette" :size="20" /><h2 class="t-h2">{{ t("profile.appearance") }}</h2></div>
        <p class="t-muted t-small">{{ t("profile.appearanceHint") }}</p>
        <BaseSelect :model-value="design" :options="designOptions" @update:model-value="changeDesign" />
      </section>

      <section class="card glass">
        <div class="cardhead"><Icon name="translate" :size="20" /><h2 class="t-h2">{{ t("profile.language") }}</h2></div>
        <p class="t-muted t-small">{{ t("profile.languageHint") }}</p>
        <LanguagePicker :model-value="lang" @update:model-value="changeLang" />
      </section>

      <section class="card glass">
        <div class="cardhead"><Icon name="lock" :size="20" /><h2 class="t-h2">{{ t("profile.setPassword") }}</h2></div>
        <form class="pw" @submit.prevent="savePassword">
          <!-- Hidden username field lets password managers associate the saved credential and clears Chrome's a11y hint; must be off-screen (not display:none) so it stays in the form. -->
          <input class="visually-hidden" type="text" name="username" autocomplete="username" readonly :value="auth.user?.email ?? ''" tabindex="-1" aria-hidden="true" />
          <BaseInput v-model="password" :label="t('profile.newPassword')" type="password" icon="key" autocomplete="new-password" />
          <BaseButton type="submit" variant="primary" :loading="savingPw" :disabled="!password">
            {{ t("common.save") }}
          </BaseButton>
        </form>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.page { flex: 1; min-height: 0; overflow: auto; display: flex; flex-direction: column; gap: 6px; max-width: 680px; }
.head { border-radius: var(--r-lg); padding: var(--s-5); display: flex; align-items: center; gap: var(--s-4); }
.card {
  border-radius: var(--r-lg); padding: var(--s-5);
  display: flex; flex-direction: column; gap: var(--s-3);
}
.cardhead { display: flex; align-items: center; gap: var(--s-2); color: var(--accent-ink); }
.cardhead h2 { color: var(--ink); }
.pw { display: flex; gap: var(--s-3); align-items: flex-end; }
.pw :deep(.field) { flex: 1; }
/* Off-screen clipping (not display:none) keeps the username field in the form so password managers and a11y see it. */
.visually-hidden {
  position: absolute; width: 1px; height: 1px;
  margin: -1px; padding: 0; overflow: hidden;
  clip: rect(0 0 0 0); clip-path: inset(50%);
  white-space: nowrap; border: 0;
}
</style>
