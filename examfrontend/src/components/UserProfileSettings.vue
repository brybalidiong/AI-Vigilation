<template>
  <div class="profile-page">

    <!-- ── Hero Banner ─────────────────────────────────────────── -->
    <div class="profile-hero">
      <div class="hero-body">
        <!-- Avatar -->
        <div class="avatar-wrap" :class="{ editable: isEditing }" @click="triggerFileInput">
          <div class="avatar-ring">
            <img v-if="previewPhotoUrl" :src="previewPhotoUrl" alt="Profile photo" class="avatar-img" />
            <div v-else class="avatar-initials">{{ initials }}</div>
          </div>
          <div class="avatar-edit-overlay" v-if="isEditing">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
              <polyline points="17 8 12 3 7 8"/>
              <line x1="12" y1="3" x2="12" y2="15"/>
            </svg>
            <span>Upload Photo</span>
          </div>
          <input type="file" ref="fileInput" accept="image/*" class="file-hidden" @change="onFileChange" :disabled="!isEditing" />
          <div class="avatar-status-dot"></div>
        </div>

        <!-- Name + meta -->
        <div class="hero-info">
          <h1 class="hero-name">{{ displayName }}</h1>
          <div class="hero-meta">
            <span class="role-chip">{{ formattedRole }}</span>
            <span class="email-chip">{{ user.email }}</span>
          </div>
        </div>

        <!-- Actions -->
        <div class="hero-actions">
          <button v-if="!isEditing" class="btn-edit-hero" @click="startEditing">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
            Edit Profile
          </button>
          <div v-else class="hero-edit-actions">
            <button class="btn-cancel-hero" @click="cancelEditing" :disabled="loading">Discard</button>
            <button class="btn-save-hero" @click="saveProfile" :disabled="loading">
              <span v-if="loading" class="btn-spinner"></span>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
              {{ loading ? 'Saving…' : 'Save Changes' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Cards Grid ──────────────────────────────────────────── -->
    <div class="cards-grid">

      <!-- Face ID Photo (spans full width) -->
      <div v-if="user.role !== 'instructor'" class="info-card face-id-card" style="grid-column: 1 / -1;">
        <div class="card-header">
          <div class="card-header-icon icon-indigo">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
              <path d="M8 21h8M12 17v4"/>
            </svg>
          </div>
          <div class="card-header-text">
            <h2 class="card-title">Face ID Photo</h2>
            <p class="card-subtitle">Upload a clear 2×2 or formal ID photo for exam identity verification.</p>
          </div>
          <!-- Status badge -->
          <div v-if="faceStatus === 'approved'" class="fid-badge fid-badge--registered">
            <span class="fid-dot fid-dot--green"></span> Approved
          </div>
          <div v-else-if="faceStatus === 'pending'" class="fid-badge fid-badge--pending">
            <span class="fid-dot fid-dot--blue"></span> Pending Approval
          </div>
          <div v-else-if="!faceStatus || faceStatus === 'none'" class="fid-badge fid-badge--required">
            <span class="fid-dot fid-dot--amber"></span> Required
          </div>
        </div>

        <div class="fid-body">

          <!-- ── APPROVED & LOCKED ──────────────────────────────────── -->
          <div v-if="faceStatus === 'approved' && !faceReuploadAllowed" class="fid-locked-wrap">
            <div class="fid-locked-photo">
              <img v-if="facePreviewUrl" :src="facePreviewUrl" alt="Approved face photo" class="fid-preview-img" />
              <div v-else class="fid-preview-placeholder">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.35">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div class="fid-locked-overlay">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                  <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <span>Locked</span>
              </div>
            </div>
            <div class="fid-guidelines">
              <p class="fid-guide-title">✅ Photo Approved</p>
              <p class="fid-locked-note">Your face photo has been verified and locked by the admin. Contact your administrator if you need to update it.</p>
            </div>
          </div>

          <!-- ── PENDING APPROVAL ───────────────────────────────────── -->
          <div v-else-if="faceStatus === 'pending'" class="fid-locked-wrap">
            <div class="fid-locked-photo fid-locked-photo--pending">
              <img v-if="facePreviewUrl" :src="facePreviewUrl" alt="Pending face photo" class="fid-preview-img" />
              <div v-else class="fid-preview-placeholder">
                <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.35">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div class="fid-locked-overlay fid-locked-overlay--pending">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                </svg>
                <span>Reviewing…</span>
              </div>
            </div>
            <div class="fid-guidelines">
              <p class="fid-guide-title">⏳ Awaiting Admin Review</p>
              <p class="fid-locked-note">Your photo has been submitted and is waiting for the administrator to approve it. You will be able to take exams once it is approved.</p>
            </div>
          </div>

          <!-- ── UPLOAD (none or reupload allowed) ─────────────────── -->
          <template v-else>
          <!-- Preview area -->
          <div class="fid-preview-wrap" @click="triggerFaceFileInput" id="face-photo-upload-zone">
            <img v-if="facePreviewUrl" :src="facePreviewUrl" alt="Face photo preview" class="fid-preview-img" />
            <div v-else class="fid-preview-placeholder">
              <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.35">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <span>Click to upload photo</span>
            </div>
            <div class="fid-preview-overlay">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              <span>{{ facePreviewUrl ? 'Change Photo' : 'Upload Photo' }}</span>
            </div>
            <input
              ref="faceFileInput"
              type="file"
              accept="image/jpeg,image/png,image/webp"
              class="file-hidden"
              @change="onFaceFileChange"
            />
          </div>

          <!-- Guidelines -->
          <div class="fid-guidelines">
            <p class="fid-guide-title">Photo Requirements</p>
            <ul class="fid-guide-list">
              <li>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Clear, front-facing photo — face fully visible
              </li>
              <li>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                Good lighting, no shadows on face
              </li>
              <li>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                2×2 ID or formal photo recommended
              </li>
              <li>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                No glasses, hats, or heavy filters
              </li>
            </ul>

            <p v-if="faceUploadError || faceError" class="fid-error">
              ⚠️ {{ faceUploadError || faceError }}
            </p>

            <!-- Standalone save button when a file is selected -->
            <div v-if="newFaceFile" class="fid-save-row">
              <p class="fid-pending-note">
                📎 <strong>{{ newFaceFile.name }}</strong>
              </p>
              <button
                class="fid-save-btn"
                :disabled="loading"
                @click="saveFacePhoto"
                id="save-face-photo-btn"
              >
                <span v-if="loading" class="fid-spinner"></span>
                <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                {{ loading ? 'Saving…' : 'Save Face Photo' }}
              </button>
            </div>
          </div>
          </template>
        </div>
      </div>

      <!-- Personal Information -->
      <div class="info-card" :class="{ editing: isEditing }">
        <div class="card-header">
          <div class="card-header-icon">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
              <circle cx="12" cy="7" r="4"/>
            </svg>
          </div>
          <div class="card-header-text">
            <h2 class="card-title">Personal Information</h2>
            <p class="card-subtitle">{{ isEditing ? 'Update your details below.' : 'Your personal data is securely stored.' }}</p>
          </div>
          <div v-if="isEditing" class="edit-badge">
            <span class="edit-dot"></span> Editing
          </div>
        </div>

        <div class="form-grid">
          <div class="field-wrap">
            <label class="field-label">First Name</label>
            <div class="field-box" :class="{ locked: !isEditing }">
              <input type="text" v-model="form.first_name" :readonly="!isEditing" placeholder="Enter first name" />
            </div>
          </div>

          <div class="field-wrap">
            <label class="field-label">Last Name</label>
            <div class="field-box" :class="{ locked: !isEditing }">
              <input type="text" v-model="form.last_name" :readonly="!isEditing" placeholder="Enter last name" />
            </div>
          </div>

          <div class="field-wrap">
            <label class="field-label">Mobile Number</label>
            <div class="field-box" :class="{ locked: !isEditing }">
              <input type="tel" v-model="form.mobile_number" :readonly="!isEditing" placeholder="Add mobile number" />
            </div>
          </div>

          <div class="field-wrap">
            <label class="field-label">
              Email Address
              <span class="field-tag">Permanent</span>
            </label>
            <div class="field-box locked permanent">
              <input type="email" :value="user.email" readonly />
              <svg class="lock-icon" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
            </div>
          </div>
        </div>
      </div>

      <!-- Account Overview -->
      <div class="info-card">
        <div class="card-header">
          <div class="card-header-icon icon-gold">
            <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
              <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <div class="card-header-text">
            <h2 class="card-title">Account Overview</h2>
            <p class="card-subtitle">Security and account details.</p>
          </div>
        </div>

        <div class="overview-list">
          <div class="overview-row">
            <div class="ov-icon ov-blue">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <span class="ov-label">Account Role</span>
            <span class="ov-value">{{ formattedRole }}</span>
          </div>
          <div class="overview-row">
            <div class="ov-icon ov-green">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            </div>
            <span class="ov-label">Account Status</span>
            <span class="ov-value ov-active">
              <span class="active-dot"></span>Active
            </span>
          </div>

          <div class="overview-row">
            <div class="ov-icon ov-slate">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            </div>
            <span class="ov-label">Data Security</span>
            <span class="ov-value">End-to-end encrypted</span>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Toast Notifications ──────────────────────────────────── -->
    <teleport to="body">
      <div class="toast-stack">
        <transition name="toast-slide">
          <div v-if="errorMsg" class="toast toast-error" role="alert">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            <div class="toast-body">
              <strong>Error</strong>
              <span>{{ errorMsg }}</span>
            </div>
          </div>
        </transition>
        <transition name="toast-slide">
          <div v-if="successMsg" class="toast toast-success" role="status">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <div class="toast-body">
              <strong>Saved</strong>
              <span>{{ successMsg }}</span>
            </div>
          </div>
        </transition>
      </div>
    </teleport>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  user:                { type: Object,  required: true },
  loading:             { type: Boolean, default: false },
  errorMsg:            { type: String,  default: '' },
  successMsg:          { type: String,  default: '' },
  faceRegistered:      { type: Boolean, default: false },
  facePhotoUrl:        { type: String,  default: '' },
  faceError:           { type: String,  default: '' },
  faceStatus:          { type: String,  default: 'none' },
  faceReuploadAllowed: { type: Boolean, default: false },
});

