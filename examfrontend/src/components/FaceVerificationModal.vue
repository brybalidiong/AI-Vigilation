<template>
  <Transition name="fv-fade">
    <div v-if="show" class="fv-overlay" role="dialog" aria-modal="true" aria-labelledby="fv-title">
      <div class="fv-card">

        <!-- ── STEP 1: Verifying ── -->
        <template v-if="step === 'liveness'">
          <div class="fv-icon fv-icon--blue">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="32" height="32">
              <path d="M2 12s3.6-6 10-6 10 6 10 6-3.6 6-10 6S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>
            </svg>
          </div>
          <h2 id="fv-title" class="fv-title">Live face check</h2>
          <p class="fv-sub">{{ prompt }}</p>
          <div class="fv-spinner"></div>
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
          <p class="fv-sub">Please look directly at the camera and stay still.</p>
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
defineProps({
  show:         { type: Boolean, default: false },
  step:         { type: String,  default: 'verifying' }, // 'verifying' | 'success' | 'failed' | 'no-photo'
  attemptsLeft: { type: Number,  default: 2 },
  errorMessage: { type: String,  default: '' },
  prompt:       { type: String,  default: '' },
});

defineEmits(['cancel', 'retry']);
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
  max-width: 400px;
  text-align: center;
}

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
