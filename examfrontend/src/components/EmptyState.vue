<template>
  <div class="empty-state">
    <div class="empty-icon-wrap" v-if="icon">
      <svg v-html="icon" class="empty-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></svg>
    </div>
    <h3 class="empty-title">{{ title }}</h3>
    <p class="empty-desc" v-if="description">{{ description }}</p>
    <slot name="actions"></slot>
  </div>
</template>

<script setup>
defineProps({
  icon: {
    type: String,
    default: '<circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line>' // info icon
  },
  title: {
    type: String,
    required: true
  },
  description: {
    type: String,
    default: ''
  }
});
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 4rem 2rem;
  background: #f8fafc;
  border-radius: 12px;
  border: 2px dashed #e2e8f0;
  width: 100%;
}

.empty-icon-wrap {
  width: 64px;
  height: 64px;
  background: #f1f5f9;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 1.5rem;
  color: #64748b;
}

.empty-icon {
  width: 32px;
  height: 32px;
}

.empty-title {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.25rem;
  font-weight: 600;
}

.empty-desc {
  margin: 0;
  color: #64748b;
  font-size: 0.95rem;
  max-width: 400px;
  line-height: 1.5;
}
</style>
