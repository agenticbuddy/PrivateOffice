import { defineStore } from "pinia";
import { ref } from "vue";
import { auth as authApi } from "@/api/client";
import type { User } from "@/api/types";
import { applyDesign, applyLocale } from "@/i18n";

export const useAuth = defineStore("auth", () => {
  const user = ref<User | null>(null);
  const ready = ref(false);

  function adopt(u: User | null) {
    user.value = u;
    if (u) {
      applyLocale(u.locale);
      applyDesign(u.design);
    }
  }

  async function fetchMe(): Promise<User | null> {
    try {
      adopt(await authApi.me());
    } catch {
      adopt(null);
    } finally {
      ready.value = true;
    }
    return user.value;
  }

  async function login(email: string, password: string) {
    adopt(await authApi.login(email, password));
  }

  async function magic(token: string) {
    adopt(await authApi.magic(token));
  }

  async function logout() {
    await authApi.logout();
    adopt(null);
  }

  async function setLocale(locale: string) {
    const u = await authApi.setLocale(locale);
    adopt(u);
  }

  async function setPassword(password: string) {
    adopt(await authApi.setPassword(password));
  }

  async function setDesign(design: string) {
    // Design is locale-agnostic: update user state and apply ONLY the design.
    // Do NOT route through adopt()/applyLocale — that would reset the rendered
    // locale to the saved value and clobber an active ?lang override (PROB-008).
    const u = await authApi.setDesign(design);
    user.value = u;
    applyDesign(u.design);
  }

  return { user, ready, fetchMe, login, magic, logout, setLocale, setPassword, setDesign };
});
