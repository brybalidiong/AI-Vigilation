<template>
  <div class="app-wrapper">
    <div class="dashboard-container">
      <!-- Sidebar -->
      <aside class="sidebar">
        <div class="sidebar-logo">
          <span class="sidebar-brand-name">AI-Vigilation</span>
        </div>
        
        <div class="sidebar-section-label">Admin Panel</div>
        
        <nav class="sidebar-nav">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            class="nav-item"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
            :id="`nav-${tab.key}`"
          >
            <component :is="'svg'" class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" v-html="tab.icon"/>
            <span>{{ tab.label }}</span>
            <span v-if="tab.count !== undefined" class="badge" style="margin-left:auto; background: rgba(0,0,0,0.2); border-radius: 99px; padding: 0.1rem 0.5rem; font-size: 0.75rem;">{{ tab.count }}</span>
          </button>
        </nav>

        <div class="sidebar-footer-nav">
          <div class="sidebar-user-info">
            <div class="sidebar-user-avatar">A</div>
            <div class="sidebar-user-text">
              <span class="sidebar-user-name">Administrator</span>
              <span class="sidebar-user-role">System Admin</span>
            </div>
          </div>
          <button class="nav-item logout-nav" @click="requestLogout" id="logout-btn" title="Logout">
            <svg class="nav-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Log Out
          </button>
        </div>
      </aside>

      <!-- Main Content -->
      <main class="main-content">
        <header class="main-header">
          <div class="header-titles">
            <h1 v-if="activeTab === 'overview'">Dashboard Overview</h1>
            <h1 v-if="activeTab === 'instructors'">Instructor Management</h1>
            <h1 v-if="activeTab === 'students'">Student Enrollment</h1>
            <p class="header-sub" v-if="activeTab === 'overview'">Manage your institution's users and access</p>
            <p class="header-sub" v-if="activeTab === 'instructors'">Register instructor accounts that can log in with their @{{ schoolDomain }} Google account</p>
            <p class="header-sub" v-if="activeTab === 'students'">Formally enroll students so they can log in with their @{{ schoolDomain }} Google account</p>
          </div>
          <div class="header-actions">
            <div class="role-pill">Admin</div>
          </div>
        </header>

        <!-- Overview Tab -->
        <section v-if="activeTab === 'overview'">
          <div class="stats-grid">
            <div class="moodle-card stat-card" id="stat-instructors">
              <div class="stat-icon instructor-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
                </svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Registered Instructors</p>
                <h2 class="stat-value">{{ instructors.length }}</h2>
              </div>
            </div>
            <div class="moodle-card stat-card" id="stat-students">
              <div class="stat-icon student-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Enrolled Students</p>
                <h2 class="stat-value">{{ students.length }}</h2>
              </div>
            </div>
            <div class="moodle-card stat-card" id="stat-domain">
              <div class="stat-icon domain-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                  <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                </svg>
              </div>
              <div class="stat-body">
                <p class="stat-label">Allowed Domain</p>
                <h2 class="stat-value domain-val" style="font-size:1.5rem;">@{{ schoolDomain }}</h2>
              </div>
            </div>
          </div>

          <div class="moodle-card mt-1">
            <h2 class="moodle-section-title">Quick Actions</h2>
            <div class="action-grid" style="display:flex; gap:1.5rem;">
              <button class="moodle-btn-ghost action-card" @click="activeTab = 'instructors'" id="action-add-instructor">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg>
                Register Instructor
              </button>
              <button class="moodle-btn-ghost action-card" @click="activeTab = 'students'" id="action-enroll-student">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                  <line x1="19" y1="8" x2="19" y2="14"/><line x1="22" y1="11" x2="16" y2="11"/>
                </svg>
                Enroll Student
              </button>
            </div>
          </div>
        </section>

        <!-- Instructors Tab -->
        <section v-if="activeTab === 'instructors'">
          <div class="moodle-filters">
             <button class="primary-btn" @click="showAddInstructor = !showAddInstructor" id="add-instructor-btn">
               <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                 <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
               </svg>
               Register Instructor
             </button>
             <input v-model="instructorSearch" type="text" class="moodle-search" placeholder="Search instructors..." id="instructor-search"/>
          </div>

          <!-- Add Instructor Form -->
          <div v-if="showAddInstructor" class="create-form-wrapper" id="instructor-form">
            <h3 class="form-title">Register New Instructor</h3>
            <div class="inline-form">
              <input v-model="newInstructor.first_name" type="text" placeholder="First Name (e.g. Juan)" id="instructor-first-name"/>
              <input v-model="newInstructor.last_name" type="text" placeholder="Last Name (e.g. Dela Cruz)" id="instructor-last-name"/>
              <input v-model="newInstructor.email" type="email" :placeholder="`Email (e.g. instructor@${schoolDomain})`" required id="instructor-email"/>
              <button class="primary-btn shrink-btn" @click="registerInstructor" :disabled="instructorLoading" id="submit-instructor-btn">
                {{ instructorLoading ? 'Registering...' : 'Register' }}
              </button>
              <button class="ghost-btn shrink-btn" @click="showAddInstructor = false; clearInstructorForm()">Cancel</button>
            </div>
            <p v-if="instructorError" class="res-msg" style="color:var(--status-danger);">{{ instructorError }}</p>
            <p v-if="instructorSuccess" class="res-msg" style="color:var(--status-success);">{{ instructorSuccess }}</p>
          </div>

          <!-- Instructors Table -->
          <div class="data-table-container">
            <table class="data-table" v-if="filteredInstructors.length > 0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ins in filteredInstructors" :key="ins.id">
                  <td class="bold-td">{{ ins.full_name || '—' }}</td>
                  <td>{{ ins.email }}</td>
                  <td style="text-align: right;">
                    <button class="danger-btn" style="padding: 0.35rem 0.8rem;" @click="removeInstructor(ins)" :id="`remove-instructor-${ins.id}`">Remove</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else-if="loadingInstructors" class="table-meta" style="text-align: center;">Loading instructors...</div>
            <div v-else class="table-meta" style="text-align: center;">No instructors found.</div>
          </div>
        </section>

        <!-- Students Tab -->
        <section v-if="activeTab === 'students'">
          <div class="moodle-filters">
             <button class="primary-btn" @click="showAddStudent = !showAddStudent" id="add-student-btn">
               <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                 <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
               </svg>
               Enroll Student
             </button>
             <input v-model="studentSearch" type="text" class="moodle-search" placeholder="Search students..." id="student-search"/>
          </div>

          <!-- Add Student Form -->
          <div v-if="showAddStudent" class="create-form-wrapper" id="student-form">
            <h3 class="form-title">Formally Enroll New Student</h3>
            <div class="inline-form">
              <input v-model="newStudent.first_name" type="text" placeholder="First Name" id="student-first-name"/>
              <input v-model="newStudent.last_name" type="text" placeholder="Last Name" id="student-last-name"/>
              <input v-model="newStudent.email" type="email" :placeholder="`Email (e.g. student@${schoolDomain})`" required id="student-email"/>
              <button class="primary-btn shrink-btn" @click="enrollStudent" :disabled="studentLoading" id="submit-student-btn">
                {{ studentLoading ? 'Enrolling...' : 'Enroll' }}
              </button>
              <button class="ghost-btn shrink-btn" @click="showAddStudent = false; clearStudentForm()">Cancel</button>
            </div>
            <p class="res-msg">Once enrolled here, the student can log in using Google Sign-In.</p>
            <p v-if="studentError" class="res-msg" style="color:var(--status-danger);">{{ studentError }}</p>
            <p v-if="studentSuccess" class="res-msg" style="color:var(--status-success);">{{ studentSuccess }}</p>
          </div>

        <!-- Students Table -->
          <div class="data-table-container">
            <table class="data-table" v-if="filteredStudents.length > 0">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Email</th>
                  <th>Status</th>
                  <th style="min-width:200px">Face ID</th>
                  <th style="text-align: right;">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="st in filteredStudents" :key="st.id">
                  <td class="bold-td">{{ st.full_name || '—' }}</td>
                  <td>{{ st.email }}</td>
                  <td>
                    <span class="status-badge" :class="st.is_enrolled ? 'badge-active' : 'badge-neutral'">
                      {{ st.is_enrolled ? 'Enrolled' : 'Inactive' }}
                    </span>
                  </td>
                  <td style="min-width:240px">
                    <!-- PENDING -->
                    <div v-if="st.face_status === 'pending'" class="face-cell">
                      <div class="face-cell-top">
                        <div class="face-thumb-wrap face-thumb--pending">
                          <img v-if="st.face_pending_photo_url" :src="st.face_pending_photo_url" class="face-thumb-img" alt="Pending" />
                          <span v-else class="face-thumb-placeholder">?</span>
                        </div>
                        <span class="face-label face-label--pending">⏳ Pending Review</span>
                      </div>
                      <div class="face-btn-row">
                        <button class="face-btn face-btn--approve" @click="approveFace(st)" :disabled="!!st._faceLoading" :id="`approve-face-${st.id}`">
                          {{ st._faceLoading === 'approve' ? 'Approving…' : '✓ Approve' }}
                        </button>
                        <button class="face-btn face-btn--reject" @click="rejectFace(st)" :disabled="!!st._faceLoading" :id="`reject-face-${st.id}`">
                          {{ st._faceLoading === 'reject' ? 'Rejecting…' : '✗ Reject' }}
                        </button>
                      </div>
                    </div>
                    <!-- APPROVED -->
                    <div v-else-if="st.face_status === 'approved'" class="face-cell">
                      <div class="face-cell-top">
                        <div class="face-thumb-wrap face-thumb--approved">
                          <img v-if="st.face_photo_url" :src="st.face_photo_url" class="face-thumb-img" alt="Approved" />
                          <span v-else class="face-thumb-placeholder">✓</span>
                        </div>
                        <span class="face-label face-label--approved">✅ Approved</span>
                      </div>
                      <label class="face-toggle" :for="`reupload-toggle-${st.id}`">
                        <input
                          type="checkbox"
                          :id="`reupload-toggle-${st.id}`"
                          :checked="st.face_reupload_allowed"
                          :disabled="!!st._faceLoading"
                          @change="toggleReupload(st)"
                        />
                        <span class="face-toggle-slider"></span>
                        <span class="face-toggle-label">Allow re-upload</span>
                      </label>
                    </div>
                    <!-- NONE -->
                    <div v-else class="face-cell">
                      <span class="face-label face-label--none">— Not submitted</span>
                    </div>
                  </td>
                  <td style="text-align: right;">
                    <button class="danger-btn" style="padding: 0.35rem 0.8rem;" @click="removeStudent(st)" :id="`remove-student-${st.id}`">Remove</button>
                  </td>
                </tr>
              </tbody>
            </table>
            <div v-else-if="loadingStudents" class="table-meta" style="text-align: center;">Loading students...</div>
            <div v-else class="table-meta" style="text-align: center;">No students found.</div>
          </div>
        </section>
      </main>

      <!-- Confirm Dialog -->
      <ConfirmModal
        v-model="confirmOpen"
        :title="confirmTitle"
        :message="confirmMessage"
        :variant="confirmVariant"
        :confirm-text="confirmConfirmText"
        :cancel-text="confirmCancelText"
        @confirm="onConfirmDialog"
        @cancel="clearPendingConfirm"
      />
      <Transition name="action-toast">
        <div v-if="actionSuccess" class="action-success-toast" role="status" aria-live="polite">
          <span class="action-success-icon">✓</span>
          <div><strong>Success</strong><span>{{ actionSuccess }}</span></div>
        </div>
      </Transition>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";
