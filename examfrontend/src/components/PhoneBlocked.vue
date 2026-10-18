<template>
  <main class="phone-blocked">
    <div class="phone-blocked__card">
      <p class="phone-blocked__brand">AI-Vigilation</p>
      <h1>Use a computer to access AI-Vigilation</h1>
      <p>This system is unavailable on phones. Open it on a laptop or desktop computer to sign in and use your account.</p>
    </div>
  </main>
</template>

<style scoped>
.phone-blocked {
  display: grid;
  min-height: 100dvh;
  place-items: center;
  padding: 24px;
  background: #f1f5f9;
}

.phone-blocked__card {
  width: min(100%, 480px);
  padding: 32px;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 31, 58, 0.08);
  text-align: center;
}

.phone-blocked__brand {
  margin-bottom: 20px;
  color: #1d3461;
  font-weight: 700;
}

h1 {
  margin-bottom: 12px;
  color: #0f1f3a;
  font-size: clamp(1.5rem, 6vw, 2rem);
  font-weight: 700;
  line-height: 1.2;
}

.phone-blocked__card > p:last-child {
  color: #475569;
  line-height: 1.6;
}
</style>
