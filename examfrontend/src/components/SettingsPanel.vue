<template>
  <div class="settings-panel">
    <div class="settings-grid">
      
      <!-- Left Column: Profile Picture Card -->
      <div class="avatar-card">
        <div class="avatar-wrapper">
          <img :src="photoPreview || form.photo || fallbackAvatar" alt="Profile Picture" class="avatar-img" />
          <div class="avatar-overlay">
            <label v-if="isEditing" for="custom_photo" class="upload-btn">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </label>
          </div>
        </div>
        <input type="file" id="custom_photo" accept="image/*" @change="onPhotoSelect" style="display: none;" />
        <div class="avatar-info">
          <h3>{{ form.first_name || 'User' }} {{ form.last_name || 'Name' }}</h3>
          <p class="role-badge">{{ form.role?.toUpperCase() || 'USER' }}</p>
          <p class="helper-text">Upload a new avatar (JPG, PNG)</p>
        </div>
      </div>

      <!-- Right Column: Settings Form -->
      <form @submit.prevent="saveSettings" class="settings-form">
        <h2 class="form-title">Personal Information</h2>
        
        <div class="form-row">
          <div class="field-group" :class="{ 'disabled-group': !isEditing }">
            <label>First Name</label>
            <input type="text" v-model="form.first_name" required placeholder="Enter first name" :disabled="!isEditing" />
          </div>
          <div class="field-group" :class="{ 'disabled-group': !isEditing }">
            <label>Last Name</label>
            <input type="text" v-model="form.last_name" required placeholder="Enter last name" :disabled="!isEditing" />
          </div>
        </div>

        <div class="field-group" :class="{ 'disabled-group': !isEditing }">
          <label>Mobile Number</label>
          <div class="input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>
            </svg>
            <input type="tel" v-model="form.mobile_number" placeholder="+63 900 000 0000" :disabled="!isEditing" />
          </div>
        </div>

        <div class="divider"></div>
        <h2 class="form-title">Account Details</h2>

        <div class="field-group disabled-group">
          <label>Email Address <span class="read-only-badge">Read-only</span></label>
          <div class="input-wrap">
            <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
              <polyline points="22,6 12,13 2,6"/>
            </svg>
            <input type="text" :value="form.email" disabled />
          </div>
        </div>



        <div class="modal-actions">
          <template v-if="!isEditing">
            <button type="button" class="btn-primary" @click="startEditing">Edit Profile</button>
          </template>
          <template v-else>
            <button type="button" class="btn-secondary" @click="cancelEditing" :disabled="loading">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="loading">
              {{ loading ? 'Saving...' : 'Save Changes' }}
            </button>
          </template>
        </div>

      </form>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from 'axios';
import { addToast } from '@/utils/toast';

const emit = defineEmits(['updated']);

const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

const form = ref({
  first_name: '',
  last_name: '',
  mobile_number: '',
  email: '',
  role: '',
  photo: ''
});

const selectedFile = ref(null);
const photoPreview = ref(null);
const fallbackAvatar = "https://ui-avatars.com/api/?name=User&background=1D3461&color=fff";

const loading = ref(false);
const isEditing = ref(false);

function startEditing() {
  isEditing.value = true;
}

function cancelEditing() {
  isEditing.value = false;
  selectedFile.value = null;
  photoPreview.value = null;
  loadUser();
}

function loadUser() {
  const userStr = localStorage.getItem('user');
  if (userStr) {
    try {
      const user = JSON.parse(userStr);
      form.value.first_name = user.first_name || '';
      form.value.last_name = user.last_name || '';
      form.value.mobile_number = user.mobile_number || '';
      form.value.email = user.email || '';
      form.value.role = user.role || '';
      form.value.photo = user.photo || '';
    } catch (e) {
      console.error("Error parsing user data");
    }
  }
}

onMounted(() => {
  loadUser();
});

function onPhotoSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  
  // Validate file type
  if (!file.type.startsWith('image/')) {
    errorMsg.value = "Please select a valid image file.";
    return;
  }
  
  selectedFile.value = file;
  
  // Create preview
  const reader = new FileReader();
  reader.onload = (e) => {
    photoPreview.value = e.target.result;
  };
  reader.readAsDataURL(file);
}

