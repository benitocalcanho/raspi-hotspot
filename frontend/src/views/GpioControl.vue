<template>
  <div>
    <h2>GPIO Control</h2>
    <GpioPanel :showAdd="authStore.user?.role === 'admin'" />
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth.js'
import GpioPanel from '../components/GpioPanel.vue'
const authStore = useAuthStore()
</script>
