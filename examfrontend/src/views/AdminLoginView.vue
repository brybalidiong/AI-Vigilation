<template>
  <div class="login-page">
    <!-- Top Bar -->
    <header class="login-header-bar">
      <div class="brand-logo">
        <span class="brand-name">AI-Vigilation Admin</span>
      </div>
      <div class="header-right">
        <span class="muted">Need help?</span>
        <button class="ghost-btn">Contact Support</button>
      </div>
    </header>

    <!-- Main Content -->
    <main class="login-main">
      <!-- Left side: Hero Text Focus -->
      <div class="login-hero">
        <div class="hero-bg-accent"></div>
        <div class="hero-content">
          <div class="dot-grid hero-dots"></div>
          <div class="hero-badge">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="#eab308"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
            System Administration
          </div>
          <h1>Platform Control.<br/><span class="text-mustard">Total Oversight.</span></h1>
          <p>Manage instructors, configure settings, and oversee all institutional online assessments securely.</p>
        </div>
      </div>

      <!-- Right side: Login Card -->
      <div class="login-form-panel">
        <div class="login-card">
          <div class="login-card-header">
            <h2>Admin Sign In</h2>
            <p>Restricted to system administrators only</p>
          </div>

          <form class="login-form" @submit.prevent="loginAdmin" id="admin-login-form">
            <div class="field-group">
              <label for="admin-username">Username</label>
              <div class="input-wrap">
                <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
                </svg>
                <input id="admin-username" v-model="username" type="text" placeholder="Enter username" required autocomplete="username"/>
              </div>
            </div>

            <div class="field-group">
              <label for="admin-password">Password</label>
              <div class="input-wrap">
                <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
                </svg>
                <input
                  id="admin-password"
                  v-model="password"
                  :type="showPassword ? 'text' : 'password'"
                  placeholder="Enter password"
                  required
                  autocomplete="current-password"
                />
                <button type="button" class="toggle-btn" @click="showPassword = !showPassword" tabindex="-1">
                  {{ showPassword ? 'Hide' : 'Show' }}
                </button>
              </div>
            </div>

            <button type="submit" class="btn-primary" :disabled="loading" id="admin-submit-btn">
              {{ loading ? 'Signing in...' : 'Sign in' }}
            </button>
          </form>

          <p v-if="error" class="error-msg">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
            {{ error }}
          </p>

          <div class="divider"><span>or</span></div>

          <button class="btn-google" @click="router.push('/')" id="back-to-login-btn">
            ← Return to Main Login
          </button>
        </div>
      </div>
    </main>

    <!-- Bottom Features Bar -->
    <footer class="login-footer-bar">
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></div>
        <div>
          <h4>System Configuration</h4>
          <p>Global settings management</p>
        </div>
      </div>
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>
        <div>
          <h4>User Management</h4>
          <p>Control instructor access</p>
        </div>
      </div>
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>
        <div>
          <h4>Audit Logs</h4>
          <p>Review system activity</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const username = ref("");
const password = ref("");
const showPassword = ref(false);
const loading = ref(false);
const error = ref("");
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

async function loginAdmin() {
  loading.value = true;
  error.value = "";
  try {
    const response = await axios.post(`${backendBaseUrl}/api/auth/admin/login/`, {
      username: username.value.trim(),
      password: password.value,
    });
    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("refresh_token", response.data.refresh_token);
    localStorage.setItem("role", "admin");
    localStorage.setItem("user", JSON.stringify(response.data.user || {}));
    router.push("/admin/dashboard");
  } catch (err) {
    const apiError = err?.response?.data?.error;
    const networkError = typeof err?.message === "string" && err.message.toLowerCase().includes("network");
    error.value = apiError || (networkError ? "Cannot reach backend. Start Django server first." : null) || err?.message || "Login failed.";
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
@import '@/assets/login-shared.css';

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Outfit:wght@300;400;500;600;700;800;900&display=swap');

.login-page {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f4f7f9;
  font-family: 'Inter', -apple-system, sans-serif;
}

/* Header */
.login-header-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 4rem;
  background: transparent;
  z-index: 10;
}
.brand-logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.brand-name {
  font-family: 'Outfit', sans-serif;
  color: #1D3461;
  font-weight: 900;
  font-size: 1.8rem;
  letter-spacing: -0.02em;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.muted {
  color: #64748b;
  font-size: 0.9rem;
  font-weight: 500;
}
.ghost-btn {
  background: #e2e8f0;
  border: 1px solid #cbd5e1;
  padding: 0.5rem 1.25rem;
  border-radius: 8px;
  font-family: inherit;
  font-weight: 600;
  color: #1D3461;
  cursor: pointer;
  transition: all 0.2s;
}
.ghost-btn:hover {
  background: #cbd5e1;
}

/* Main Content */
.login-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  padding: 1.5rem 4rem;
  gap: 4rem;
}

/* Left side Hero Typography */
.login-hero {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  max-width: 550px;
  position: relative;
}

.hero-bg-accent {
  position: absolute;
  bottom: -200px;
  left: -150px;
  width: 700px;
  height: 700px;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.08), transparent 60%);
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.hero-content {
  position: relative;
  z-index: 2;
}

