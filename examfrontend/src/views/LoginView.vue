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
      <div class="login-form-panel">
        <div class="login-card-wrapper">
          
          <!-- Front Card (Student / Instructor) -->
          <div v-if="!showAdminLogin" class="login-card login-front">
            <div class="login-card-header">
              <div class="login-card-brand"><span class="login-card-brand__mark">AI</span><span>AI-Vigilation</span></div>
              <h2>Welcome back</h2>
              <p>Sign in with your DNSC account.</p>
            </div>

            <p class="domain-notice">Restricted to <strong>@{{ schoolDomain }}</strong> accounts</p>

            <button class="btn-google" @click="loginWithGoogle" :disabled="loading" id="google-login-btn">
              <svg class="google-icon" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <span>{{ loading ? 'Signing in...' : 'Continue with DNSC Google' }}</span>
            </button>

            <div class="divider">
              <span>or</span>
            </div>

            <button type="button" class="login-text-action" @click="openAdminLogin" id="admin-login-btn">
              Admin account
            </button>

            <p v-if="error" class="error-msg">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ error }}
            </p>
            
          </div>

          <!-- Back Card (Admin) -->
          <div v-else class="login-card login-back">
            <div class="login-card-header">
              <div class="login-card-brand"><span class="login-card-brand__mark">AI</span><span>AI-Vigilation</span></div>
              <h2>Admin account</h2>
              <p>Sign in with your administrator credentials.</p>
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
                {{ adminLoading ? 'Signing in...' : 'Log in' }}
              </button>
            </form>

            <p v-if="adminError" class="error-msg">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
              {{ adminError }}
            </p>

            <button type="button" class="login-text-action" @click="returnToSchoolLogin" id="back-to-login-btn">
              Back to DNSC account sign in
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
import { useRoute, useRouter } from "vue-router";
import axios from "axios";

const router = useRouter();
const route = useRoute();
const loading = ref(false);
const error = ref("");

const showAdminLogin = ref(route.query.login === "admin");
const adminUsername = ref("");
const adminPassword = ref("");
const showAdminPassword = ref(false);
const adminLoading = ref(false);
const adminError = ref("");

const schoolDomain = import.meta.env.VITE_SCHOOL_DOMAIN || "dnsc.edu.ph";
const backendBaseUrl = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

function openAdminLogin() {
  error.value = "";
  showAdminLogin.value = true;
  router.replace({ path: "/", query: { login: "admin" } });
}

