import { defineStore } from "pinia";
import { ref } from "vue";
import { notifications as api } from "@/api/client";
import type { NotificationItem } from "@/api/types";

// Notification inbox store. AppShell starts polling on mount (the bell lives in the
// doc-centre header) and refreshes every POLL_MS so the badge stays live without a reload.
const POLL_MS = 30_000;

export const useNotifications = defineStore("notifications", () => {
  const items = ref<NotificationItem[]>([]);
  const unread = ref(0);
  let timer: number | null = null;

  async function fetch() {
    try {
      const data = await api.list();
      items.value = data.items;
      unread.value = data.unread;
    } catch {
      /* not logged in / transient — leave the current state */
    }
  }

  async function markAllRead() {
    if (!unread.value) return;
    unread.value = 0;
    items.value = items.value.map((n) => ({ ...n, read: true }));
    try { await api.markAllRead(); } catch { /* will reconcile on next poll */ }
  }

  async function markRead(id: number) {
    const n = items.value.find((x) => x.id === id);
    if (!n || n.read) return;
    n.read = true;
    unread.value = Math.max(0, unread.value - 1);
    try { await api.markRead(id); } catch { /* will reconcile on next poll */ }
  }

  function startPolling() {
    if (timer !== null) return;
    fetch();
    timer = window.setInterval(fetch, POLL_MS);
  }

  function stopPolling() {
    if (timer !== null) { window.clearInterval(timer); timer = null; }
  }

  return { items, unread, fetch, markAllRead, markRead, startPolling, stopPolling };
});
