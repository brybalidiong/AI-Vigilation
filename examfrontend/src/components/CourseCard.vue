<template>
  <article
    class="course-display-card"
    :class="folderClass"
    tabindex="0"
    role="button"
    @click="$emit('click')"
    @keydown.enter="$emit('click')"
    @keydown.space.prevent="$emit('click')"
  >
    <div class="course-banner" :style="photoStyle">
      <div class="course-badge">{{ code }}</div>
      <div v-if="!photo" class="banner-decor decor-1"></div>
      <div v-if="!photo" class="banner-decor decor-2"></div>
    </div>
    <div class="course-body">
      <h3 class="course-title">{{ name }}</h3>
      <div class="course-footer">
        <div class="course-stats">
          <span v-if="meta" class="course-stat">{{ meta }}</span>
          <span v-else class="course-stat">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
            {{ students }} {{ students === 1 ? 'student' : 'students' }}
          </span>
        </div>
        <span class="course-open-link">
          Open
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="15" height="15"><path d="M5 12h14"/><path d="M12 5l7 7-7 7"/></svg>
        </span>
      </div>
    </div>
  </article>
</template>

<script setup>
import { computed } from "vue";

const props = defineProps({
  folderClass: { type: String, default: "folder-1" },
  code: { type: String, default: "" },
  name: { type: String, default: "" },
  students: { type: Number, default: 0 },
  photo: { type: String, default: "" },
  // legacy prop — kept for backwards compatibility
  meta: { type: String, default: "" },
});
defineEmits(["click"]);

const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const photoStyle = computed(() => {
  if (!props.photo) return {};
  const url = props.photo.startsWith("http") ? props.photo : `${backendBaseUrl}${props.photo}`;
  return {
    backgroundImage: `url(${url})`,
    backgroundSize: "cover",
    backgroundPosition: "center",
  };
});
</script>

<style scoped>
.course-display-card {
  position: relative;
  border-radius: 17px;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.05);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease;
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 232px;
  outline: none;
}

.course-display-card:hover,
.course-display-card:focus-visible {
  transform: translateY(-5px);
  box-shadow: 0 18px 38px rgba(var(--dash-accent-rgb, 29, 52, 97), 0.14);
  border-color: rgba(var(--dash-accent-rgb, 29, 52, 97), 0.22);
}

.course-display-card:focus-visible {
  box-shadow: 0 0 0 3px rgba(29, 52, 97, 0.15), 0 18px 36px rgba(29, 52, 97, 0.13);
}

.course-banner {
  height: 116px;
  position: relative;
  padding: 1.15rem 1.25rem;
  overflow: hidden;
  display: flex;
  align-items: flex-start;
}

.folder-1 .course-banner { background: linear-gradient(135deg, #1D3461 0%, #2d4a7a 100%); }
.folder-2 .course-banner { background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%); }
.folder-3 .course-banner { background: linear-gradient(135deg, #7c3aed 0%, #a78bfa 100%); }
.folder-4 .course-banner { background: linear-gradient(135deg, #b45309 0%, #f59e0b 100%); }
.folder-5 .course-banner { background: linear-gradient(135deg, #be123c 0%, #fb7185 100%); }

.banner-decor {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
}
.decor-1 { width: 140px; height: 140px; top: -45px; right: -15px; }
.decor-2 { width: 85px; height: 85px; bottom: -25px; left: 35px; background: rgba(255, 255, 255, 0.18); }

.course-badge {
  position: relative;
  z-index: 1;
  background: #294a7a;
  border: 1px solid #6e87ad;
  color: #fff;
  padding: 0.4rem 0.85rem;
  border-radius: 9px;
  font-family: 'Poppins', sans-serif;
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
}

.course-body {
  padding: 1.35rem 1.45rem 1.45rem;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.course-title {
  font-family: 'Poppins', sans-serif;
  font-size: 1.22rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 1.15rem;
  line-height: 1.38;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.course-footer {
  margin-top: auto;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.course-stats { display: flex; flex-wrap: wrap; gap: 0.5rem; }

.course-stat {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #64748b;
  font-size: 0.88rem;
  font-weight: 500;
}

.course-open-link {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  font-family: 'Poppins', sans-serif;
  font-size: 0.88rem;
  font-weight: 700;
  color: var(--dash-accent, #1D3461);
  white-space: nowrap;
  transition: gap 0.2s ease;
}

.course-display-card:hover .course-open-link {
  gap: 0.5rem;
}
</style>