const emit = defineEmits(['save-profile']);

const isEditing       = ref(false);
const fileInput       = ref(null);
const newPhotoFile    = ref(null);
const previewPhotoUrl = ref('');
const form = ref({ first_name: '', last_name: '', mobile_number: '' });

// Face photo state
const faceFileInput   = ref(null);
const newFaceFile     = ref(null);
const facePreviewUrl  = ref('');
const faceUploadError = ref('');

watch(() => props.user, (v) => {
  if (!isEditing.value && v) resetForm();
}, { immediate: true, deep: true });

function resetForm() {
  form.value = {
    first_name:    props.user.first_name    || '',
    last_name:     props.user.last_name     || '',
    mobile_number: props.user.mobile_number || '',
  };
  newPhotoFile.value    = null;
  previewPhotoUrl.value = props.user.photo  || '';
  newFaceFile.value     = null;
  // Show pending photo if awaiting review, else show approved photo
  facePreviewUrl.value  = (props.faceStatus === 'pending' ? props.user.face_pending_photo_url : null)
                          || props.facePhotoUrl
                          || '';
  faceUploadError.value = '';
}

const initials = computed(() => {
  const f = (props.user.first_name || '').trim();
  const l = (props.user.last_name  || '').trim();
  if (f && l) return `${f[0]}${l[0]}`.toUpperCase();
  if (f)      return f[0].toUpperCase();
  return 'U';
});

