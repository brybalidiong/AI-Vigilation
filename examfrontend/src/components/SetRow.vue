<template>
  <div class="turo-list-card" @click="$emit('click')">
    <div class="turo-list-decor" :class="colorClass"></div>
    <div class="turo-list-icon" :class="colorClass">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="22" height="22"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
    </div>
    <div class="turo-list-info">
      <h4 class="turo-list-title">{{ name }}</h4>
      <div class="turo-list-meta">
        <span class="turo-badge">{{ count }} student{{ count !== 1 ? 's' : '' }} enrolled</span>
      </div>
    </div>
    <div class="turo-list-actions">
      <slot name="actions"></slot>
      <div class="turo-arrow">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18"><polyline points="9 18 15 12 9 6"></polyline></svg>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  name: { type: String, default: "" },
  count: { type: Number, default: 0 },
  colorClass: { type: String, default: "turo-color-1" }
});
defineEmits(["click"]);
</script>

<style scoped>

.turo-list-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.25rem;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
  position: relative;
  overflow: hidden;
  margin-bottom: 0.75rem;
}
.turo-list-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  border-color: #cbd5e1;
  background: #f8fafc;
}

.turo-list-decor {
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 6px;
  border-radius: 6px 0 0 6px;
}
.turo-color-1 { background: linear-gradient(135deg, #6366f1, #a855f7); color: #6366f1; }
.turo-color-2 { background: linear-gradient(135deg, #10b981, #3b82f6); color: #10b981; }
.turo-color-3 { background: linear-gradient(135deg, #f59e0b, #ef4444); color: #f59e0b; }
.turo-color-4 { background: linear-gradient(135deg, #ec4899, #8b5cf6); color: #ec4899; }

.turo-list-icon {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.turo-list-info {
  flex: 1;
  min-width: 0;
}
.turo-list-title {
  font-family: 'Poppins', sans-serif;
  font-size: 1.15rem;
  font-weight: 700;
  color: #1e293b;
  margin: 0 0 0.4rem 0;
}
.turo-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.3rem 0.6rem;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 6px;
  font-family: 'Poppins', sans-serif;
  font-size: 0.75rem;
  font-weight: 600;
}

.turo-list-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.turo-arrow {
  color: #cbd5e1;
  transition: all 0.3s ease;
}
.turo-list-card:hover .turo-arrow {
  color: #6366f1;
  transform: translateX(4px);
}
</style>
