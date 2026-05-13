<template>
  <div class="door-log">
    <h2>{{ $t('doorLog.title') }}</h2>
    <div class="status-row">
      <span>{{ $t('doorLog.current') }}:</span>
      <strong>{{ $t('doorLog.' + status.state) }}</strong>
      <span v-if="!status.enabled" class="muted">{{ $t('doorLog.disabled') }}</span>
    </div>
    <table>
      <thead>
        <tr>
          <th>{{ $t('doorLog.timestamp') }}</th>
          <th>{{ $t('doorLog.state') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in log" :key="entry.timestamp">
          <td>{{ formatDate(entry.timestamp) }}</td>
          <td>{{ $t('doorLog.' + entry.state) }}</td>
        </tr>
        <tr v-if="!log.length">
          <td colspan="2" class="muted">{{ $t('doorLog.empty') }}</td>
        </tr>
      </tbody>
    </table>
    <button @click="loadDoorLog">{{ $t('doorLog.refresh') }}</button>
    <p v-if="error" class="error">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const log = ref([])
const status = ref({ state: 'unknown', enabled: false })
const error = ref('')

function formatDate(ts) {
  return new Date(ts).toLocaleString()
}

async function loadDoorLog() {
  error.value = ''
  try {
    const [{ data: statusData }, { data: logData }] = await Promise.all([
      api.get('/door/status'),
      api.get('/door/log?limit=50'),
    ])
    status.value = statusData
    log.value = logData
  } catch (e) {
    error.value = e.response?.data?.error || 'Could not load door log.'
  }
}

onMounted(loadDoorLog)
</script>

<style scoped>
.door-log {
  max-width: 500px;
  margin: 1em auto;
}
.status-row {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.75rem;
}
table {
  width: 100%;
  border-collapse: collapse;
}
th, td {
  border: 1px solid #ccc;
  padding: 0.5em;
  text-align: left;
}
.muted {
  color: #777;
  font-size: 0.9rem;
}
.error {
  color: #c0392b;
  margin-top: 0.5rem;
}
</style>