const displayName = computed(() => {
  return [props.user.first_name, props.user.last_name].filter(Boolean).join(' ') || 'User';
});

const formattedRole = computed(() => {
  if (!props.user.role) return 'User';
  return props.user.role.charAt(0).toUpperCase() + props.user.role.slice(1);
});

function startEditing()  { isEditing.value = true; }
function cancelEditing() { isEditing.value = false; resetForm(); }

function triggerFileInput() {
  if (isEditing.value && fileInput.value) fileInput.value.click();
}

function onFileChange(e) {
  const file = e.target.files[0];
  if (file) {
    newPhotoFile.value    = file;
    previewPhotoUrl.value = URL.createObjectURL(file);
  }
}

function saveProfile() {
  const fd = new FormData();
  fd.append('first_name',    form.value.first_name);
  fd.append('last_name',     form.value.last_name);
  fd.append('mobile_number', form.value.mobile_number);
  if (newPhotoFile.value) fd.append('custom_photo', newPhotoFile.value);
  if (newFaceFile.value)  fd.append('face_photo',   newFaceFile.value);
  emit('save-profile', fd);
}

function triggerFaceFileInput() {
  faceFileInput.value?.click();
}

function onFaceFileChange(e) {
  faceUploadError.value = '';
  const file = e.target.files[0];
  if (!file) return;
  // Basic validation: must be image
  if (!file.type.startsWith('image/')) {
    faceUploadError.value = 'Please upload an image file (JPG, PNG, etc.)';
    return;
  }
  // Warn if file is too large (> 5 MB)
  if (file.size > 5 * 1024 * 1024) {
    faceUploadError.value = 'File is too large. Please upload an image under 5 MB.';
    return;
  }
  newFaceFile.value    = file;
  facePreviewUrl.value = URL.createObjectURL(file);
}

