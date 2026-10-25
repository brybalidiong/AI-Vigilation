<template>
  <div class="assignment-field">
    <span class="assignment-field__label">Assigned instructors</span>
    <details ref="picker" class="assignment-picker" :class="{ 'assignment-picker--disabled': disabled, 'assignment-picker--above': openAbove }" @toggle="positionPanel">
      <summary :aria-label="`${label}: ${summary}`" @click="disabled && $event.preventDefault()">
        <span class="assignment-picker__summary">{{ summary }}</span>
      </summary>
      <div class="assignment-picker__panel">
        <input
          v-model.trim="search"
          type="search"
          class="assignment-picker__search"
          :aria-label="`Search instructors for ${label}`"
          placeholder="Search name or email"
          :disabled="disabled"
        />
        <div class="assignment-picker__toolbar">
          <span>{{ filteredInstructors.length }} of {{ instructors.length }} shown</span>
          <button type="button" :disabled="disabled || !filteredInstructors.length" @click="selectShown">Select shown</button>
        </div>
        <div class="assignment-picker__list" role="group" :aria-label="`Instructors for ${label}`">
          <label v-for="instructor in filteredInstructors" :key="instructor.id" class="assignment-picker__option">
            <input type="checkbox" :checked="modelValue.includes(instructor.id)" :disabled="disabled" @change="toggle(instructor.id)" />
            <span class="assignment-picker__person"><strong>{{ instructor.full_name || instructor.email }}</strong><small>{{ instructor.email }}</small></span>
            <span v-if="!instructor.is_active" class="assignment-picker__status">Inactive</span>
          </label>
          <p v-if="!filteredInstructors.length" class="assignment-picker__empty">No matching instructors.</p>
        </div>
      </div>
    </details>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';

const props = defineProps({
  instructors: { type: Array, required: true },
  modelValue: { type: Array, required: true },
  label: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);
const picker = ref(null);
const search = ref('');
const openAbove = ref(false);
const summary = computed(() => {
  if (!props.modelValue.length) return props.disabled ? 'Choose a course group first' : 'Select instructors';
  const first = props.instructors.find((instructor) => instructor.id === props.modelValue[0]);
  const name = first?.full_name || first?.email || 'Instructor';
  return props.modelValue.length === 1 ? name : `${name} +${props.modelValue.length - 1}`;
});
const filteredInstructors = computed(() => {
  const query = search.value.toLowerCase();
  const matches = props.instructors.filter((instructor) => !query ||
    `${instructor.full_name || ''} ${instructor.email || ''}`.toLowerCase().includes(query));
  return query ? matches : matches.sort((a, b) =>
    Number(props.modelValue.includes(b.id)) - Number(props.modelValue.includes(a.id)));
});
function toggle(id) {
  const next = props.modelValue.includes(id)
    ? props.modelValue.filter((value) => value !== id)
    : [...props.modelValue, id];
  emit('update:modelValue', next);
}
function selectShown() {
  const next = [...props.modelValue];
  for (const instructor of filteredInstructors.value) {
    if (instructor.is_active && !next.includes(instructor.id)) next.push(instructor.id);
  }
  emit('update:modelValue', next);
}
function closeOnOutsideClick(event) {
  if (picker.value?.open && !picker.value.contains(event.target)) picker.value.open = false;
}
async function positionPanel() {
  if (!picker.value?.open) return;
  await nextTick();
  const panel = picker.value?.querySelector('.assignment-picker__panel');
  if (!panel) return;
  const bounds = picker.value.getBoundingClientRect();
  const below = window.innerHeight - bounds.bottom;
  openAbove.value = below < panel.offsetHeight + 12 && bounds.top > below;
}
onMounted(() => document.addEventListener('pointerdown', closeOnOutsideClick));
onUnmounted(() => document.removeEventListener('pointerdown', closeOnOutsideClick));
</script>

<style scoped>
.assignment-field { display: grid; gap: .25rem; min-width: 0; }
.assignment-field__label { color: #6a788d; font-size: .68rem; font-weight: 700; }
.assignment-picker { position: relative; min-width: 0; }
.assignment-picker summary { display: flex; align-items: center; min-height: 41px; padding: .55rem 2.65rem .55rem .85rem; border: 1px solid #d5dfeb; border-radius: 10px; background-color: #fff; background-image: var(--select-chevron); background-repeat: no-repeat; background-position: right .95rem center; background-size: .95rem; color: #334155; font: inherit; font-size: .75rem; cursor: pointer; list-style: none; }
.assignment-picker summary::-webkit-details-marker { display: none; }
.assignment-picker summary:focus, .assignment-picker__search:focus-visible { border-color: #1d3461; outline: 3px solid rgba(29, 52, 97, .14); }
.assignment-picker__summary { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.assignment-picker--disabled summary { background-color: #f4f6fa; color: #8895a8; cursor: default; }
.assignment-picker__panel { position: absolute; z-index: 30; top: calc(100% + .35rem); right: 0; width: max(100%, 18rem); padding: .65rem; border: 1px solid #d8e1ee; border-radius: 12px; background: #fff; box-shadow: 0 12px 30px rgba(24, 43, 74, .16); }
.assignment-picker--above .assignment-picker__panel { top: auto; bottom: calc(100% + .35rem); }
.assignment-picker__search { width: 100%; height: 38px; padding: .5rem .7rem; border: 1px solid #d8e1ee; border-radius: 8px; background: #fff; color: #203553; font: inherit; font-size: .75rem; }
.assignment-picker__toolbar { display: flex; align-items: center; justify-content: space-between; gap: .5rem; padding: .5rem .1rem .35rem; color: #7b899d; font-size: .7rem; }
.assignment-picker__toolbar button { padding: .1rem 0; border: 0; background: transparent; color: #28548e; font: inherit; font-weight: 700; cursor: pointer; }
.assignment-picker__toolbar button:disabled { color: #9aa6b7; cursor: default; }
.assignment-picker__list { max-height: 13rem; overflow-y: auto; border-top: 1px solid #edf1f6; }
.assignment-picker__option { display: flex; align-items: center; gap: .55rem; min-height: 2.8rem; padding: .35rem .25rem; color: #203553; cursor: pointer; }
.assignment-picker__option + .assignment-picker__option { border-top: 1px solid #f0f3f7; }
.assignment-picker__option input { flex: none; accent-color: #1d3461; }
.assignment-picker__person { display: grid; min-width: 0; line-height: 1.25; }
.assignment-picker__person strong, .assignment-picker__person small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.assignment-picker__person strong { font-size: .74rem; font-weight: 700; }
.assignment-picker__person small { color: #7b899d; font-size: .67rem; font-weight: 400; }
.assignment-picker__status { margin-left: auto; color: #9a5b16; font-size: .66rem; font-weight: 700; }
.assignment-picker__empty { margin: 0; padding: .8rem .2rem; color: #7b899d; font-size: .73rem; }
@media (max-width: 620px) { .assignment-picker__panel { left: 0; right: auto; width: min(19rem, calc(100vw - 3rem)); } }
</style>
