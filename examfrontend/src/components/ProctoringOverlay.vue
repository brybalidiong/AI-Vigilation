<template>
  <div v-if="terminated" class="terminated-overlay">
    <section class="terminated-card" role="alertdialog" aria-modal="true" aria-labelledby="terminated-title" aria-describedby="terminated-reason terminated-note">
      <h1 id="terminated-title">Exam terminated</h1>

      <div id="terminated-reason" class="terminated-reason">
        <p v-if="terminateReason === 'gaze'">
          <template v-if="gazeNoFaceCount >= gazeNoFaceLimit">
            Your face was not visible to the camera {{ gazeNoFaceCount }} time{{ gazeNoFaceCount !== 1 ? 's' : '' }}.
          </template>
          <template v-else>
            You looked away from the exam screen {{ gazeViolationCount }} time{{ gazeViolationCount !== 1 ? 's' : '' }}.
          </template>
        </p>
        <p v-else-if="terminateReason === 'gadget'">
          A prohibited gadget was detected {{ gadgetWarningCount }} time{{ gadgetWarningCount !== 1 ? 's' : '' }}.
        </p>
        <p v-else-if="terminateReason === 'screen_share'">
          Entire-screen sharing stopped during the exam.
        </p>
        <p v-else-if="terminateReason === 'split_screen'">
          Split-screen or a resized exam window was detected. Total browser warnings: {{ switchCount }}.
        </p>
        <p v-else-if="terminateReason === 'screenshot'">
          A screenshot shortcut was attempted. Total browser warnings: {{ switchCount }}.
        </p>
        <p v-else-if="terminateReason === 'extended_monitor'">
          An additional display was detected. Total browser warnings: {{ switchCount }}.
        </p>
        <p v-else>
          You left the exam tab or window. Total browser warnings: {{ switchCount }}.
        </p>
      </div>

      <p id="terminated-note" class="terminated-note">
        Contact your instructor if you have questions about this result.
      </p>

      <button class="return-button" @click="$emit('dismiss')">
        Return to Dashboard
      </button>
    </section>
  </div>
</template>

<script setup>
defineProps({
  terminated: { type: Boolean, default: false },
  switchCount: { type: Number, default: 0 },
  terminateReason: { type: String, default: 'tab' },
  gazeViolationCount: { type: Number, default: 0 },
  gazeNoFaceCount: { type: Number, default: 0 },
  gazeViolationLimit: { type: Number, default: 8 },
  gazeNoFaceLimit: { type: Number, default: 5 },
  gadgetWarningCount: { type: Number, default: 0 },
  gadgetWarningLimit: { type: Number, default: 3 },
});
defineEmits(["dismiss"]);
</script>

<style scoped>
.terminated-overlay {
  position: fixed;
  inset: 0;
  z-index: 999999;
  display: grid;
  place-items: center;
  padding: 1rem;
  background: rgba(17, 24, 39, 0.68);
  font-family: 'Poppins', sans-serif;
}

.terminated-card {
  width: min(100%, 440px);
  padding: clamp(1.5rem, 5vw, 2rem);
  background: #fff;
  color: #1f2937;
  border-radius: 16px;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.22);
}

.terminated-card h1 {
  margin: 0 0 0.75rem;
  color: #172554;
  font-size: clamp(1.375rem, 4vw, 1.625rem);
  line-height: 1.25;
  font-weight: 700;
}

.terminated-reason p {
  margin: 0;
  font-size: 1rem;
  line-height: 1.55;
}

.terminated-note {
  margin: 0.75rem 0 1.5rem;
  color: #64748b;
  font-size: 0.875rem;
  line-height: 1.5;
}

.return-button {
  border: 0;
  border-radius: 8px;
  background: #1e3768;
  color: #fff;
  padding: 0.75rem 1.125rem;
  font: 600 0.9375rem 'Poppins', sans-serif;
  cursor: pointer;
}

.return-button:hover {
  background: #172b53;
}

.return-button:focus-visible {
  outline: 3px solid #93c5fd;
  outline-offset: 3px;
}

@media (max-width: 480px) {
  .return-button { width: 100%; }
}
</style>