.dot-grid {
  background-image: radial-gradient(#cbd5e1 2px, transparent 2px);
  background-size: 16px 16px;
}

.hero-dots {
  position: absolute;
  width: 140px;
  height: 140px;
  top: -60px;
  left: 20px;
  z-index: -1;
  opacity: 0.8;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.6rem;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 0.6rem 1.25rem;
  border-radius: 99px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #475569;
  margin-bottom: 2rem;
  box-shadow: 0 4px 12px rgba(0,0,0,0.03);
}

.hero-content h1 {
  font-family: 'Outfit', sans-serif;
  color: #1D3461;
  font-size: 3.8rem;
  font-weight: 900;
  line-height: 1.1;
  margin-bottom: 1.25rem;
  letter-spacing: -0.03em;
}

.text-mustard {
  color: #f59e0b;
}

.hero-content p {
  color: #475569;
  font-size: 1.15rem;
  line-height: 1.6;
  font-weight: 400;
  max-width: 95%;
}

/* Right side Card */
.login-form-panel {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}
.login-card {
  background: #ffffff;
  border-radius: 24px;
  padding: 2.5rem 3rem;
  width: 100%;
  max-width: 440px;
  box-shadow: 0 15px 35px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  position: relative;
  z-index: 10;
  border: 1px solid #f1f5f9;
}

.login-card-header h2 {
  font-family: 'Outfit', sans-serif;
  font-size: 1.9rem;
  font-weight: 800;
  color: #1D3461;
  margin-bottom: 0.4rem;
  letter-spacing: -0.02em;
}
.login-card-header p {
  font-size: 0.95rem;
  color: #64748b;
}

.domain-notice {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.85rem 1.25rem;
  font-size: 0.9rem;
  color: #475569;
}
.domain-notice strong { font-weight: 600; color: #1e293b; }

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  width: 100%;
  padding: 1rem 1.5rem;
  background: #fff;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 600;
  color: #1e293b;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.btn-google:hover:not(:disabled) {
  background: #f8fafc;
  border-color: #94a3b8;
}
.btn-google:disabled { opacity: 0.6; cursor: not-allowed; }
.google-icon { width: 22px; height: 22px; flex-shrink: 0; }

.divider {
  display: flex;
  align-items: center;
  gap: 1rem;
  color: #94a3b8;
  font-size: 0.85rem;
  font-weight: 500;
}
.divider::before, .divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}

.btn-admin {
  width: 100%;
  padding: 1rem 1.5rem;
  background: #1D3461;
  color: #fff;
  border: none;
  border-radius: 12px;
  font-family: inherit;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-admin:hover {
  background: #162a4f;
  transform: translateY(-1px);
}

.error-msg {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 0.85rem 1.25rem;
  font-size: 0.9rem;
  font-weight: 500;
  color: #dc2626;
}

.login-footer-links {
  text-align: center;
  margin-top: 0.5rem;
}
.login-note {
  font-size: 0.85rem;
  color: #94a3b8;
}

/* Footer Features Bar */
.login-footer-bar {
  display: flex;
  justify-content: center;
  gap: 4rem;
  padding: 1.5rem 4rem;
  border-top: 1px solid rgba(0,0,0,0.05);
}
.feature-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}
.feature-icon {
  background: #e2e8f0;
  border-radius: 10px;
  padding: 0.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #1D3461;
}
.feature-item h4 {
  color: #1D3461;
  font-weight: 700;
  font-size: 0.95rem;
  margin: 0 0 0.2rem 0;
  font-family: 'Outfit', sans-serif;
}
.feature-item p {
  color: #64748b;
  font-size: 0.85rem;
  margin: 0;
}

@media (max-width: 992px) {
  .login-main { flex-direction: column; gap: 3rem; text-align: center; }
  .login-form-panel { justify-content: center; }
  .login-hero { align-items: center; }
  .hero-graphics { height: 300px; }
  .login-footer-bar { flex-direction: column; gap: 1.5rem; align-items: flex-start; padding: 2rem; }
}
</style>