watch(() => props.successMsg, (v) => {
  if (v) {
    if (isEditing.value) isEditing.value = false;
    // Clear pending face file so the button disappears and badge updates
    newFaceFile.value = null;
    faceUploadError.value = '';
  }
});


/** Saves only the face photo without entering Edit Profile mode. */
function saveFacePhoto() {
  if (!newFaceFile.value) return;
  const fd = new FormData();
  fd.append('first_name',    props.user.first_name    || '');
  fd.append('last_name',     props.user.last_name     || '');
  fd.append('mobile_number', props.user.mobile_number || '');
  fd.append('face_photo', newFaceFile.value);
  emit('save-profile', fd);
}
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@700;800;900&family=Inter:wght@400;500;600;700&display=swap');

/* ─── Root ──────────────────────────────────────────────── */
.profile-page {
  max-width: 1080px;
  width: 100%;
  margin: 0 auto;
  padding-bottom: 5rem;
  font-family: 'Inter', sans-serif;
}

/* ─── Hero ──────────────────────────────────────────────── */
.profile-hero {
  background: #1D3461;
  border-radius: 20px;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.hero-body {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 2.25rem 2.5rem;
}

/* ─── Avatar ─────────────────────────────────────────────── */
.avatar-wrap {
  position: relative;
  flex-shrink: 0;
  cursor: default;
}
.avatar-wrap.editable { cursor: pointer; }

.avatar-ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 4px solid rgba(255,255,255,0.25);
  overflow: hidden;
  background: #162a4f;
  transition: border-color 0.2s ease;
}
.avatar-wrap.editable:hover .avatar-ring {
  border-color: rgba(255,255,255,0.6);
}

.avatar-img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}

.avatar-initials {
  width: 100%; height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Outfit', sans-serif;
  font-size: 2.8rem;
  font-weight: 900;
  color: #fff;
}

