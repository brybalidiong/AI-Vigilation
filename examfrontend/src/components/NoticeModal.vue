<template>
  <Teleport to="body">
    <Transition name="notice-pop">
    <div v-if="modelValue" class="notice-backdrop" @click.self="$emit('close')">
      <section class="notice-dialog" :class="type" role="alertdialog" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="messageId" @keydown.esc="$emit('close')">
        <div class="notice-mark" :class="type" aria-hidden="true">
          <svg v-if="type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m5 12 4 4L19 6" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9" /><path d="M12 7v6m0 4h.01" /></svg>
        </div>
        <h2 :id="titleId">{{ title || (type === 'success' ? 'Action complete' : 'Please note') }}</h2>
        <p :id="messageId">{{ message }}</p>
        <button type="button" class="notice-button" autofocus @click="$emit('close')">OK</button>
      </section>
    </div>
    </Transition>
  </Teleport>
</template>

<script setup>
defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  message: { type: String, default: '' },
  type: { type: String, default: 'success' },
});
defineEmits(['close']);
const titleId = `notice-title-${Math.random().toString(36).slice(2)}`;
const messageId = `notice-message-${Math.random().toString(36).slice(2)}`;
</script>

<style scoped>
.notice-backdrop { position: fixed; inset: 0; z-index: 1000002; display: grid; place-items: center; padding: 1rem; background: rgba(15, 23, 42, .58); backdrop-filter: blur(5px); }
.notice-dialog { width: min(100%, 450px); padding: 2.25rem; border-radius: 22px; background: #fff; border: 1px solid #e2e8f0; box-shadow: 0 26px 80px rgba(15, 23, 42, .28); text-align: center; font-family: 'Poppins', sans-serif; }
.notice-dialog.success { width: min(100%, 520px); padding: 2.75rem 2.5rem 2.25rem; }
.notice-mark { width: 64px; height: 64px; display: grid; place-items: center; margin: 0 auto 1.35rem; border-radius: 20px; background: #e8f5ee; color: #15803d; }
.notice-mark.warning { background: #fff3df; color: #b45309; }
.notice-mark.error { background: #feecec; color: #b91c1c; }
.notice-mark svg { width: 30px; height: 30px; }
h2 { margin: 0 0 .65rem; color: #1d3461; font-size: 1.45rem; font-weight: 800; line-height: 1.25; }
p { margin: 0 auto 1.9rem; max-width: 40ch; color: #475569; font-size: 1.02rem; line-height: 1.6; }
.notice-button { min-width: 160px; padding: .88rem 1.4rem; border: 0; border-radius: 11px; background: #1d3461; color: white; font: inherit; font-size: .98rem; font-weight: 700; cursor: pointer; }
.notice-button:hover, .notice-button:focus-visible { background: #142849; }
.notice-pop-enter-active, .notice-pop-leave-active { transition: opacity .22s ease; }
.notice-pop-enter-active .notice-dialog, .notice-pop-leave-active .notice-dialog { transition: transform .28s cubic-bezier(.2, 1.35, .45, 1), opacity .22s ease; }
.notice-pop-enter-from, .notice-pop-leave-to { opacity: 0; }
.notice-pop-enter-from .notice-dialog, .notice-pop-leave-to .notice-dialog { opacity: 0; transform: translateY(18px) scale(.9); }
@media (prefers-reduced-motion: reduce) { .notice-pop-enter-active, .notice-pop-leave-active, .notice-pop-enter-active .notice-dialog, .notice-pop-leave-active .notice-dialog { transition: none; } }
</style>
