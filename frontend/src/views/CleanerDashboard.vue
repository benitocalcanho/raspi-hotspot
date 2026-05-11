<template>
  <div>
    <h2>{{ $t('cleaner_dashboard_title') }}</h2>

    <div v-if="dashboard" class="welcome">
      {{ $t('cleaner_dashboard_welcome', { username: dashboard.user.username }) }}
    </div>

    <div class="section">
      <h3>{{ $t('gpio_controls') }}</h3>
      <GpioPanel />
    </div>

    <div class="section">
      <h3>{{ $t('recent_logins') }}</h3>
      <AuditLog :entries="dashboard?.recent_logins ?? []" />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'
import AuditLog from '../components/AuditLog.vue'
import GpioPanel from '../components/GpioPanel.vue'

const dashboard = ref(null)

onMounted(async () => {
  const { data } = await api.get('/user/dashboard')
  dashboard.value = data
})
</script>

<style scoped>
h2 { margin-bottom: 1rem; }
.welcome { font-size: 1.05rem; margin-bottom: 1.5rem; color: #555; }
.section { background: white; border-radius: 10px; padding: 1.2rem; margin-bottom: 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
h3 { margin-bottom: 0.75rem; font-size: 1rem; color: #0f3460; }
</style>
