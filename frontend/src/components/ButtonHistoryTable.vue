<template>
  <div class="button-history-wrap">
    <table v-if="entries.length">
      <thead>
        <tr>
          <th>Date/Time</th>
          <th>User</th>
          <th>Button</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in entries" :key="entry.id">
          <td class="mono">{{ formatDate(entry.timestamp) }}</td>
          <td>{{ entry.username ?? '—' }}</td>
          <td>{{ entry.detail?.button ?? '—' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">No button presses yet.</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const entries = ref([])

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

async function loadButtonHistory() {
  const { data } = await api.get('/admin/audit?event=button_press')
  entries.value = data.items
}

onMounted(loadButtonHistory)
</script>

<style scoped>
.button-history-wrap table {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1rem;
}
.button-history-wrap th, .button-history-wrap td {
  padding: 0.5rem 0.7rem;
  border-bottom: 1px solid #eee;
  text-align: left;
}
.button-history-wrap th {
  background: #f8f8fa;
  font-size: 0.97rem;
}
.mono {
  font-family: monospace;
  font-size: 0.97em;
}
.empty {
  color: #888;
  font-size: 0.97em;
  margin: 1.5rem 0;
}
</style>