.avatar-edit-overlay {
  position: absolute;
  inset: 4px;
  border-radius: 50%;
  background: rgba(0,0,0,0.55);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.avatar-wrap.editable:hover .avatar-edit-overlay { opacity: 1; }

.file-hidden { display: none; }

.avatar-status-dot {
  position: absolute;
  bottom: 6px; right: 6px;
  width: 15px; height: 15px;
  border-radius: 50%;
  background: #22c55e;
  border: 3px solid #1D3461;
}

/* ─── Hero Info ──────────────────────────────────────────── */
.hero-info { flex: 1; min-width: 0; }

.hero-name {
  font-family: 'Outfit', sans-serif;
  font-size: 2.1rem;
  font-weight: 900;
  color: #fff;
  margin: 0 0 0.65rem;
  letter-spacing: -0.02em;
  line-height: 1;
}

.hero-meta {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.role-chip {
  padding: 0.3rem 0.85rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 700;
  background: #fff;
  color: #1D3461;
  letter-spacing: 0.02em;
}

.email-chip {
  padding: 0.3rem 0.85rem;
  border-radius: 6px;
  font-size: 0.78rem;
  font-weight: 500;
  background: rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.8);
  border: 1px solid rgba(255,255,255,0.18);
}

/* ─── Hero Buttons ───────────────────────────────────────── */
.hero-actions { flex-shrink: 0; }

.btn-edit-hero {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.65rem 1.4rem;
  border-radius: 10px;
  background: rgba(255,255,255,0.14);
  color: #fff;
  border: 1px solid rgba(255,255,255,0.28);
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.18s ease, border-color 0.18s ease;
}
.btn-edit-hero:hover {
  background: rgba(255,255,255,0.22);
  border-color: rgba(255,255,255,0.45);
}

.hero-edit-actions {
  display: flex;
  gap: 0.6rem;
}

.btn-cancel-hero {
  padding: 0.65rem 1.2rem;
  border-radius: 10px;
  background: transparent;
  color: rgba(255,255,255,0.75);
  border: 1px solid rgba(255,255,255,0.22);
  font-family: 'Inter', sans-serif;
  font-weight: 600;
  font-size: 0.9rem;
  cursor: pointer;
  transition: color 0.18s ease, border-color 0.18s ease;
}
.btn-cancel-hero:hover:not(:disabled) {
  color: #fff;
  border-color: rgba(255,255,255,0.45);
}
.btn-cancel-hero:disabled { opacity: 0.45; cursor: not-allowed; }

.btn-save-hero {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.65rem 1.4rem;
  border-radius: 10px;
  background: #fff;
  color: #1D3461;
  border: none;
  font-family: 'Inter', sans-serif;
  font-weight: 700;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease;
}
.btn-save-hero:hover:not(:disabled) {
  background: #f0f4f8;
}
.btn-save-hero:disabled { opacity: 0.55; cursor: not-allowed; }

.btn-spinner {
  width: 13px; height: 13px;
  border: 2px solid rgba(29,52,97,0.2);
  border-top-color: #1D3461;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ─── Cards Grid ─────────────────────────────────────────── */
.cards-grid {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 1.25rem;
  align-items: start;
}

.info-card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid #e8eaed;
}
.info-card.editing {
  border-color: #1D3461;
}

/* ─── Card Header ────────────────────────────────────────── */
.card-header {
  display: flex;
  align-items: center;
  gap: 0.9rem;
  padding: 1.35rem 1.5rem;
  border-bottom: 1px solid #f0f2f5;
}

.card-header-icon {
  width: 36px; height: 36px;
  border-radius: 8px;
  background: #eef2f7;
  color: #1D3461;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.icon-gold { background: #fef9ec; color: #b45309; }

.card-header-text { flex: 1; min-width: 0; }

.card-title {
  font-family: 'Outfit', sans-serif;
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.08rem;
}
.card-subtitle {
  font-size: 0.8rem;
  color: #94a3b8;
  margin: 0;
}

.edit-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.25rem 0.7rem;
  border-radius: 6px;
  background: #eef2f7;
  color: #1D3461;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.03em;
  flex-shrink: 0;
}
.edit-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #1D3461;
  animation: blink 1.2s ease-in-out infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50%       { opacity: 0.3; }
}

/* ─── Form ───────────────────────────────────────────────── */
.form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.35rem;
  padding: 1.5rem;
}

.field-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.45rem;
}

.field-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 0.45rem;
}

.field-tag {
  background: #f1f5f9;
  color: #94a3b8;
  padding: 0.1rem 0.45rem;
  border-radius: 4px;
  font-size: 0.68rem;
  font-weight: 600;
  letter-spacing: 0.04em;
}

