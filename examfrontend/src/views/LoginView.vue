<template>
  <div class="login-page">
    <!-- Top Bar -->
    <header class="login-header-bar">
      <div class="brand-logo">
        <span class="brand-name">AI-Vigilation</span>
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
            Davao del Norte State College
          </div>
          <h1>Smarter Proctoring.<br/><span class="text-mustard">Powered by Vision.</span></h1>
          <p>Secure your online assessments with our AI-driven invigilation system.</p>
        </div>
      </div>

      <!-- Right side: Login Card -->
      <div class="login-form-panel perspective-container">
        <div class="login-card-wrapper" :class="{ 'is-flipped': showAdminLogin }">
          
          <!-- Front Card (Student / Instructor) -->
          <div class="login-card login-front">
            <div class="login-card-header">
              <h2>Welcome Back!</h2>
              <p>Sign in to continue your learning journey.</p>
            </div>

            <div class="domain-notice">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
              </svg>
              <span>Restricted to <strong>@{{ schoolDomain }}</strong> accounts</span>
            </div>

            <button class="btn-google" @click="loginWithGoogle" :disabled="loading" id="google-login-btn">
              <svg class="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>{{ loading ? 'Signing in...' : 'Continue with Google' }}</span>
            </button>

            <div class="divider">
              <span>or</span>
            </div>

            <button class="btn-admin" @click="showAdminLogin = true" id="admin-login-btn">
              Admin Login &rarr;
            </button>

            <p v-if="error" class="error-msg">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ error }}
            </p>
            
            <div class="login-footer-links">
              <span class="login-note">Students & Instructors use Google Sign-In</span>
            </div>
          </div>

          <!-- Back Card (Admin) -->
          <div class="login-card login-back">
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
                  <input id="admin-username" v-model="adminUsername" type="text" placeholder="Enter username" required autocomplete="username"/>
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
                    v-model="adminPassword"
                    :type="showAdminPassword ? 'text' : 'password'"
                    placeholder="Enter password"
                    required
                    autocomplete="current-password"
                  />
                  <button type="button" class="toggle-btn" @click="showAdminPassword = !showAdminPassword" tabindex="-1">
                    {{ showAdminPassword ? 'Hide' : 'Show' }}
                  </button>
                </div>
              </div>

              <button type="submit" class="btn-primary" :disabled="adminLoading" id="admin-submit-btn">
                {{ adminLoading ? 'Signing in...' : 'Sign in' }}
              </button>
            </form>

            <p v-if="adminError" class="error-msg">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ adminError }}
            </p>

            <div class="divider"><span>or</span></div>

            <button type="button" class="btn-google" @click="showAdminLogin = false" id="back-to-login-btn">
              &larr; Return to Main Login
            </button>
          </div>
        </div>
      </div>
    </main>

    <!-- Bottom Features Bar -->
    <footer class="login-footer-bar">
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg></div>
        <div>
          <h4>AI-Powered Proctoring</h4>
          <p>Automated gaze tracking</p>
        </div>
      </div>
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg></div>
        <div>
          <h4>Real-time Monitoring</h4>
          <p>Live instructor dashboards</p>
        </div>
      </div>
      <div class="feature-item">
        <div class="feature-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg></div>
        <div>
          <h4>Secure and Trusted</h4>
          <p>Domain-restricted access</p>
        </div>
      </div>
    </footer>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { signInWithPopup, signOut } from "firebase/auth";
