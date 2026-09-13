import { ref } from 'vue';

export const toasts = ref([]);

let toastId = 0;

export function addToast(message, type = 'success', duration = 3000) {
  const id = toastId++;
  const toast = { id, message, type };
  toasts.value.push(toast);

  if (duration > 0) {
    setTimeout(() => {
      removeToast(id);
    }, duration);
  }
}

export function removeToast(id) {
  const index = toasts.value.findIndex(t => t.id === id);
  if (index > -1) {
    toasts.value.splice(index, 1);
  }
}
