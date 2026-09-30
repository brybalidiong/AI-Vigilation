<template>
  <article class="timeline-row" :class="[toneClass, { 'timeline-row--center': centerCopy }]">
    <div class="timeline-date" :title="dateTitle">
      <span class="timeline-date-month">{{ dateMonth }}</span>
      <span class="timeline-date-day">{{ dateDay }}</span>
    </div>

    <div class="timeline-rail" aria-hidden="true">
      <span class="timeline-dot"></span>
    </div>

    <div class="timeline-main">
      <div class="timeline-copy">
        <div class="timeline-title-row">
          <h3 class="timeline-title">{{ title || 'Untitled exam' }}</h3>
          <span
            v-if="status"
            class="timeline-status"
            :class="statusClass"
          >{{ status }}</span>
        </div>
        <div v-if="timeText || subtitle" class="timeline-meta">
          <span v-if="timeText" class="timeline-meta-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 7v5l3 2" />
            </svg>
            {{ timeText }}
          </span>
          <span v-if="subtitle" class="timeline-meta-item">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
              <path d="M12 21s7-5.2 7-11a7 7 0 10-14 0c0 5.8 7 11 7 11z" />
              <circle cx="12" cy="10" r="2.5" />
            </svg>
            {{ subtitle }}
          </span>
        </div>
      </div>
    </div>

    <div class="timeline-actions">
      <slot name="actions"></slot>
      <span class="timeline-chevron" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="m9 6 6 6-6 6" />
        </svg>
      </span>
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
  /** ISO / API datetime used for the left date block */
  dateIso: { type: [String, Date, null], default: null },
  /** Visual accent: blue | yellow | green | red | orange */
  tone: { type: String, default: '' },
  centerCopy: { type: Boolean, default: false },
  dateMonth: { type: String, default: '' },
  dateDay: { type: String, default: '' },
});

const resolvedParts = computed(() => {
  if (props.dateMonth && props.dateDay) {
    return { month: props.dateMonth, day: props.dateDay };
  }
  const raw = props.dateIso;
  const d = raw instanceof Date ? raw : (raw ? new Date(raw) : null);
  if (!d || Number.isNaN(d.getTime())) return { month: '—', day: '—' };
  return {
    month: d.toLocaleString('en-US', { month: 'short' }).toUpperCase(),
    day: String(d.getDate()).padStart(2, '0'),
  };
});

const dateMonth = computed(() => resolvedParts.value.month);
const dateDay = computed(() => resolvedParts.value.day);

const dateTitle = computed(() => {
  const raw = props.dateIso;
  const d = raw instanceof Date ? raw : (raw ? new Date(raw) : null);
  if (!d || Number.isNaN(d.getTime())) return props.timeText || '';
  return d.toLocaleString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
});

const toneClass = computed(() => {
  const explicit = String(props.tone || '').toLowerCase();
  if (['blue', 'yellow', 'green', 'red', 'orange', 'amber', 'rose', 'slate'].includes(explicit)) {
    return `tone-${explicit}`;
  }
  const status = String(props.status || '').toLowerCase();
  const cls = props.statusClass;
  const classStr = Array.isArray(cls)
    ? cls.join(' ')
    : (typeof cls === 'object' && cls ? Object.keys(cls).filter((k) => cls[k]).join(' ') : String(cls || ''));

  if (status.includes('terminated') || classStr.includes('badge-terminated')) return 'tone-red';
  if (status.includes('not taken') || classStr.includes('badge-not-taken')) return 'tone-orange';
  if (status.includes('done') || classStr.includes('badge-done')) return 'tone-green';
  if (status.includes('pending') || status.includes('not yet') || classStr.includes('badge-pending') || classStr.includes('badge-upcoming')) return 'tone-yellow';
  if (status.includes('ongoing') || status.includes('open') || classStr.includes('badge-active')) return 'tone-blue';
  return 'tone-blue';
});
</script>

