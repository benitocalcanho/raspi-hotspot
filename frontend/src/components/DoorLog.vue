<template>
  <div class="door-log">
    <h2>{{ $t('doorLog.title') }}</h2>
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
      </tbody>
    </table>
    <button @click="fetchLog">{{ $t('doorLog.refresh') }}</button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const log = ref([])
const { t } = useI18n()

function formatDate(ts) {
  return new Date(ts).toLocaleString()
}

async function fetchLog() {
  const res = await fetch('/api/door/log?limit=50')
  if (res.ok) {
    log.value = await res.json()
  }
}

onMounted(fetchLog)
</script>

<style scoped>
.door-log {
  max-width: 500px;
  margin: 1em auto;
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
</style>
