import { defineStore } from "pinia";
import { ref } from "vue";

export type ToastTone = "success" | "danger" | "neutral";
export interface ToastItem {
  id: number;
  tone: ToastTone;
  message: string;
}

let seq = 0;

export const useToast = defineStore("toast", () => {
  const items = ref<ToastItem[]>([]);

  function push(message: string, tone: ToastTone = "success") {
    const id = ++seq;
    items.value.push({ id, message, tone });
    setTimeout(() => remove(id), 3200);
  }

  function remove(id: number) {
    items.value = items.value.filter((t) => t.id !== id);
  }

  return { items, push, remove };
});
