<template>
  <div id="app">
    <!-- Language switcher removed: now auto-detects browser language -->
    <NavBar v-if="authStore.isLoggedIn && authStore.user?.role !== 'guest'" />
    <main :class="['main-content', authStore.user?.role === 'guest' ? 'guest' : '']">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import NavBar from './components/NavBar.vue'
import { useAuthStore } from './stores/auth.js'

const authStore = useAuthStore()

onMounted(async () => {
  // Restore session if a token exists in localStorage
  if (localStorage.getItem('access_token')) {
    await authStore.fetchCurrentUser()
  }
})
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  background: #f5f7fa;
  color: #2c3e50;
}
.main-content { padding: 1.5rem; max-width: 1100px; margin: 0 auto; }
.main-content.guest { padding: 0; max-width: 100%; }
</style>