async function saveSettings() {
  loading.value = true;

  try {
    const token = localStorage.getItem("access_token");
    
    // Use FormData for file uploads
    const formData = new FormData();
    formData.append('first_name', form.value.first_name);
    formData.append('last_name', form.value.last_name);
    formData.append('mobile_number', form.value.mobile_number);
    
    if (selectedFile.value) {
      formData.append('custom_photo', selectedFile.value);
    }

    const response = await axios.post(`${backendBaseUrl}/api/auth/me/update/`, formData, {
      headers: { 
        Authorization: `Bearer ${token}`,
        'Content-Type': 'multipart/form-data'
      }
    });
    
    // Update local storage
    const updatedUser = response.data.user;
    localStorage.setItem("user", JSON.stringify(updatedUser));
    
    // Update local form state photo so preview isn't needed anymore
    form.value.photo = updatedUser.photo;
    isEditing.value = false;
    selectedFile.value = null;
    photoPreview.value = null;
    
    addToast('Settings saved successfully!', 'success');
    emit('updated', updatedUser);
  } catch (err) {
    console.error(err);
    addToast(err.response?.data?.message || 'Failed to update settings. Please try again.', 'error');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>

.settings-panel {
  display: flex;
  flex-direction: column;
  font-family: 'Poppins', sans-serif;
  animation: fadeIn 0.3s ease forwards;
  width: 100%;
}

.settings-grid {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 2rem;
  width: 100%;
  max-width: 1000px;
}

@media (max-width: 800px) {
  .settings-grid {
    grid-template-columns: 1fr;
  }
}

.avatar-card {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.02);
  border: 1px solid #f1f5f9;
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  height: max-content;
}

.settings-form {
  background: #ffffff;
  border-radius: 20px;
  box-shadow: 0 10px 30px rgba(0,0,0,0.02);
  width: 100%;
  padding: 2.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  border: 1px solid #f1f5f9;
}

.form-title {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
  font-weight: 700;
  color: #1D3461;
}

/* Avatar styling */
.avatar-wrapper {
  position: relative;
  width: 120px;
  height: 120px;
  border-radius: 50%;
  overflow: hidden;
  box-shadow: 0 8px 24px rgba(0,0,0,0.1);
  border: 4px solid #ffffff;
  margin-bottom: 1.5rem;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.avatar-wrapper:hover .avatar-overlay {
  opacity: 1;
}

.upload-btn {
  color: white;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
}

.avatar-info h3 {
  margin: 0 0 0.5rem 0;
  color: #1e293b;
  font-size: 1.4rem;
}

.role-badge {
  display: inline-block;
  background: #f1f5f9;
  color: #475569;
  padding: 0.3rem 0.8rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 700;
  margin: 0 0 1rem 0;
}

.helper-text {
  margin: 0;
  color: #94a3b8;
  font-size: 0.85rem;
}

/* Text fields */
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.field-group label {
  font-size: 0.9rem;
  font-weight: 600;
  color: #1e293b;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.read-only-badge {
  font-size: 0.7rem;
  background: #f1f5f9;
  color: #64748b;
  padding: 0.2rem 0.5rem;
  border-radius: 12px;
  font-weight: 700;
}

.field-group input {
  padding: 0.85rem 1rem;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  font-family: inherit;
  font-size: 0.95rem;
  color: #1e293b;
  transition: all 0.2s;
}

.field-group input:focus {
  outline: none;
  border-color: #1D3461;
  box-shadow: 0 0 0 3px rgba(29, 52, 97, 0.1);
}

.input-wrap {
  position: relative;
}

.input-icon {
  position: absolute;
  left: 1rem;
  top: 50%;
  transform: translateY(-50%);
  color: #94a3b8;
}

.input-wrap input {
  width: 100%;
  padding-left: 2.75rem;
  box-sizing: border-box;
}

.disabled-group input {
  background: #f8fafc;
  color: #64748b;
  cursor: not-allowed;
  border-color: #e2e8f0;
}

.divider {
  height: 1px;
  background: #e2e8f0;
  margin: 0.5rem 0;
}

.error-msg {
  color: #dc2626;
  background: #fef2f2;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
}

.success-msg {
  color: #059669;
  background: #d1fae5;
  padding: 0.75rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 500;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
  margin-top: 0.5rem;
}

.btn-primary {
  padding: 0.85rem 1.75rem;
  background: #1D3461;
  color: white;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  width: auto;
}

.btn-primary:hover:not(:disabled) {
  background: #162a4f;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 0.85rem 1.75rem;
  background: #f1f5f9;
  color: #475569;
  border: none;
  border-radius: 10px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  width: auto;
}

.btn-secondary:hover:not(:disabled) {
  background: #e2e8f0;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
