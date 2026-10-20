<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="confirm-overlay"
      role="presentation"
      @click.self="onCancel"
    >
      <div
        class="confirm-dialog"
        :class="variant"
        role="dialog"
        aria-modal="true"
        :aria-labelledby="titleId"
        @keydown.escape.prevent="onCancel"
      >
        <!-- Icon ring -->
        <div class="icon-ring" :class="variant">
          <svg v-if="variant === 'neutral'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/>
            <path d="M9 6V4h6v2"/>
          </svg>
        </div>

        <h2 :id="titleId" class="confirm-title">{{ title }}</h2>
        <p class="confirm-message">{{ message }}</p>

        <div class="confirm-actions">
          <button type="button" class="confirm-btn cancel" @click="onCancel">
            {{ cancelText }}
          </button>
          <button
            type="button"
            class="confirm-btn"
            :class="variant === 'danger' ? 'danger' : 'primary'"
            @click="onConfirm"
          >
            {{ confirmText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { watch } from "vue";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: "Confirm" },
  message: { type: String, default: "" },
  confirmText: { type: String, default: "Confirm" },
  cancelText: { type: String, default: "Cancel" },
  /** "danger" (destructive) or "neutral" (e.g. logout) */
  variant: { type: String, default: "danger" },
});

const emit = defineEmits(["update:modelValue", "confirm", "cancel"]);

const titleId = "confirm-modal-title-" + Math.random().toString(36).slice(2);

function onConfirm() {
  emit("confirm");
  emit("update:modelValue", false);
}

function onCancel() {
  emit("cancel");
  emit("update:modelValue", false);
}

watch(
  () => props.modelValue,
  (open) => {
    if (typeof document === "undefined") return;
    document.body.style.overflow = open ? "hidden" : "";
  },
);
</script>


<style scoped>

.confirm-overlay {
  position: fixed; inset: 0; z-index: 9999;
  display: flex; align-items: center; justify-content: center;
  padding: 1.25rem;
  background: rgba(15, 23, 42, 0.58);
  animation: overlayIn 0.3s ease;
}
@keyframes overlayIn { from { opacity: 0; } to { opacity: 1; } }

.confirm-dialog {
  width: 100%; max-width: 420px;
  border-radius: 24px;
  border: 1px solid #d9e1ec;
  background: #fff;
  box-shadow: 0 24px 64px rgba(15, 23, 42, 0.22);
  padding: 2.5rem;
  color: #1e293b;
  font-family: 'Poppins', sans-serif;
  animation: dialogIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.confirm-dialog.danger  { border-color: rgba(239, 68, 68, 0.2); }

@keyframes dialogIn {
  from { transform: scale(0.94) translateY(20px); opacity: 0; }
  to   { transform: scale(1) translateY(0); opacity: 1; }
}

.icon-ring {
  width: 56px; height: 56px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 1.5rem;
  box-shadow: 0 8px 16px rgba(0,0,0,0.05);
}
.icon-ring.neutral { background: rgba(29, 52, 97, 0.1); color: #1D3461; }
.icon-ring.danger  { background: linear-gradient(135deg, #fee2e2, #fecaca); color: #dc2626; }

.confirm-title {
  margin: 0 0 0.75rem;
  font-size: 1.25rem; font-weight: 800;
  letter-spacing: -0.02em; color: #1e293b;
  font-family: 'Poppins', sans-serif;
}

.confirm-message {
  margin: 0 0 2rem;
  font-size: 0.95rem; line-height: 1.6;
  color: #64748b;
}

.confirm-actions {
  display: flex; justify-content: flex-end;
  gap: 1rem; flex-wrap: wrap;
}

.confirm-btn {
  border-radius: 12px; padding: 0.75rem 1.5rem;
  font-weight: 700; font-size: 0.9rem;
  cursor: pointer; border: 1px solid transparent;
  font-family: 'Poppins', sans-serif; transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}

.confirm-btn.cancel {
  background: transparent; border-color: #cbd5e1; color: #64748b;
}
.confirm-btn.cancel:hover { background: #f8fafc; color: #1e293b; border-color: #94a3b8; transform: translateY(-2px); }

.confirm-btn.primary {
  background: #1D3461; color: #fff; box-shadow: 0 4px 12px rgba(29, 52, 97, 0.2);
}
.confirm-btn.primary:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(29, 52, 97, 0.3); background: #162a4f; }

.confirm-btn.danger {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: #fff; box-shadow: 0 4px 12px rgba(239, 68, 68, 0.2);
}
.confirm-btn.danger:hover { transform: translateY(-2px); box-shadow: 0 8px 16px rgba(239, 68, 68, 0.3); }
</style>
