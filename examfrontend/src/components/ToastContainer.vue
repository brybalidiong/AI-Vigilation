<template>
  <div class="toast-container" aria-live="polite" aria-relevant="additions">
    <TransitionGroup name="toast">
      <div 
        v-for="toast in toasts" 
        :key="toast.id" 
        class="toast" 
        :class="`toast-${toast.type}`"
        :role="toast.type === 'error' ? 'alert' : 'status'"
      >
        <div class="toast-icon">
          <svg v-if="toast.type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <svg v-else-if="toast.type === 'error'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="15" y1="9" x2="9" y2="15"></line>
            <line x1="9" y1="9" x2="15" y2="15"></line>
          </svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="16" x2="12" y2="12"></line>
            <line x1="12" y1="8" x2="12.01" y2="8"></line>
          </svg>
        </div>
        <div class="toast-content">{{ toast.message }}</div>
        <button type="button" class="toast-close" aria-label="Dismiss notification" @click="removeToast(toast.id)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { toasts, removeToast } from '@/utils/toast';
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  pointer-events: none;
}

.toast {
  --toast-accent: #2563eb;
  --toast-tint: #eff6ff;
  pointer-events: auto;
  display: flex;
  align-items: flex-start;
  gap: 0.85rem;
  background: linear-gradient(90deg, var(--toast-tint) 0%, #fff 24%);
  padding: 0.95rem 1rem;
  border-radius: 15px;
  box-shadow: 0 14px 38px rgba(15, 23, 42, 0.15), 0 2px 8px rgba(15, 23, 42, 0.06);
  width: min(400px, calc(100vw - 2.5rem));
  border: 1px solid #e2e8f0;
  border-left: 4px solid var(--toast-accent);
}

.toast-success {
  --toast-accent: #15803d;
  --toast-tint: #ecfdf3;
}

.toast-error {
  --toast-accent: #b91c1c;
  --toast-tint: #fff1f2;
}

.toast-info {
  --toast-accent: #2563eb;
  --toast-tint: #eff6ff;
}

.toast-icon {
  flex: none;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 11px;
  background: var(--toast-tint);
  color: var(--toast-accent);
}

.toast-icon svg {
  width: 19px;
  height: 19px;
}

.toast-content {
  flex: 1;
  align-self: center;
  color: #24344d;
  font-size: 0.92rem;
  font-weight: 600;
  font-family: 'Poppins', sans-serif;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.toast-close {
  flex: none;
  background: #f1f5f9;
  border: none;
  border-radius: 8px;
  color: #64748b;
  cursor: pointer;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s;
}

.toast-close:hover {
  background: #e2e8f0;
  color: #1d3461;
}
.toast-close:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }

.toast-close svg {
  width: 16px;
  height: 16px;
}

/* Transitions */
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(30px);
}

.toast-leave-to {
  opacity: 0;
  transform: scale(0.9);
}
@media (max-width: 480px) {
  .toast-container { top: 0.75rem; right: 0.75rem; left: 0.75rem; }
  .toast { width: 100%; }
}
@media (prefers-reduced-motion: reduce) {
  .toast-enter-active, .toast-leave-active { transition: none; }
}
</style>
