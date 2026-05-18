<template>
  <div class="door-log">
    <div class="door-status">
      <div>
        <span class="lbl">{{ $t('doorLog.current') }}</span>
        <strong :class="['state', status.state]">{{ statusText }}</strong>
      </div>
      <div>
        <span class="lbl">{{ $t('sensor') }}</span>
        <strong>{{ sensorText }}</strong>
      </div>
      <button class="btn-sm" @click="load" :disabled="loading">
        {{ loading ? $t('refreshing') : $t('doorLog.refresh') }}
      </button>
    </div>

    <p v-if="error" class="error">{{ error }}</p>

    <table class="log-table">
      <thead>
        <tr>
          <th>{{ $t('doorLog.timestamp') }}</th>
          <th>{{ $t('doorLog.state') }}</th>
          <th>{{ $t('source') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-if="!events.length">
          <td colspan="3" class="muted">{{ $t('doorLog.empty') }}</td>
        </tr>
        <tr v-for="event in events" :key="event.id">
          <td>{{ formatTimestamp(event.timestamp) }}</td>
          <td>
            <span :class="['state-pill', event.state]">{{ event.state }}</span>
          </td>
          <td>{{ event.source }}</td>
        </tr>
      </tbody>
    </table>
    <button v-if="page < pages" class="btn-sm load-more" @click="loadMore" :disabled="loading">
      {{ loading ? $t('loading') : $t('load_more_count', { shown: events.length, total }) }}
    </button>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import api from '../api.js'

const { t } = useI18n()

const loading = ref(false)
const error = ref('')
const status = ref({ state: 'unknown', enabled: false, pin_number: 23, error: null })
const events = ref([])
const page = ref(1)
const pages = ref(1)
const total = ref(0)
const perPage = 50

const statusText = computed(() => {
  if (status.value.state === 'open') return t('doorLog.open')
  if (status.value.state === 'closed') return t('doorLog.closed')
  return t('doorLog.unknown')
})

const sensorText = computed(() => {
  if (status.value.enabled) return `GPIO${status.value.pin_number}`
  return status.value.error ? `${t('sensor_unavailable')}: ${status.value.error}` : t('sensor_disabled')
})

function formatTimestamp(value) {
  if (!value) return ''
  return new Date(value).toLocaleString()
}

async function load({ nextPage = 1, append = false } = {}) {
  loading.value = true
  error.value = ''
  try {
    const [statusRes, eventsRes] = await Promise.all([
      api.get('/door/status'),
      api.get(`/door/events?page=${nextPage}&limit=${perPage}`),
    ])
    status.value = statusRes.data
    events.value = append ? [...events.value, ...eventsRes.data.items] : eventsRes.data.items
    page.value = eventsRes.data.page
    pages.value = eventsRes.data.pages || 1
    total.value = eventsRes.data.total || events.value.length
  } catch (err) {
    error.value = err.response?.data?.error || 'Could not load door log.'
  } finally {
    loading.value = false
  }
}

async function loadMore() {
  if (loading.value || page.value >= pages.value) return
  await load({ nextPage: page.value + 1, append: true })
}

onMounted(load)
</script>

<style scoped>
.door-log {
  display: grid;
  gap: 1rem;
}

.door-status {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  flex-wrap: wrap;
}

.lbl {
  display: block;
  color: #666;
  font-size: 0.8rem;
}

.state {
  text-transform: uppercase;
}

.state.open {
  color: #b42318;
}

.state.closed {
  color: #027a48;
}

.state.unknown {
  color: #667085;
}

.log-table {
  width: 100%;
  border-collapse: collapse;
}

.load-more {
  justify-self: start;
}

.log-table th,
.log-table td {
  border-bottom: 1px solid #e5e7eb;
  padding: 0.65rem 0.5rem;
  text-align: left;
}

.muted {
  color: #667085;
}

.state-pill {
  border-radius: 999px;
  display: inline-block;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  text-transform: uppercase;
}

.state-pill.open {
  background: #fee4e2;
  color: #b42318;
}

.state-pill.closed {
  background: #dcfae6;
  color: #027a48;
}
</style>