.field-box {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  height: 46px;
  padding: 0 0.9rem;
  border-radius: 10px;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  transition: border-color 0.18s ease;
}
.field-box:focus-within { border-color: #1D3461; }
.field-box.locked {
  background: #f8fafc;
  border-color: #f1f5f9;
}
.field-box.permanent {
  background: #f1f5f9;
  border-color: transparent;
}

.field-box input {
  flex: 1;
  border: none;
  background: transparent;
  font-family: 'Inter', sans-serif;
  font-size: 0.92rem;
  color: #0f172a;
  outline: none;
  min-width: 0;
}
.field-box.locked input { color: #64748b; }
.field-box input::placeholder { color: #cbd5e1; }

.lock-icon { color: #cbd5e1; flex-shrink: 0; }

/* ─── Account Overview ───────────────────────────────────── */
.overview-list {
  display: flex;
  flex-direction: column;
  padding: 0.4rem 0 1rem;
}

.overview-row {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.8rem 1.5rem;
  border-bottom: 1px solid #f8fafc;
}
.overview-row:last-child { border-bottom: none; }

.ov-icon {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.ov-blue   { background: #eff6ff; color: #1D3461; }
.ov-green  { background: #f0fdf4; color: #16a34a; }
.ov-purple { background: #f5f3ff; color: #6d28d9; }
.ov-slate  { background: #f8fafc; color: #475569; }

.ov-label {
  flex: 1;
  font-size: 0.82rem;
  color: #94a3b8;
  font-weight: 500;
}

.ov-value {
  font-size: 0.88rem;
  color: #0f172a;
  font-weight: 600;
  text-align: right;
}

.ov-active {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #16a34a !important;
}

.active-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  background: #22c55e;
  animation: blink 1.5s ease-in-out infinite;
}

/* ─── Toasts ─────────────────────────────────────────────── */
.toast-stack {
  position: fixed;
  bottom: 2rem;
  right: 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  z-index: 99999;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.9rem 1.1rem;
  border-radius: 12px;
  min-width: 260px;
  max-width: 340px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  border-left: 4px solid transparent;
}

.toast-error {
  background: #fff5f5;
  color: #991b1b;
  border-left-color: #ef4444;
}
.toast-success {
  background: #f0fdf4;
  color: #14532d;
  border-left-color: #22c55e;
}

.toast-body {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.toast-body strong { font-size: 0.87rem; font-weight: 700; }
.toast-body span   { font-size: 0.8rem; opacity: 0.8; }

.toast-slide-enter-active { transition: all 0.28s cubic-bezier(0.34,1.56,0.64,1); }
.toast-slide-leave-active { transition: all 0.18s ease-in; }
.toast-slide-enter-from   { opacity: 0; transform: translateX(30px); }
.toast-slide-leave-to     { opacity: 0; transform: translateY(8px); }

/* ─── Responsive ─────────────────────────────────────────── */
@media (max-width: 860px) {
  .cards-grid { grid-template-columns: 1fr; }
}

@media (max-width: 620px) {
  .hero-body { flex-direction: column; align-items: flex-start; gap: 1.25rem; padding: 1.75rem 1.5rem; }
  .hero-name { font-size: 1.7rem; }
  .hero-actions { width: 100%; }
  .btn-edit-hero { width: 100%; justify-content: center; }
  .hero-edit-actions { width: 100%; }
  .btn-cancel-hero, .btn-save-hero { flex: 1; justify-content: center; }
  .form-grid { grid-template-columns: 1fr; }
  .avatar-ring { width: 96px; height: 96px; }
  .avatar-initials { font-size: 2.2rem; }
}

/* ─── Face ID Card ───────────────────────────────────────── */
.icon-indigo { background: #eef2ff; color: #4f46e5; }

.fid-body {
  display: flex;
  gap: 2rem;
  padding: 1.5rem;
  align-items: flex-start;
}

/* Preview zone: a 2×2 style portrait box */
.fid-preview-wrap {
  flex-shrink: 0;
  position: relative;
  width: 150px;
  height: 180px;
  border-radius: 12px;
  overflow: hidden;
  border: 2px dashed #cbd5e1;
  background: #f8fafc;
  cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease;
}
.fid-preview-wrap:hover {
  border-color: #4f46e5;
  background: #eef2ff;
}
.fid-preview-img {
  width: 100%; height: 100%;
  object-fit: cover;
  display: block;
}
.fid-preview-placeholder {
  width: 100%; height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: #94a3b8;
  font-size: 0.78rem;
  font-weight: 500;
  text-align: center;
  padding: 0.5rem;
}
.fid-preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(79, 70, 229, 0.75);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  color: #fff;
  font-size: 0.78rem;
  font-weight: 600;
  opacity: 0;
  transition: opacity 0.2s ease;
}
.fid-preview-wrap:hover .fid-preview-overlay { opacity: 1; }

/* Guidelines */
.fid-guidelines { flex: 1; min-width: 0; }

.fid-guide-title {
  font-size: 0.82rem;
  font-weight: 700;
  color: #334155;
  margin: 0 0 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.fid-guide-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.55rem;
}
.fid-guide-list li {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.87rem;
  color: #475569;
}
.fid-guide-list li svg { color: #22c55e; flex-shrink: 0; }

.fid-error {
  font-size: 0.85rem;
  color: #dc2626;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  margin: 0;
}

.fid-pending-note {
  font-size: 0.84rem;
  color: #0369a1;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 0.6rem 0.85rem;
  margin: 0.6rem 0 0;
}
.fid-pending-note em { font-style: normal; font-weight: 700; }

/* Status badges */
.fid-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.28rem 0.75rem;
  border-radius: 20px;
  font-size: 0.76rem;
  font-weight: 700;
  flex-shrink: 0;
  letter-spacing: 0.03em;
}
.fid-badge--registered { background: #f0fdf4; color: #15803d; border: 1px solid #bbf7d0; }
.fid-badge--required   { background: #fffbeb; color: #b45309; border: 1px solid #fde68a; }
.fid-badge--pending    { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

.fid-dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}
.fid-dot--green { background: #22c55e; animation: blink 1.5s ease-in-out infinite; }
.fid-dot--amber { background: #f59e0b; animation: blink 1.2s ease-in-out infinite; }
.fid-dot--blue  { background: #3b82f6; animation: blink 1s ease-in-out infinite; }

@media (max-width: 600px) {
  .fid-body { flex-direction: column; }
  .fid-preview-wrap { width: 100%; height: 200px; }
}

.fid-save-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.75rem;
}

.fid-pending-note {
  font-size: 0.84rem;
  color: #0369a1;
  margin: 0;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 260px;
}

.fid-save-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.6rem 1.2rem;
  border-radius: 10px;
  background: #1D3461;
  color: #fff;
  border: none;
  font-family: 'Inter', sans-serif;
  font-size: 0.88rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.18s ease, transform 0.15s ease;
  flex-shrink: 0;
}
.fid-save-btn:hover:not(:disabled) {
  background: #16294f;
  transform: translateY(-1px);
}
.fid-save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.fid-spinner {
  width: 12px;
  height: 12px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  flex-shrink: 0;
}

/* ─── Locked / Pending states ─────────────────────────────── */
.fid-locked-wrap {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
}

.fid-locked-photo {
  position: relative;
  width: 130px;
  height: 130px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  border: 2px solid #22c55e;
  box-shadow: 0 0 0 4px rgba(34,197,94,0.12);
}
.fid-locked-photo--pending {
  border-color: #3b82f6;
  box-shadow: 0 0 0 4px rgba(59,130,246,0.12);
}
.fid-locked-photo .fid-preview-img,
.fid-locked-photo .fid-preview-placeholder {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}

.fid-locked-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.48);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.3rem;
  color: #fff;
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}
.fid-locked-overlay--pending { background: rgba(30,64,175,0.5); }

.fid-locked-note {
  font-size: 0.84rem;
  color: #64748b;
  margin: 0.4rem 0 0;
  line-height: 1.55;
}
</style>
