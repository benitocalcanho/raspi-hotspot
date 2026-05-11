<template>
  <div class="login-view">
    <h1>{{ $t('sign_in') }}</h1>
    <form @submit.prevent="handleLogin">
      <div class="field">
          <label for="username">{{ $t('username') }}</label>
        <input id="username" v-model="username" required />
      </div>
      <div class="field">
          <label for="password">Password</label>
        <input id="password" v-model="password" type="password" autocomplete="current-password" required />
      </div>
      <p v-if="error" class="error">{{ error }}</p>
      <button type="submit" :disabled="loading">
        {{ loading ? $t('signing_in') : $t('sign_in') }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

const authStore = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const user = await authStore.login(username.value, password.value)
    if (user.role === 'admin') {
      router.push('/admin')
    } else if (['cleaner', 'guest', 'user'].includes(user.role)) {
      router.push('/guest')
    } else {
      router.push('/dashboard')
    }
  } catch (e) {
    error.value = e.response?.data?.error || 'Login failed. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}
.login-card {
  background: white;
  border-radius: 12px;
  padding: 2.5rem;
  width: 100%;
  max-width: 380px;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
}
h1 { font-size: 1.8rem; margin-bottom: 0.25rem; color: #1a1a2e; }
.subtitle { color: #666; margin-bottom: 1.5rem; }
.field { margin-bottom: 1rem; }
.field label { display: block; font-size: 0.85rem; font-weight: 600; margin-bottom: 0.3rem; }
.field input {
  width: 100%; padding: 0.65rem 0.8rem; border: 1px solid #ddd;
  border-radius: 6px; font-size: 1rem; transition: border-color 0.2s;
}
.field input:focus { outline: none; border-color: #0f3460; }
button {
  width: 100%; padding: 0.75rem; background: #0f3460; color: white;
  border: none; border-radius: 6px; font-size: 1rem; cursor: pointer;
  margin-top: 0.5rem; transition: background 0.2s;
}
button:hover:not(:disabled) { background: #16213e; }
button:disabled { opacity: 0.6; cursor: not-allowed; }
.error { color: #e74c3c; font-size: 0.88rem; margin-bottom: 0.5rem; }
</style>
