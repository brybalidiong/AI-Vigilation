<template>
  <Transition name="fv-fade">
    <div v-if="show" class="fv-overlay" role="dialog" aria-modal="true" aria-labelledby="fv-title">
      <div class="fv-card">
        <div v-if="showLivePreview" class="fv-steps" aria-label="Verification progress">
          <span :class="{ 'fv-step--active': step === 'detecting', 'fv-step--done': step !== 'detecting' }">1 Face</span>
          <span :class="{ 'fv-step--active': ['face-found', 'liveness', 'blink'].includes(step), 'fv-step--done': step === 'verifying' }">2 Blink</span>
          <span :class="{ 'fv-step--active': step === 'verifying' }">3 Match</span>
        </div>
        <div v-if="showLivePreview" class="fv-preview">
          <video ref="previewVideo" autoplay muted playsinline></video>
          <span class="fv-preview-label">Live camera</span>
        </div>

        <template v-if="step === 'detecting'">
          <h2 id="fv-title" class="fv-title">Finding your face</h2>
          <p class="fv-sub" aria-live="polite">{{ prompt }}</p>
          <div class="fv-spinner" aria-hidden="true"></div>
          <button class="fv-btn fv-btn--secondary" type="button" @click="$emit('cancel')">Cancel</button>
        </template>
        <template v-else-if="step === 'face-found'">
          <h2 id="fv-title" class="fv-title">Face detected</h2>
          <p class="fv-sub fv-sub--ready" role="status">{{ prompt }}</p>
          <button class="fv-btn fv-btn--secondary" type="button" @click="$emit('cancel')">Cancel</button>
        </template>
        <template v-else-if="step === 'liveness' || step === 'blink'">
          <h2 id="fv-title" class="fv-title" :class="{ 'fv-title--blink': step === 'blink' }">
            {{ step === 'blink' ? 'Blink now' : 'Prepare to blink' }}
          </h2>
          <p class="fv-sub" :class="{ 'fv-sub--blink': step === 'blink' }" aria-live="assertive">{{ prompt }}</p>
          <div class="fv-capture-indicator" :class="{ 'fv-capture-indicator--blink': step === 'blink' }">Camera is checking your eyes</div>
          <button class="fv-btn fv-btn--secondary" type="button" @click="$emit('cancel')">Cancel</button>
        </template>
        <template v-else-if="step === 'verifying'">
          <div class="fv-icon fv-icon--blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <h2 id="fv-title" class="fv-title">Verifying Identity</h2>
          <p class="fv-sub">Checking the blink and matching your face to your ID.</p>
          <div class="fv-spinner"></div>
        </template>

        <!-- ── STEP 2: Success ── -->
        <template v-else-if="step === 'success'">
          <div class="fv-icon fv-icon--green">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="32" height="32">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <h2 id="fv-title" class="fv-title">Identity Verified</h2>
          <p class="fv-sub">Your identity has been confirmed. Starting your exam...</p>
        </template>

        <!-- ── STEP 3: Failed ── -->
        <template v-else-if="step === 'failed'">
          <div class="fv-icon fv-icon--red">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="32" height="32">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </div>
          <h2 id="fv-title" class="fv-title">Verification Failed</h2>
          <div class="fv-error-box">
            {{ errorMessage || 'Face did not match the registered photo.' }}
          </div>
          <p class="fv-sub">
            {{ attemptsLeft > 0
              ? `You have ${attemptsLeft} attempt${attemptsLeft !== 1 ? 's' : ''} remaining. Ensure good lighting.`
              : 'You have used all attempts. Please contact your instructor.' }}
          </p>
          <div class="fv-actions">
            <button class="fv-btn fv-btn--secondary" @click="$emit('cancel')">Cancel</button>
            <button
              v-if="attemptsLeft > 0"
              class="fv-btn fv-btn--primary"
              @click="$emit('retry')"
            >Try Again</button>
          </div>
        </template>

        <!-- ── STEP 4: No face photo registered ── -->
        <template v-else-if="step === 'no-photo'">
          <div class="fv-icon fv-icon--orange">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="32" height="32">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <h2 id="fv-title" class="fv-title">No Photo Registered</h2>
          <p class="fv-sub">You have no formal photo registered. Please contact your administrator.</p>
          <div class="fv-actions">
            <button class="fv-btn fv-btn--secondary fv-btn--full" @click="$emit('cancel')">
              Return to Dashboard
            </button>
          </div>
        </template>

      </div>
    </div>
  </Transition>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue';