import { auth, googleProvider } from "@/firebase";
import { useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const loading = ref(false);
const error = ref("");

const showAdminLogin = ref(false);
const adminUsername = ref("");
const adminPassword = ref("");
const showAdminPassword = ref(false);
const adminLoading = ref(false);
const adminError = ref("");

const schoolDomain = import.meta.env.VITE_SCHOOL_DOMAIN || "dnsc.edu.ph";
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

async function loginWithGoogle() {
  loading.value = true;
  error.value = "";
  try {
    const result = await signInWithPopup(auth, googleProvider);
    const email = result.user.email || "";

    if (!email.endsWith("@" + schoolDomain)) {
      await signOut(auth);
      error.value = "Only school accounts are allowed.";
      return;
    }

    const idToken = await result.user.getIdToken();
    const response = await axios.post(backendBaseUrl + "/api/auth/google/", { token: idToken });

    const { access_token, refresh_token, user } = response.data;
    localStorage.setItem("access_token", access_token);
    localStorage.setItem("refresh_token", refresh_token);
    localStorage.setItem("user", JSON.stringify(user || {}));
    const r = user?.role || "student";
    localStorage.setItem("role", r);

    if (r === "instructor") {
      router.push("/instructor/dashboard");
    } else {
      router.push("/student/dashboard");
    }
  } catch (err) {
    const status = err?.response?.status;
    if (status === 403 || status === 401) await signOut(auth);
    error.value = err?.response?.data?.error || err?.message || "Login failed.";
  } finally {
    loading.value = false;
  }
}

async function loginAdmin() {
  adminLoading.value = true;
  adminError.value = "";
  try {
    const response = await axios.post(backendBaseUrl + "/api/auth/admin/login/", {
      username: adminUsername.value.trim(),
      password: adminPassword.value,
    });
    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("refresh_token", response.data.refresh_token);
    localStorage.setItem("role", "admin");
    localStorage.setItem("user", JSON.stringify(response.data.user || {}));
    router.push("/admin/dashboard");
  } catch (err) {
    const apiError = err?.response?.data?.error;
    const networkError = typeof err?.message === "string" && err.message.toLowerCase().includes("network");
    adminError.value = apiError || (networkError ? "Cannot reach backend. Start Django server first." : null) || err?.message || "Login failed.";
  } finally {
    adminLoading.value = false;
  }
}
</script>

<style scoped>

.login-page {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f4f7f9;
  font-family: 'Poppins', -apple-system, sans-serif;
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
  font-family: 'Poppins', sans-serif;
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
  font-family: 'Poppins', sans-serif;
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
/* Perspective wrapper for flip animation */
.perspective-container {
  flex: 1;
  display: flex;
  justify-content: flex-end;
  perspective: 1200px;
}

.login-card-wrapper {
  position: relative;
  width: 100%;
  max-width: 440px;
  transform-style: preserve-3d;
  transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
  display: grid;
  grid-template-columns: 1fr;
}
.login-card-wrapper.is-flipped {
  transform: rotateY(180deg);
}

.login-front, .login-back {
  grid-area: 1 / 1;
  backface-visibility: hidden;
  background: #ffffff;
  border-radius: 24px;
  padding: 2.5rem 3rem;
  box-shadow: 0 15px 35px rgba(15, 23, 42, 0.05);
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  border: 1px solid #f1f5f9;
}
.login-back {
  transform: rotateY(180deg);
}

.login-card-header h2 {
  font-family: 'Poppins', sans-serif;
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
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  border-radius: 12px;
  padding: 0.85rem 1.25rem;
  font-size: 0.9rem;
  color: #065f46;
}
.domain-notice strong { font-weight: 600; color: #064e3b; }

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
  font-family: 'Poppins', sans-serif;
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

/* Admin Form Styles */
.login-form { display: flex; flex-direction: column; gap: 1.25rem; }
.field-group { display: flex; flex-direction: column; gap: 0.5rem; }
.field-group label { font-family: 'Poppins', sans-serif; font-size: 0.85rem; font-weight: 700; color: #1e293b; }

.input-wrap { position: relative; }
.input-icon { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: #64748b; pointer-events: none; }

.input-wrap input {
  width: 100%;
  padding: 0.9rem 1.25rem 0.9rem 2.8rem;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  font-family: inherit;
  font-size: 0.95rem;
  color: #1e293b;
  background: #f8fafc;
  outline: none;
  transition: all 0.2s;
  box-sizing: border-box;
}
.input-wrap input::placeholder { color: #94a3b8; }
.input-wrap input:focus {
  border-color: #1D3461;
  box-shadow: 0 0 0 4px rgba(29, 52, 97, 0.1);
  background: #fff;
}

.toggle-btn {
  position: absolute; right: 0.75rem; top: 50%; transform: translateY(-50%);
  background: #f1f5f9; border: 1px solid #e2e8f0; color: #64748b;
  font-weight: 600; border-radius: 8px; padding: 0.3rem 0.75rem;
  font-size: 0.75rem; cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.toggle-btn:hover { background: #e2e8f0; color: #1e293b; }

.btn-primary {
  width: 100%; padding: 1rem;
  background: #1D3461; color: #fff;
  border: none; border-radius: 12px;
  font-family: inherit; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; transition: all 0.2s; margin-top: 0.5rem;
}
.btn-primary:hover:not(:disabled) {
  background: #162a4f;
  transform: translateY(-1px);
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
</style>

