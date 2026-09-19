<template>
  <article class="timeline-row">
    <div class="timeline-time" :title="timeText">
      <span class="timeline-time-clock">{{ timeClock }}</span>
      <span v-if="timeMeridiem" class="timeline-time-meridiem">{{ timeMeridiem }}</span>
    </div>

    <div class="timeline-main" :class="{ 'timeline-main--center': centerCopy }">
      <div v-if="!centerCopy" class="timeline-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
        </svg>
      </div>
      <div class="timeline-copy" :class="{ 'timeline-copy--center': centerCopy }">
        <div class="timeline-title-row">
          <h3 class="timeline-title">{{ title || 'Untitled exam' }}</h3>
          <span
            v-if="status"
            class="timeline-status status-badge"
            :class="statusClass"
          >{{ status }}</span>
        </div>
        <p v-if="subtitle" class="timeline-subtitle">{{ subtitle }}</p>
      </div>
    </div>

    <div class="timeline-actions">
      <slot name="actions"></slot>
    </div>
  </article>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  timeText: { type: String, default: '' },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  status: { type: String, default: '' },
  statusClass: { type: [String, Object, Array], default: '' },
  centerCopy: { type: Boolean, default: false },
});

const timeClock = computed(() => {
  const t = (props.timeText || '').trim();
  const m = t.match(/^(\d{1,2}:\d{2})/);
  return m ? m[1] : t || '—';
});

const timeMeridiem = computed(() => {
  const t = (props.timeText || '').trim();
  const m = t.match(/\b(AM|PM)\b/i);
  return m ? m[1].toUpperCase() : '';
});
</script>

<style scoped>
.timeline-row {
  position: relative;
  display: grid;
  grid-template-columns: 5rem minmax(0, 1fr) auto;
  grid-template-areas: "time main actions";
  align-items: center;
  column-gap: 1rem;
  padding: 0.85rem 1rem 0.85rem 0.9rem;
  margin-bottom: 0.6rem;
  border-radius: 13px;
  background: #fff;
  border: 1px solid #e8edf5;
  transition: border-color 0.18s, box-shadow 0.18s;
}
.timeline-row::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--dash-accent, #1D3461);
  border-radius: 3px 0 0 3px;
  pointer-events: none;
}
.timeline-row:hover {
  border-color: rgba(var(--dash-accent-rgb, 29, 52, 97), 0.22);
  box-shadow: 0 8px 24px rgba(var(--dash-accent-rgb, 29, 52, 97), 0.09);
}
.timeline-time {
  grid-area: time;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding-left: 0.25rem;
}
.timeline-time-clock {
  font-family: 'Poppins', sans-serif;
  font-size: 0.92rem;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: #0f172a;
  line-height: 1.1;
}
.timeline-time-meridiem {
  margin-top: 0.1rem;
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748b;
}
.timeline-main {
  grid-area: main;
  display: flex;
  align-items: center;
  gap: 0.65rem;
  min-width: 0;
}
.timeline-main--center {
  justify-content: center;
}
.timeline-icon {
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--dash-accent, #1D3461);
  background: var(--dash-accent-soft, #eef2ff);
}
.timeline-icon svg {
  width: 17px;
  height: 17px;
  display: block;
}
.timeline-copy {
  flex: 1;
  min-width: 0;
}
.timeline-copy--center {
  flex: 0 1 auto;
  text-align: center;
}
.timeline-copy--center .timeline-title-row {
  justify-content: center;
}
.timeline-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  margin-bottom: 0.15rem;
}
.timeline-title {
  margin: 0;
  font-family: 'Poppins', sans-serif;
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.25;
  color: #1e293b;
}
.timeline-subtitle {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 500;
  color: #94a3b8;
}
.timeline-status {
  font-size: 0.65rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.2rem 0.5rem !important;
  border-radius: 999px !important;
}
.timeline-actions {
  grid-area: actions;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.4rem;
}
@media (max-width: 720px) {
  .timeline-row {
    grid-template-columns: 1fr;
    grid-template-areas:
      "time"
      "main"
      "actions";
    text-align: center;
  }
  .timeline-time {
    align-items: center;
    flex-direction: row;
    gap: 0.35rem;
    justify-content: center;
    padding-left: 0;
  }
  .timeline-time-meridiem {
    margin-top: 0;
  }
  .timeline-main {
    flex-direction: column;
  }
  .timeline-actions {
    justify-content: center;
  }
}
</style>
