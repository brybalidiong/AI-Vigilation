<template>
  <div v-if="terminated" class="premium-terminated-overlay">
    <div class="glass-panel terminated-card">
      <div class="icon-container">
        <div class="pulse-ring"></div>
        <svg class="warning-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      
      <h1 class="terminated-title">Exam Terminated</h1>
      
      <div class="terminated-reason-box">
        <p v-if="terminateReason === 'gaze'" class="terminated-message">
          <template v-if="gazeNoFaceCount >= gazeNoFaceLimit">
            Your face was not visible to the camera <span class="highlight">{{ gazeNoFaceCount }}</span> time{{ gazeNoFaceCount !== 1 ? 's' : '' }}.
          </template>
          <template v-else>
            You looked away from the exam screen <span class="highlight">{{ gazeViolationCount }}</span> time{{ gazeViolationCount !== 1 ? 's' : '' }}.
          </template>
        </p>
        <p v-else class="terminated-message">
          You minimized the screen or switched tabs <span class="highlight">{{ switchCount }}</span> time{{ switchCount !== 1 ? 's' : '' }}.
        </p>
      </div>

      <p class="terminated-subtext">
        Your exam has been automatically submitted and flagged for academic review. Please contact your instructor for further details.
      </p>

      <button class="premium-btn" @click="$emit('dismiss')">
        Return to Dashboard
      </button>
    </div>
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
});
defineEmits(["dismiss"]);
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&display=swap');

.premium-terminated-overlay {
  position: fixed;
  inset: 0;
  z-index: 999999;
  background: radial-gradient(circle at center, rgba(30, 10, 15, 0.85) 0%, rgba(5, 5, 5, 0.98) 100%);
  backdrop-filter: blur(16px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  animation: fadeIn 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.glass-panel {
  background: rgba(40, 15, 20, 0.4);
  border: 1px solid rgba(255, 60, 80, 0.3);
  box-shadow: 0 24px 48px rgba(255, 30, 60, 0.15), inset 0 1px 0 rgba(255, 255, 255, 0.1);
  border-radius: 24px;
  padding: 3.5rem 3rem;
  width: 90%;
  max-width: 540px;
  text-align: center;
  position: relative;
  overflow: hidden;
  animation: slideUp 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  transform: translateY(20px);
  opacity: 0;
}

.glass-panel::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg, #ff3366, #ff8a00);
}

.icon-container {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 50, 80, 0.15);
  border-radius: 50%;
  border: 1px solid rgba(255, 50, 80, 0.4);
}

.pulse-ring {
  position: absolute;
  inset: -10px;
  border-radius: 50%;
  border: 2px solid rgba(255, 50, 80, 0.5);
  animation: pulse 2s infinite cubic-bezier(0.4, 0, 0.2, 1);
}

.warning-icon {
  width: 40px;
  height: 40px;
  color: #ff4d6d;
  filter: drop-shadow(0 0 12px rgba(255, 77, 109, 0.6));
}

.terminated-title {
  color: #ffffff;
  font-size: 2.2rem;
  font-weight: 700;
  margin-bottom: 1.5rem;
  letter-spacing: -0.5px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.5);
}

.terminated-reason-box {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.terminated-message {
  color: #f0f0f0;
  font-size: 1.15rem;
  line-height: 1.5;
  margin: 0;
}

.highlight {
  color: #ff4d6d;
  font-weight: 700;
  font-size: 1.3rem;
  padding: 0 0.2rem;
}

.terminated-subtext {
  color: #a0a0b0;
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 2.5rem;
}

.premium-btn {
  background: linear-gradient(135deg, #ff3366, #ff0044);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 1rem 2.5rem;
  font-size: 1.05rem;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 8px 24px rgba(255, 51, 102, 0.3);
  width: 100%;
}

.premium-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(255, 51, 102, 0.5);
  background: linear-gradient(135deg, #ff4d7a, #ff1a55);
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

@keyframes pulse {
  0% { transform: scale(1); opacity: 0.8; }
  100% { transform: scale(1.5); opacity: 0; }
}
</style>