import ConfirmModal from "@/components/ConfirmModal.vue";

const router = useRouter();
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";
const schoolDomain = import.meta.env.VITE_SCHOOL_DOMAIN || "dnsc.edu.ph";

const activeTab = ref("overview");

const tabs = computed(() => [
  {
    key: "overview",
    label: "Overview",
    icon: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
  },
  {
    key: "instructors",
    label: "Instructors",
    count: instructors.value.length,
    icon: '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  },
  {
    key: "students",
    label: "Students",
    count: students.value.length,
    icon: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  },
]);

// Instructors
const instructors = ref([]);
const loadingInstructors = ref(false);
const showAddInstructor = ref(false);
const instructorLoading = ref(false);
const instructorError = ref("");
const instructorSuccess = ref("");
const instructorSearch = ref("");
const newInstructor = ref({ email: "", first_name: "", last_name: "" });

// Students
const students = ref([]);
const loadingStudents = ref(false);
const showAddStudent = ref(false);
const studentLoading = ref(false);
const studentError = ref("");
const studentSuccess = ref("");
const actionSuccess = ref("");
let actionSuccessTimer = null;

function showActionSuccess(text) {
  actionSuccess.value = text;
  clearTimeout(actionSuccessTimer);
  actionSuccessTimer = setTimeout(() => { actionSuccess.value = ""; }, 4000);
}
const studentSearch = ref("");
const newStudent = ref({ email: "", first_name: "", last_name: "" });

const confirmOpen = ref(false);
const confirmTitle = ref("");
const confirmMessage = ref("");
const confirmVariant = ref("danger");
const confirmConfirmText = ref("Confirm");
const confirmCancelText = ref("Cancel");
let _pendingConfirmCallback = null;

function openConfirm(options) {
  confirmTitle.value = options.title || "Confirm";
  confirmMessage.value = options.message || "Are you sure?";
  confirmVariant.value = options.variant || "danger";
  confirmConfirmText.value = options.confirmText || "Confirm";
  confirmCancelText.value = options.cancelText || "Cancel";
  _pendingConfirmCallback = options.onConfirm || null;
  confirmOpen.value = true;
}

function onConfirmDialog() {
  if (_pendingConfirmCallback) _pendingConfirmCallback();
  clearPendingConfirm();
}

function clearPendingConfirm() {
  _pendingConfirmCallback = null;
  confirmOpen.value = false;
}

function getHeaders() {
  const token = localStorage.getItem("access_token");
  return { Authorization: `Bearer ${token}` };
}

async function fetchInstructors() {
  loadingInstructors.value = true;
  try {
    const res = await axios.get(`${backendBaseUrl}/api/admin/instructors/`, { headers: getHeaders() });
    instructors.value = res.data.instructors || [];
  } catch (e) {
    console.error(e);
  } finally {
    loadingInstructors.value = false;
  }
}

async function fetchStudents() {
  loadingStudents.value = true;
  try {
    const res = await axios.get(`${backendBaseUrl}/api/admin/students/`, { headers: getHeaders() });
    students.value = res.data.students || [];
  } catch (e) {
    console.error(e);
  } finally {
    loadingStudents.value = false;
  }
}

async function registerInstructor() {
  instructorError.value = "";
  instructorSuccess.value = "";
  if (!newInstructor.value.email) {
    instructorError.value = "Email is required.";
    return;
  }
  instructorLoading.value = true;
  try {
    const res = await axios.post(`${backendBaseUrl}/api/admin/instructors/`, newInstructor.value, { headers: getHeaders() });
    instructorSuccess.value = `Instructor "${res.data.email}" registered successfully!`;
    showActionSuccess(`Instructor "${res.data.email}" registered successfully.`);
    instructors.value.unshift(res.data);
    clearInstructorForm();
    setTimeout(() => { instructorSuccess.value = ""; showAddInstructor.value = false; }, 2000);
  } catch (e) {
    instructorError.value = e?.response?.data?.error || "Failed to register instructor.";
  } finally {
    instructorLoading.value = false;
  }
}

function removeInstructor(ins) {
  openConfirm({
    title: "Remove Instructor",
    message: `Are you sure you want to remove "${ins.full_name || ins.email}"? This action cannot be undone.`,
    onConfirm: async () => {
      try {
        await axios.delete(`${backendBaseUrl}/api/admin/instructors/${ins.id}/`, { headers: getHeaders() });
        instructors.value = instructors.value.filter((i) => i.id !== ins.id);
        showActionSuccess('Instructor removed successfully.');
      } catch (e) {
        alert(e?.response?.data?.error || "Failed to remove instructor.");
      }
    },
  });
}

async function enrollStudent() {
  studentError.value = "";
  studentSuccess.value = "";
  if (!newStudent.value.email) {
    studentError.value = "Email is required.";
    return;
  }
  studentLoading.value = true;
  try {
    const res = await axios.post(`${backendBaseUrl}/api/admin/students/`, newStudent.value, { headers: getHeaders() });
    studentSuccess.value = `Student "${res.data.email}" enrolled successfully!`;
    showActionSuccess(`Student "${res.data.email}" enrolled successfully.`);
    const existing = students.value.find((s) => s.id === res.data.id);
    if (!existing) students.value.unshift(res.data);
    clearStudentForm();
    setTimeout(() => { studentSuccess.value = ""; showAddStudent.value = false; }, 2000);
  } catch (e) {
    studentError.value = e?.response?.data?.error || "Failed to enroll student.";
  } finally {
    studentLoading.value = false;
  }
}

function removeStudent(st) {
  openConfirm({
    title: "Remove Student Enrollment",
    message: `Are you sure you want to remove "${st.full_name || st.email}" from the system? They will no longer be able to log in.`,
    onConfirm: async () => {
      try {
        await axios.delete(`${backendBaseUrl}/api/admin/students/${st.id}/`, { headers: getHeaders() });
        students.value = students.value.filter((s) => s.id !== st.id);
        showActionSuccess('Student removed successfully.');
      } catch (e) {
        alert(e?.response?.data?.error || "Failed to remove student.");
      }
    },
  });
}

async function approveFace(st) {
  st._faceLoading = 'approve';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'approve_face' },
      { headers: getHeaders() }
    );
    st.face_status = res.data.face_status;
    if (res.data.face_photo_url) st.face_photo_url = res.data.face_photo_url;
    st.face_pending_photo_url = null;
    st.face_reupload_allowed = false;
    showActionSuccess('Face photo approved successfully.');
  } catch (e) {
    alert(e?.response?.data?.error || 'Failed to approve face photo.');
  } finally {
    st._faceLoading = null;
  }
}