function returnToSchoolLogin() {
  adminError.value = "";
  adminPassword.value = "";
  showAdminLogin.value = false;
  router.replace({ path: "/" });
}

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
  min-height: 100vh;
  overflow-x: clip;
  display: flex;
  flex-direction: column;
  background: linear-gradient(125deg, #f4f7fb 0%, #edf3fa 64%, #f7f1e9 100%);
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
  font-size: 3.3rem;
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

/* Sign-in card */
.login-form-panel {
  position: relative;
  isolation: isolate;
  flex: 1;
  display: flex;
  justify-content: flex-end;
}
.login-form-panel::before,
.login-form-panel::after {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  pointer-events: none;
  content: '';
}
.login-form-panel::before {
  top: -2rem;
  right: -2rem;
  width: 19rem;
  height: 19rem;
  background: rgba(84, 124, 183, 0.17);
  filter: blur(18px);
}
.login-form-panel::after {
  bottom: -3rem;
  left: 1rem;
  width: 13rem;
  height: 13rem;
  background: rgba(233, 177, 80, 0.18);
  filter: blur(22px);
}

.login-card-wrapper {
  position: relative;
  width: 100%;
  max-width: 460px;
}

.login-front, .login-back {
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.86), rgba(255, 255, 255, 0.64));
  -webkit-backdrop-filter: blur(22px) saturate(1.25);
  backdrop-filter: blur(22px) saturate(1.25);
  border: 1px solid rgba(255, 255, 255, 0.82);
  border-radius: 24px;
  padding: 0;
  box-shadow: 0 28px 65px rgba(32, 55, 91, 0.14), 0 5px 15px rgba(32, 55, 91, 0.055);
  display: flex;
  flex-direction: column;
  gap: 0;
  overflow: hidden;
}
.login-card-brand {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.6rem;
  margin-bottom: 1.2rem;
  color: #355579;
  font-size: 0.75rem;
  font-weight: 750;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.login-card-brand__mark {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  border-radius: 9px;
  background: #1D3461;
  color: #fff;
  font-size: 0.78rem;
  letter-spacing: -0.04em;
}

.login-card-header {
  padding: 2rem 2.35rem 0.65rem;
  background: transparent;
  text-align: left;
}
.login-card-header h2 {
  font-family: 'Poppins', sans-serif;
  font-size: 1.75rem;
  font-weight: 800;
  color: #1D3461;
  margin: 0 0 0.35rem;
  letter-spacing: -0.02em;
}
.login-card-header p {
  margin: 0;
  font-size: 0.9rem;
  color: #64748b;
}

.domain-notice {
  margin: 0.65rem 2.35rem 0;
  font-size: 0.78rem;
  color: #64748b;
}
.domain-notice strong { font-weight: 600; color: #475569; }
.login-front .btn-google { order: 1; }
.login-front .domain-notice { order: 2; }
.login-front .divider { order: 3; }
.login-front .login-text-action { order: 4; }
.login-front .error-msg { order: 5; }

.btn-google {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  width: auto;
  min-height: 54px;
  margin: 1.2rem 2.35rem 0;
  padding: 0.8rem 1.25rem;
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(188, 201, 220, 0.85);
  border-radius: 10px;
  font-family: inherit;
  font-size: 0.96rem;
  font-weight: 600;
  color: #1D3461;
  cursor: pointer;
  transition: background 0.2s, border-color 0.2s, box-shadow 0.2s;
}
.btn-google:hover:not(:disabled) {
  background: #fff;
  border-color: #aebdd3;
  box-shadow: 0 5px 14px rgba(29, 52, 97, 0.08);
}
.btn-google:disabled { opacity: 0.6; cursor: not-allowed; }
.google-icon { width: 22px; height: 22px; flex-shrink: 0; }

.divider {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  margin: 1.35rem 2.35rem 0;
  color: #8b9ab0;
  font-size: 0.78rem;
  font-weight: 500;
}
.divider::before, .divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(133, 153, 180, 0.32);
}

.login-text-action {
  align-self: center;
  margin: 0.8rem auto 1.7rem;
  padding: 0.45rem 0.7rem;
  border: 0;
  background: transparent;
  color: #1D3461;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
}
.login-text-action:hover { text-decoration: underline; }
.login-text-action:focus-visible { outline: 2px solid #1D3461; outline-offset: 3px; border-radius: 4px; }

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
  margin: 0 2.35rem 1.5rem;
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
.login-form { display: flex; flex-direction: column; gap: 1rem; margin: 1.35rem 2.35rem 0; }
.field-group { display: flex; flex-direction: column; gap: 0.45rem; }
.field-group label { font-family: 'Poppins', sans-serif; font-size: 0.82rem; font-weight: 700; color: #334663; }

.input-wrap { position: relative; }
.input-icon { position: absolute; left: 1rem; top: 50%; transform: translateY(-50%); color: #64748b; pointer-events: none; }

.input-wrap input {
  width: 100%;
  min-height: 49px;
  padding: 0.8rem 4rem 0.8rem 2.8rem;
  border: 1px solid #d5deea;
  border-radius: 10px;
  font-family: inherit;
  font-size: 0.95rem;
  color: #1e293b;
  background: rgba(255, 255, 255, 0.7);
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
  position: absolute; right: 0.55rem; top: 50%; transform: translateY(-50%);
  background: transparent; border: 0; color: #526784;
  font-weight: 700; border-radius: 6px; padding: 0.4rem 0.65rem;
  font-size: 0.75rem; cursor: pointer; transition: all 0.2s; font-family: inherit;
}
.toggle-btn:hover { background: #edf2f8; color: #1D3461; }

.btn-primary {
  width: 100%; min-height: 50px; padding: 0.85rem 1rem;
  background: #1D3461; color: #fff;
  border: none; border-radius: 10px;
  font-family: inherit; font-size: 0.95rem; font-weight: 600;
  cursor: pointer; transition: background 0.2s, box-shadow 0.2s; margin-top: 0.45rem;
}
.btn-primary:hover:not(:disabled) {
  background: #162a4f;
  box-shadow: 0 6px 16px rgba(29, 52, 97, 0.16);
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
@media (max-width: 540px) {
  .login-card-header { padding: 1.5rem 1.4rem; }
  .btn-google { margin: 1.4rem 1.4rem 0; }
  .domain-notice { margin-left: 1.4rem; margin-right: 1.4rem; }
  .divider { margin-left: 1.4rem; margin-right: 1.4rem; }
  .login-form { margin-left: 1.4rem; margin-right: 1.4rem; }
  .error-msg { margin-left: 1.4rem; margin-right: 1.4rem; }
}
</style>

