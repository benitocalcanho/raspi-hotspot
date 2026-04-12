<template>
  <div class="audit-wrap">
    <table v-if="entries.length">
      <thead>
        <tr>
          <th>Time</th>
          <th>User</th>
          <th>Event</th>
          <th>IP Address</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in entries" :key="entry.id">
          <td class="mono">{{ formatDate(entry.timestamp) }}</td>
          <td>{{ entry.username ?? '—' }}</td>
          <td><span :class="['badge', eventClass(entry.event)]">{{ entry.event }}</span></td>
          <td class="mono">{{ entry.ip_address ?? '—' }}</td>
          <td class="mono small">{{ entry.detail ?? '' }}</td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">No audit events yet.</p>
  </div>
</template>

<script setup>
defineProps({ entries: Array })

function formatDate(iso) {
  return new Date(iso).toLocaleString()
}

function eventClass(event) {
  if (event.includes('success') || event.includes('created')) return 'ok'
  if (event.includes('failed') || event.includes('deleted')) return 'fail'
  return 'info'
}
</script>

<style scoped>
.audit-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { padding: 0.55rem 0.8rem; text-align: left; border-bottom: 1px solid #f0f0f0; }
th { background: #f8f9fa; font-weight: 600; color: #555; }
.badge { padding: 0.15rem 0.5rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge.ok { background: #e8fde8; color: #27ae60; }
.badge.fail { background: #fde8e8; color: #c0392b; }
.badge.info { background: #e8f4fd; color: #2980b9; }
.mono { font-family: monospace; }
.small { font-size: 0.78rem; color: #888; max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.empty { color: #888; padding: 0.75rem 0; }
</style>