<style scoped>
.timeline-row {
  --tone-soft: #e8f1ff;
  --tone-ink: #2f6fed;
  --tone-tag-bg: #e8f1ff;
  --tone-tag-fg: #2458d6;

  position: relative;
  display: grid;
  grid-template-columns: 3.4rem 1.35rem minmax(0, 1fr) auto;
  grid-template-areas: "date rail main actions";
  align-items: stretch;
  column-gap: 0.85rem;
  padding: 1.05rem 0.35rem 1.05rem 0;
  margin: 0;
  background: transparent;
  border: 0;
  border-bottom: 1px solid #eef1f6;
  border-radius: 0;
  box-shadow: none;
  transition: background 0.15s ease;
}
.timeline-row:last-child {
  border-bottom: 0;
}
.timeline-row:hover {
  background: rgba(248, 250, 252, 0.85);
}
.timeline-row.tone-blue {
  --tone-soft: #e8f1ff;
  --tone-ink: #2f6fed;
  --tone-tag-bg: #e8f1ff;
  --tone-tag-fg: #2458d6;
}
.timeline-row.tone-amber {
  --tone-soft: #fff4d6;
  --tone-ink: #d97706;
  --tone-tag-bg: #fff4d6;
  --tone-tag-fg: #b45309;
}
.timeline-row.tone-rose {
  --tone-soft: #ffe4e8;
  --tone-ink: #e11d48;
  --tone-tag-bg: #ffe4e8;
  --tone-tag-fg: #be123c;
}
.timeline-row.tone-slate {
  --tone-soft: #eef2f7;
  --tone-ink: #64748b;
  --tone-tag-bg: #eef2f7;
  --tone-tag-fg: #475569;
}
.timeline-row.tone-green { --tone-soft: #e8f5ee; --tone-ink: #15803d; --tone-tag-bg: #e8f5ee; --tone-tag-fg: #166534; }
.timeline-row.tone-red { --tone-soft: #feecec; --tone-ink: #dc2626; --tone-tag-bg: #feecec; --tone-tag-fg: #b91c1c; }
.timeline-row.tone-yellow { --tone-soft: #fff8d9; --tone-ink: #a16207; --tone-tag-bg: #fff8d9; --tone-tag-fg: #854d0e; }
.timeline-row.tone-orange { --tone-soft: #fff0df; --tone-ink: #c2410c; --tone-tag-bg: #fff0df; --tone-tag-fg: #9a3412; }

.timeline-date {
  grid-area: date;
  align-self: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.05rem;
  min-height: 3.35rem;
  padding: 0.4rem 0.35rem;
  border-radius: 12px;
  background: var(--tone-soft);
  color: var(--tone-ink);
}
.timeline-date-month {
  font-family: 'Poppins', sans-serif;
  font-size: 0.62rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  line-height: 1;
  opacity: 0.85;
}
.timeline-date-day {
  font-family: 'Poppins', sans-serif;
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.03em;
  line-height: 1.05;
}

.timeline-rail {
  grid-area: rail;
  position: relative;
  align-self: stretch;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
}
/* Full-height segment so adjacent rows form one continuous vertical line */
.timeline-rail::before {
  content: "";
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  width: 2px;
  transform: translateX(-50%);
  background: #e6ebf2;
}
.timeline-row:first-child .timeline-rail::before {
  top: 50%;
}
.timeline-row:last-child .timeline-rail::before {
  bottom: 50%;
}
.timeline-dot {
  position: relative;
  z-index: 1;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: var(--tone-ink);
  box-shadow: 0 0 0 4px #fff;
}

.timeline-main {
  grid-area: main;
  align-self: center;
  min-width: 0;
}
.timeline-copy {
  min-width: 0;
}
.timeline-title-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.4rem 0.55rem;
  margin-bottom: 0.35rem;
}
.timeline-title {
  margin: 0;
  font-family: 'Poppins', sans-serif;
  font-size: 0.98rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.3;
  color: #1e3a5f;
}
.timeline-status {
  display: inline-flex;
  align-items: center;
  font-size: 0.68rem !important;
  font-weight: 700 !important;
  letter-spacing: 0.02em;
  text-transform: none !important;
  padding: 0.22rem 0.6rem !important;
  border-radius: 999px !important;
  border: 0 !important;
  background: var(--tone-tag-bg) !important;
  color: var(--tone-tag-fg) !important;
}
.timeline-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 1rem;
}
.timeline-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 500;
  color: #8b97a8;
  line-height: 1.2;
}
.timeline-meta-item svg {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0.85;
}

.timeline-actions {
  grid-area: actions;
  align-self: center;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.4rem;
}
.timeline-chevron {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
  color: #c0c8d4;
}
.timeline-chevron svg {
  width: 16px;
  height: 16px;
}
.timeline-row:hover .timeline-chevron {
  color: #94a3b8;
}

@media (max-width: 720px) {
  .timeline-row {
    grid-template-columns: 3.1rem 1.1rem minmax(0, 1fr);
    grid-template-areas:
      "date rail main"
      "actions actions actions";
    row-gap: 0.65rem;
  }
  .timeline-actions {
    justify-content: flex-start;
    padding-left: 4.2rem;
  }
  .timeline-chevron {
    display: none;
  }
}
</style>
