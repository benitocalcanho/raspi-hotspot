<template>
  <nav class="navbar">
    <div class="brand">{{ $t('app_name') }}</div>
    <div class="links">
      <router-link v-if="authStore.user?.role === 'admin'" to="/admin">{{ $t('nav_admin') }}</router-link>
      <router-link v-if="authStore.user?.role === 'cleaner'" to="/guest">{{ $t('nav_cleaner') }}</router-link>
      <router-link v-if="authStore.user?.role === 'guest'" to="/guest">{{ $t('nav_guest') }}</router-link>
      <router-link v-if="authStore.user?.role === 'user'" to="/dashboard">{{ $t('nav_dashboard') }}</router-link>
      <router-link v-if="authStore.user?.role === 'admin'" to="/gpio">{{ $t('nav_gpio') }}</router-link>
      <button @click="handleLogout" class="logout">{{ $t('nav_signout') }}</button>
    </div>
  </nav>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  display: flex; align-items: center; justify-content: space-between;
  background: #0f3460; color: white; padding: 0.75rem 1.5rem;
  position: sticky; top: 0; z-index: 100;
}
.brand { font-weight: 700; font-size: 1.1rem; }
.links { display: flex; align-items: center; gap: 1rem; }
.links a { color: rgba(255,255,255,0.8); text-decoration: none; font-size: 0.9rem; }
.links a.router-link-active { color: white; font-weight: 600; }
.logout {
  background: rgba(255,255,255,0.15); border: none; color: white;
  padding: 0.35rem 0.8rem; border-radius: 5px; cursor: pointer; font-size: 0.9rem;
}
.logout:hover { background: rgba(255,255,255,0.25); }
</style>
