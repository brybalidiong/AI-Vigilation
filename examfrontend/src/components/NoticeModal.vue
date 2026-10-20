<template>
  <Teleport to="body">
    <Transition name="notice-pop">
    <div v-if="modelValue" class="notice-backdrop" @click.self="$emit('close')">
      <section class="notice-dialog" :class="type" role="alertdialog" aria-modal="true" :aria-labelledby="titleId" :aria-describedby="messageId" @keydown.esc="$emit('close')">
        <div class="notice-mark" :class="type" aria-hidden="true">
          <svg v-if="type === 'success'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="m5 12 4 4L19 6" /></svg>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="9" /><path d="M12 7v6m0 4h.01" /></svg>
        </div>
        <span class="notice-label">{{ type === 'success' ? 'Success' : type === 'error' ? 'Something went wrong' : 'Heads up' }}</span>
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
.notice-dialog { --notice-color: #b45309; --notice-soft: #fff3df; position: relative; overflow: hidden; width: min(100%, 450px); padding: 2.35rem 2.25rem 2.1rem; border-radius: 22px; background: linear-gradient(180deg, #f8faff 0%, #fff 35%); border: 1px solid #dce4ef; box-shadow: 0 26px 80px rgba(15, 23, 42, .25), 0 5px 18px rgba(15, 23, 42, .08); text-align: center; font-family: 'Poppins', sans-serif; }
.notice-dialog::before { content: ''; position: absolute; inset: 0 0 auto; height: 5px; background: var(--notice-color); }
.notice-dialog.success { --notice-color: #15803d; --notice-soft: #e8f5ee; width: min(100%, 520px); }
.notice-dialog.error { --notice-color: #b91c1c; --notice-soft: #feecec; }
.notice-mark { width: 68px; height: 68px; display: grid; place-items: center; margin: 0 auto 1rem; border-radius: 21px; background: var(--notice-soft); color: var(--notice-color); box-shadow: 0 0 0 7px rgba(255, 255, 255, .88), 0 0 0 8px #e6eaf1; }
.notice-mark svg { width: 30px; height: 30px; }
.notice-label { display: inline-block; margin-bottom: .55rem; color: var(--notice-color); font-size: .7rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
h2 { margin: 0 0 .65rem; color: #1d3461; font-size: 1.45rem; font-weight: 800; line-height: 1.25; }
p { margin: 0 auto 1.8rem; max-width: 40ch; color: #475569; font-size: 1rem; line-height: 1.6; overflow-wrap: anywhere; }
.notice-button { min-width: 160px; padding: .88rem 1.4rem; border: 0; border-radius: 11px; background: #1d3461; color: white; font: inherit; font-size: .98rem; font-weight: 700; cursor: pointer; box-shadow: 0 6px 16px rgba(29, 52, 97, .18); transition: background .2s ease, transform .2s ease, box-shadow .2s ease; }
.notice-button:hover { background: #142849; transform: translateY(-1px); box-shadow: 0 9px 20px rgba(29, 52, 97, .22); }
.notice-button:focus-visible { outline: 3px solid #93b4f4; outline-offset: 3px; }
.notice-button:active { transform: translateY(0); }
.notice-pop-enter-active, .notice-pop-leave-active { transition: opacity .22s ease; }
.notice-pop-enter-active .notice-dialog, .notice-pop-leave-active .notice-dialog { transition: transform .28s cubic-bezier(.2, 1.35, .45, 1), opacity .22s ease; }
.notice-pop-enter-from, .notice-pop-leave-to { opacity: 0; }
.notice-pop-enter-from .notice-dialog, .notice-pop-leave-to .notice-dialog { opacity: 0; transform: translateY(18px) scale(.9); }
@media (prefers-reduced-motion: reduce) { .notice-pop-enter-active, .notice-pop-leave-active, .notice-pop-enter-active .notice-dialog, .notice-pop-leave-active .notice-dialog { transition: none; } }
@media (max-width: 480px) { .notice-dialog, .notice-dialog.success { padding: 2rem 1.25rem 1.5rem; } }
</style>
