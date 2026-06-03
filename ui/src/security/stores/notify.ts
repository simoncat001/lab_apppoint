import { defineStore } from 'pinia';
import { ref } from 'vue';

export type NoticeTone = 'info' | 'success' | 'error';

export interface Notice {
  id: number;
  message: string;
  tone: NoticeTone;
}

export const useNotifyStore = defineStore('notify', () => {
  const items = ref<Notice[]>([]);

  const push = (message: string, tone: NoticeTone = 'info') => {
    const id = Date.now() + Math.floor(Math.random() * 1000);
    items.value.push({ id, message, tone });
    setTimeout(() => {
      items.value = items.value.filter((item) => item.id !== id);
    }, 3200);
  };

  const remove = (id: number) => {
    items.value = items.value.filter((item) => item.id !== id);
  };

  return { items, push, remove };
});
