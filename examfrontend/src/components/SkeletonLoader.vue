<template>
  <div :class="['skeleton', type]" :style="{ width: width, height: height }"></div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'text', // 'text', 'card', 'avatar', 'row'
  },
  width: {
    type: String,
    default: '100%',
  },
  height: {
    type: String,
    default: 'auto',
  }
});
</script>

<style scoped>
.skeleton {
  background: #e2e8f0;
  background: linear-gradient(110deg, #ececec 8%, #f5f5f5 18%, #ececec 33%);
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
</style>