async function rejectFace(st) {
  st._faceLoading = 'reject';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'reject_face' },
      { headers: getHeaders() }
    );
    st.face_status = res.data.face_status;
    st.face_pending_photo_url = null;
    showActionSuccess('Face photo rejected. The student may submit a new photo.');
  } catch (e) {
    alert(e?.response?.data?.error || 'Failed to reject face photo.');
  } finally {
    st._faceLoading = null;
  }
}

async function toggleReupload(st) {
  st._faceLoading = 'toggle';
  try {
    const res = await axios.patch(
      `${backendBaseUrl}/api/admin/students/${st.id}/`,
      { action: 'toggle_reupload' },
      { headers: getHeaders() }
    );
    st.face_reupload_allowed = res.data.face_reupload_allowed;
    st.face_status = res.data.face_status;
    showActionSuccess(
      res.data.face_reupload_allowed
        ? 'Face photo re-upload enabled.'
        : 'Face photo re-upload disabled.'
    );
  } catch (e) {
    alert(e?.response?.data?.error || 'Failed to toggle re-upload.');
  } finally {
    st._faceLoading = null;
  }
}

function clearInstructorForm() {
  newInstructor.value = { email: "", first_name: "", last_name: "" };
  instructorError.value = "";
  instructorSuccess.value = "";
}

