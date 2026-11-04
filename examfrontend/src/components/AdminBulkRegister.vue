<template>
  <div class="bulk-register">
    <p class="bulk-register__hint">Add {{ role === 'student' ? 'students' : 'instructors' }} from school emails. Names follow <strong>surname.givenname@{{ schoolDomain }}</strong>. Preview the names before registering.</p>
    <label class="bulk-register__field">Institute
      <select v-model="institute" @change="clearPreview">
        <option value="" disabled>Select institute</option>
        <option v-for="item in institutes" :key="item.code" :value="item.code">{{ item.code }} — {{ item.name }}</option>
      </select>
    </label>
    <div class="bulk-register__sources">
      <label class="bulk-register__field">Paste school emails
        <textarea v-model="emails" rows="5" :placeholder="`reyes.alex@${schoolDomain}\nsantos.maria@${schoolDomain}`" @input="onPasteInput" />
      </label>
      <label class="bulk-register__field">Or upload an Excel attendance file (.xlsx)
        <input :key="fileInputKey" type="file" accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" @change="onFileChange" />
        <small>Emails may be in any worksheet or column. Up to 500 addresses per batch.</small>
      </label>
    </div>
    <div class="bulk-register__actions">
      <button type="button" class="bulk-register__button" :disabled="busy || !institute || (!emails.trim() && !file)" @click="preview">{{ busy && !rows.length ? 'Reading…' : 'Preview batch' }}</button>
      <button type="button" class="bulk-register__button bulk-register__button--primary" :disabled="busy || !readyCount" @click="save">{{ busy && rows.length ? 'Registering…' : `Register ${readyCount} ${role === 'student' ? 'students' : 'instructors'}` }}</button>
    </div>
    <p v-if="error" class="bulk-register__error" role="alert">{{ error }}</p>
    <template v-if="rows.length">
      <p class="bulk-register__summary" role="status">{{ batchSummary }}</p>
      <div class="bulk-register__table-wrap">
        <table class="bulk-register__table">
          <thead><tr><th>Email</th><th>First name</th><th>Last name</th><th>Status</th></tr></thead>
          <tbody>
            <tr v-for="(row, index) in rows" :key="`${row.email}-${index}`">
              <td>{{ row.email }}</td><td>{{ row.first_name || '—' }}</td><td>{{ row.last_name || '—' }}</td>
              <td><span class="bulk-register__status" :class="`bulk-register__status--${row.status}`">{{ statusLabel(row.status) }}</span><small v-if="row.reason">{{ row.reason }}</small></td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import axios from 'axios';

const props = defineProps({
  role: { type: String, required: true },
  institutes: { type: Array, required: true },
  schoolDomain: { type: String, required: true },
});
const emit = defineEmits(['saved']);
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';
const institute = ref('');
const emails = ref('');
const file = ref(null);
const fileInputKey = ref(0);
const rows = ref([]);
const error = ref('');
const busy = ref(false);
const readyCount = computed(() => rows.value.filter(row => row.status === 'ready' || row.status === 'restore').length);
const batchSummary = computed(() => {
  const registered = rows.value.filter(row => row.status === 'created' || row.status === 'restored').length;
  const skipped = rows.value.length - readyCount.value - registered;
  return registered
    ? `${registered} registered or restored · ${skipped} skipped or needing attention`
    : `${readyCount.value} ready · ${skipped} skipped or needing attention`;
});

function clearPreview() { rows.value = []; error.value = ''; }
function onPasteInput() {
  file.value = null;
  fileInputKey.value += 1;
  clearPreview();
}
function onFileChange(event) {
  file.value = event.target.files?.[0] || null;
  if (file.value) emails.value = '';
  clearPreview();
}
function payload(isPreview) {
  const data = new FormData();
  data.append('role', props.role);
  data.append('institute', institute.value);
  data.append('preview', String(isPreview));
  if (file.value) data.append('file', file.value);
  else data.append('emails', emails.value);
  return data;
}
async function submit(isPreview) {
  busy.value = true;
  error.value = '';
  try {
    const token = localStorage.getItem('access_token');
    const { data } = await axios.post(`${backendBaseUrl}/api/admin/bulk-register/`, payload(isPreview), {
      headers: { Authorization: `Bearer ${token}` },
    });
    rows.value = data.rows || [];
    if (!isPreview) emit('saved', data);
  } catch (err) {
    error.value = err?.response?.data?.error || 'Could not process this batch.';
  } finally {
    busy.value = false;
  }
}
function preview() { submit(true); }
function save() { if (readyCount.value) submit(false); }
function statusLabel(status) {
  return ({ ready: 'Ready', restore: 'Restore access', created: 'Registered', restored: 'Restored',
    existing: 'Already registered', duplicate: 'Duplicate', invalid: 'Invalid', conflict: 'Role conflict' })[status] || status;
}
</script>

<style scoped>
.bulk-register { display: grid; gap: 1rem; }
.bulk-register__hint { margin: 0; color: #596b83; font-size: .84rem; line-height: 1.5; }
.bulk-register__hint strong { color: #1d3461; }
.bulk-register__field { display: grid; gap: .4rem; color: #475569; font-size: .78rem; font-weight: 700; }
.bulk-register__field select, .bulk-register__field textarea, .bulk-register__field input { width: 100%; min-height: 43px; border: 1px solid #d5dfeb; border-radius: 9px; padding: .6rem .75rem; background: #fff; color: #142849; font: inherit; font-size: .84rem; }
.bulk-register__field select { appearance: none; padding-right: 2.65rem; background-image: var(--select-chevron); background-repeat: no-repeat; background-position: right .95rem center; background-size: .95rem; }
.bulk-register__field textarea { resize: vertical; }
.bulk-register__field select:focus, .bulk-register__field textarea:focus, .bulk-register__field input:focus { border-color: #1d3461; outline: 3px solid rgba(29, 52, 97, .14); }
.bulk-register__field small { color: #697b94; font-weight: 500; }
.bulk-register__sources { display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 1rem; }
.bulk-register__actions { display: flex; flex-wrap: wrap; gap: .6rem; }
.bulk-register__button { border: 1px solid #cbd7e7; border-radius: 9px; padding: .62rem .9rem; background: #fff; color: #1d3461; font: inherit; font-size: .82rem; font-weight: 700; cursor: pointer; }
.bulk-register__button--primary { border-color: #1d3461; background: #1d3461; color: #fff; }
.bulk-register__button:disabled { opacity: .48; cursor: not-allowed; }
.bulk-register__error { margin: 0; color: #b91c1c; font-size: .82rem; }
.bulk-register__summary { margin: 0; color: #425a79; font-size: .8rem; font-weight: 700; }
.bulk-register__table-wrap { max-height: 340px; overflow: auto; border: 1px solid #e0e7f1; border-radius: 10px; }
.bulk-register__table { width: 100%; border-collapse: collapse; text-align: left; font-size: .78rem; }
.bulk-register__table th { position: sticky; top: 0; background: #f1f5fa; color: #526984; }
.bulk-register__table th, .bulk-register__table td { padding: .65rem .75rem; border-bottom: 1px solid #e8edf4; }
.bulk-register__table td { color: #263b59; overflow-wrap: anywhere; }
.bulk-register__table td small { display: block; margin-top: .25rem; color: #687b92; }
.bulk-register__status { font-weight: 700; color: #1d3461; }
.bulk-register__status--invalid, .bulk-register__status--conflict { color: #b91c1c; }
.bulk-register__status--created, .bulk-register__status--restored { color: #147d52; }
@media (max-width: 700px) { .bulk-register__sources { grid-template-columns: 1fr; } }
</style>
