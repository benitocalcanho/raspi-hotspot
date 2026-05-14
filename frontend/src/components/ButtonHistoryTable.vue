<template>
  <div class="button-history-wrap">
    <p v-if="error" class="error">{{ error }}</p>
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
    <button v-if="page < pages" class="btn-sm" @click="loadMore" :disabled="loading">
      {{ loading ? 'Loading...' : `Load more (${entries.length}/${total})` }}
    </button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'

const entries = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const loading = ref(false)
const error = ref('')
const perPage = 50

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

async function loadButtonHistory({ nextPage = 1, append = false } = {}) {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get(`/admin/audit?event=button_press&page=${nextPage}&per_page=${perPage}`)
    entries.value = append ? [...entries.value, ...data.items] : data.items
    page.value = data.page
    pages.value = data.pages || 1
    total.value = data.total || entries.value.length
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not load button history.'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loading.value || page.value >= pages.value) return
  await loadButtonHistory({ nextPage: page.value + 1, append: true })
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
.error {
  color: #c0392b;
  font-size: 0.9rem;
}
.btn-sm {
  padding: 0.35rem 0.75rem;
  background: #eef2f7;
  color: #344054;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.85rem;
}
.btn-sm:disabled {
  cursor: wait;
  opacity: 0.7;
}
</style>