const props = defineProps({
  show:         { type: Boolean, default: false },
  step:         { type: String,  default: 'detecting' },
  attemptsLeft: { type: Number,  default: 2 },
  errorMessage: { type: String,  default: '' },
  prompt:       { type: String,  default: '' },
  stream:       { type: Object,  default: null },
});

defineEmits(['cancel', 'retry']);

const previewVideo = ref(null);
const showLivePreview = computed(() => ['detecting', 'face-found', 'liveness', 'blink', 'verifying'].includes(props.step));
watch(() => [props.show, props.step, props.stream], async () => {
  if (!props.show || !props.stream || !showLivePreview.value) return;
  await nextTick();
  if (previewVideo.value && previewVideo.value.srcObject !== props.stream) {
    previewVideo.value.srcObject = props.stream;
    previewVideo.value.play().catch(() => {});
  }
}, { immediate: true, flush: 'post' });
</script>

<style scoped>

.fv-overlay {
  position: fixed;
  inset: 0;
  z-index: 999998;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Poppins', sans-serif;
}

.fv-fade-enter-active, .fv-fade-leave-active {
  transition: opacity 0.2s ease;
}
.fv-fade-enter-from, .fv-fade-leave-to {
  opacity: 0;
}

.fv-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
  padding: 2.5rem 2rem;
  width: 90%;
  max-width: 460px;
  text-align: center;
}

.fv-steps {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.4rem;
  margin-bottom: 1rem;
  color: #94a3b8;
  font-size: 0.76rem;
  font-weight: 700;
}
.fv-steps span { padding: 0.4rem 0.25rem; border-radius: 6px; background: #f1f5f9; }
.fv-steps .fv-step--active { color: #1d3461; background: #e8eef8; }
.fv-steps .fv-step--done { color: #166534; background: #edf7ef; }
.fv-preview {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  background: #17253d;
  aspect-ratio: 16 / 10;
  margin-bottom: 1.3rem;
}
.fv-preview video { width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
.fv-preview-label {
  position: absolute;
  left: 0.75rem;
  bottom: 0.75rem;
  background: #17253d;
  color: #fff;
  padding: 0.3rem 0.55rem;
  border-radius: 5px;
  font-size: 0.72rem;
  font-weight: 700;
}
.fv-title--blink { color: #a34e0d; font-size: 1.8rem; }
.fv-sub--ready { color: #166534; font-weight: 600; }
.fv-sub--blink { color: #74400b; font-weight: 700; }
.fv-capture-indicator {
  margin: 0 auto 1.2rem;
  padding: 0.55rem 0.75rem;
  border-radius: 6px;
  background: #eef2f7;
  color: #475569;
  font-size: 0.8rem;
  font-weight: 600;
}
.fv-capture-indicator--blink { background: #fff2dc; color: #92400e; }

/* Icons */
.fv-icon {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 1.25rem;
}

.fv-icon--blue { background: #eff6ff; color: #3b82f6; }
.fv-icon--green { background: #f0fdf4; color: #22c55e; }
.fv-icon--red { background: #fef2f2; color: #ef4444; }
.fv-icon--orange { background: #fff7ed; color: #f97316; }

/* Text */
.fv-title {
  color: #0f172a;
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0 0 0.5rem;
}

.fv-sub {
  color: #64748b;
  font-size: 0.95rem;
  line-height: 1.5;
  margin: 0 0 1.5rem;
}

/* Spinner */
.fv-spinner {
  width: 36px;
  height: 36px;
  border: 3px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 1.5rem auto 0;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Error box */
.fv-error-box {
  background: #fef2f2;
  color: #b91c1c;
  border-radius: 8px;
  padding: 0.85rem 1rem;
  font-size: 0.9rem;
  font-weight: 500;
  margin-bottom: 1rem;
}

/* Buttons */
.fv-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.5rem;
}

.fv-btn {
  flex: 1;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.2s ease;
}

.fv-btn--primary {
  background: #3b82f6;
  color: #ffffff;
}
.fv-btn--primary:hover {
  background: #2563eb;
}

.fv-btn--secondary {
  background: #f1f5f9;
  color: #475569;
}
.fv-btn--secondary:hover {
  background: #e2e8f0;
}

.fv-btn--full {
  width: 100%;
  flex: unset;
}
</style>
