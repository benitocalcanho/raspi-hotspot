<template>
  <div class="audit-wrap">
    <div class="tz-hint" style="margin-bottom: 0.5em; color: #888; font-size: 0.95em;">
      All times are shown in your browser's local timezone ({{ timezoneName }}).
    </div>
    <table class="audit-log" v-if="entries.length">
      <thead>
        <tr>
          <th>Date/Time</th>
          <th>User</th>
          <th>Event</th>
          <th>IP</th>
          <th>Device</th>
          <th>Language</th>
          <th>Detail</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="entry in entries" :key="entry.id">
          <td class="mono">{{ formatDate(entry.timestamp) }}</td>
          <td><span class="badge user-badge">{{ entry.username }}</span></td>
          <td>
            <span class="badge event-badge" :class="eventClass(entry.event)">{{ formatEvent(entry.event) }}</span>
          </td>
          <td>{{ entry.ip_address }}</td>
          <td>{{ formatClient(entry) }}</td>
          <td>{{ getClientField(entry, 'language') }}</td>
          <td>{{ formatDetail(entry.detail) }}</td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty">No audit log entries found.</div>
  </div>
</template>

<script setup>
// Capitalize and space event names for display
function formatEvent(event) {
  if (!event) return '';
  // Replace underscores with spaces and capitalize
  return event.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
defineProps({ entries: Array })
const timezoneName = Intl.DateTimeFormat().resolvedOptions().timeZone
function formatDate(iso) {
  if (!iso) return ''
  const hasTimezone = /([zZ]|[+\-]\d{2}:\d{2})$/.test(iso)
  const value = hasTimezone ? iso : `${iso}Z`
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false
  });
}
function eventClass(event) {
  if (!event) return '';
  const e = event.toLowerCase();
  if (e.includes('failed') || e.includes('deleted')) return 'fail';
  if (e.includes('button_press')) return 'button';
  if (e.includes('login_success')) return 'ok';
  return 'info';
}
function getClientField(entry, field) {
  return entry?.detail?.client?.[field] || '—'
}
function formatClient(entry) {
  const client = entry?.detail?.client || {}
  const parts = [client.device, client.browser, client.os].filter(Boolean).filter(v => v !== 'Unknown')
  if (parts.length) return parts.join(' · ')
  return entry.user_agent?.split(' ')[0] || '—'
}
function formatDetail(detail) {
  if (!detail) return ''
  if (typeof detail === 'string') return detail
  const clone = JSON.parse(JSON.stringify(detail))
  if (clone.client) delete clone.client
  const keys = Object.keys(clone)
  if (!keys.length) return ''
  return JSON.stringify(clone)
}
</script>

<style scoped>
.event-badge.button {
  background: #fff4e5;
  color: #e67e22;
}
.event-badge.ok {
  background: #e8fde8;
  color: #27ae60;
}
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

.user-badge {
  background: #e8f4fd;
  color: #2980b9;
  padding: 0.15rem 0.5rem;
  border-radius: 20px;
  font-size: 0.85em;
  font-weight: 600;
}

.event-badge {
  margin-right: 0.1em;
  font-size: 0.85em;
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 20px;
  background: #f4f4f4;
  color: #555;
}
.event-badge.info {
  background: #e8f4fd;
  color: #2980b9;
}
.event-badge.fail {
  background: #fde8e8;
  color: #c0392b;
}
</style>