function clearStudentForm() {
  newStudent.value = { email: "", first_name: "", last_name: "" };
  studentError.value = "";
  studentSuccess.value = "";
}

const filteredInstructors = computed(() => {
  const q = instructorSearch.value.toLowerCase();
  if (!q) return instructors.value;
  return instructors.value.filter(
    (i) => (i.full_name || "").toLowerCase().includes(q) || i.email.toLowerCase().includes(q)
  );
});

const filteredStudents = computed(() => {
  const q = studentSearch.value.toLowerCase();
  if (!q) return students.value;
  return students.value.filter(
    (s) => (s.full_name || "").toLowerCase().includes(q) || s.email.toLowerCase().includes(q)
  );
});

function requestLogout() {
  openConfirm({
    variant: 'logout',
    title: 'Log out?',
    message: 'You will be signed out of the admin panel and returned to the admin login page.',
    confirmText: 'Log out',
    onConfirm: logout,
  });
}

function logout() {
  localStorage.clear();
  router.push("/admin/login");
}

onMounted(() => {
  fetchInstructors();
  fetchStudents();
});
</script>

<style scoped>
@import '@/assets/dashboard.css';

.action-success-toast {
  position: fixed;
  top: 1.25rem;
  right: 1.25rem;
  z-index: 1000002;
  display: flex;
  align-items: flex-start;
  gap: 0.7rem;
  width: min(390px, calc(100vw - 2rem));
  padding: 0.9rem 1rem;
  color: #14532d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-left: 4px solid #22c55e;
  border-radius: 10px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.2);
}
.action-success-icon { flex: 0 0 auto; font-size: 1rem; font-weight: 800; }
.action-success-toast div { display: grid; gap: 0.15rem; }
.action-success-toast strong { font-size: 0.82rem; }
.action-success-toast span { font-size: 0.86rem; line-height: 1.35; }
.action-toast-enter-active, .action-toast-leave-active { transition: opacity 0.2s ease, transform 0.2s ease; }
.action-toast-enter-from, .action-toast-leave-to { opacity: 0; transform: translateY(-10px); }

