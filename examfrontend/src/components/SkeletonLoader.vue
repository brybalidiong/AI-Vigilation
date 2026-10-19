<template>
  <div :class="['skeleton', type]" :style="{ width, height }" aria-hidden="true"></div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'text', // 'text', 'card', 'avatar', 'row'
  },
  width: {
    type: String,
    default: null,
  },
  height: {
    type: String,
    default: null,
  }
});
</script>

<style scoped>
.skeleton {
  width: 100%;
  background: linear-gradient(110deg, #e2e8f0 8%, #f1f5f9 18%, #e2e8f0 33%);
  border-radius: 5px;
  background-size: 200% 100%;
  animation: 1.5s shine linear infinite;
  display: inline-block;
}

.skeleton.text {
  height: 1em;
  margin-bottom: 0.5rem;
  border-radius: 4px;
}

.skeleton.avatar {
  border-radius: 50%;
  width: 48px;
  height: 48px;
}

.skeleton.card {
  border-radius: 18px;
  height: 240px;
}

.skeleton.row {
  border-radius: 8px;
  height: 70px;
  margin-bottom: 0.5rem;
}

@keyframes shine {
  to {
    background-position-x: -200%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .skeleton { animation: none; }
}
</style>
