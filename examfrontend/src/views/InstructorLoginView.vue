<template>
  <div class="login-page">
    <!-- Left branding panel -->
    <div class="login-brand">
      <div class="brand-content">
        <div class="brand-logo">
          <span class="brand-name">AI-Vigilation</span>
        </div>
        <div class="brand-tagline">
          <h1>Instructor<br/>Portal</h1>
          <p>Sign in to manage your courses, upload exams, and monitor student progress.</p>
        </div>
        <div class="brand-features">
          <div class="feature-item"><div class="feature-dot"></div><span>Manage courses & exams</span></div>
          <div class="feature-item"><div class="feature-dot"></div><span>Real-time exam progress</span></div>
          <div class="feature-item"><div class="feature-dot"></div><span>Proctoring insights</span></div>
        </div>
      </div>
    </div>

    <!-- Right login panel -->
    <div class="login-form-panel">
      <div class="login-card">
        <div class="login-header">
          <h2>Instructor Sign In</h2>
          <p>Access your teaching dashboard</p>
        </div>

        <form class="login-form" @submit.prevent="loginInstructor">
          <div class="field-group">
            <label for="username">Username</label>
            <div class="input-wrap">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>
              </svg>
              <input id="username" v-model="username" type="text" placeholder="Enter username" required autocomplete="username"/>
            </div>
          </div>

          <div class="field-group">
            <label for="password">Password</label>
            <div class="input-wrap">
              <svg class="input-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                id="password"
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

          <button type="submit" class="btn-primary" :disabled="loading">
            {{ loading ? 'Signing in...' : 'Sign in' }}
          </button>
        </form>

        <p v-if="error" class="error-msg">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          {{ error }}
        </p>

        <button class="btn-back" @click="router.push('/')">← Back</button>
      </div>
    </div>
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

async function loginInstructor() {
  loading.value = true;
  error.value = "";
  try {
    const response = await axios.post(`${backendBaseUrl}/api/auth/instructor/login/`, {
      username: username.value.trim(),
      password: password.value,
    });
    localStorage.setItem("access_token", response.data.access_token);
    localStorage.setItem("refresh_token", response.data.refresh_token);
    localStorage.setItem("role", "instructor");
    localStorage.setItem("user", JSON.stringify(response.data.user || {}));
    router.push("/instructor/dashboard");
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
</style>
