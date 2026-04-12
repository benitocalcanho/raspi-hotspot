import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api.js'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const isLoggedIn = computed(() => !!user.value)

  async function login(username, password) {
    const { data } = await api.post('/auth/login', { username, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    user.value = data.user
    return data.user
  }

  async function logout() {
    try { await api.post('/auth/logout') } catch { /* ignore */ }
    localStorage.clear()
    user.value = null
  }

  async function fetchCurrentUser() {
    try {
      const { data } = await api.get('/auth/me')
      user.value = data
    } catch {
      localStorage.clear()
      user.value = null
    }
  }

  return { user, isLoggedIn, login, logout, fetchCurrentUser }
})