/* Admin specific additions */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 1.5rem;
}
.stat-icon {
  width: 54px;
  height: 54px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.instructor-icon { background: rgba(99, 102, 241, 0.1); color: #6366f1; }
.student-icon { background: rgba(16, 185, 129, 0.1); color: #10b981; }
.domain-icon { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
.stat-label {
  font-size: 0.75rem; color: var(--text-secondary); margin: 0 0 0.25rem;
  font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
}
.stat-value {
  font-family: 'Poppins', sans-serif;
  font-size: 2.2rem; font-weight: 900; color: var(--text-primary);
  margin: 0; letter-spacing: -0.04em; line-height: 1;
}

.modal-backdrop {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex; align-items: center; justify-content: center;
}

/* ─── Face ID column ─────────────────────────────────────── */
.face-cell {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.25rem 0;
}

.face-cell-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.face-btn-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: nowrap;
}

.face-thumb-wrap {
  width: 44px;
  height: 44px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #e2e8f0;
  background: #f8fafc;
}
.face-thumb--pending { border-color: #3b82f6; background: #eff6ff; }
.face-thumb--approved { border-color: #22c55e; background: #f0fdf4; }

.face-thumb-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.face-thumb-placeholder { font-size: 1.1rem; color: #94a3b8; }

.face-actions {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 0;
}

.face-label {
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}
.face-label--pending  { color: #2563eb; }
.face-label--approved { color: #15803d; }
.face-label--none     { color: #94a3b8; font-size: 0.8rem; font-weight: 500; text-transform: none; }

.face-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.22rem 0.65rem;
  border-radius: 6px;
  border: none;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: opacity 0.15s;
}
.face-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.face-btn--approve { background: #dcfce7; color: #15803d; }
.face-btn--approve:hover:not(:disabled) { background: #bbf7d0; }
.face-btn--reject  { background: #fee2e2; color: #b91c1c; }
.face-btn--reject:hover:not(:disabled)  { background: #fecaca; }

/* toggle switch */
.face-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  cursor: pointer;
  user-select: none;
}
.face-toggle input { display: none; }
.face-toggle-slider {
  width: 30px; height: 16px;
  border-radius: 999px;
  background: #cbd5e1;
  position: relative;
  flex-shrink: 0;
  transition: background 0.2s;
}
.face-toggle-slider::after {
  content: '';
  position: absolute;
  top: 2px; left: 2px;
  width: 12px; height: 12px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.2);
  transition: transform 0.2s;
}
.face-toggle input:checked + .face-toggle-slider { background: #6366f1; }
.face-toggle input:checked + .face-toggle-slider::after { transform: translateX(14px); }
.face-toggle-label { font-size: 0.76rem; font-weight: 600; color: #475569; white-space: nowrap; }
</style>
