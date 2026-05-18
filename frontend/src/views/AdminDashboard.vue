<template>
  <div>
    <h2>Admin Dashboard</h2>

    <!-- Overview cards -->
    <div class="cards" v-if="overview">
      <div class="card">
        <span class="num">{{ overview.total_users }}</span>
        <span class="lbl">Total Users</span>
      </div>
      <div class="card">
        <span class="num">{{ overview.active_users }}</span>
        <span class="lbl">Active Users</span>
      </div>
      <div class="card">
        <span class="num">{{ overview.total_audit_events }}</span>
        <span class="lbl">Audit Events</span>
      </div>
      <div class="card ngrok">
        <span class="num small">{{ overview.ngrok_url || 'Offline' }}</span>
        <span class="lbl">ngrok URL</span>
        <button @click="restartNgrok" class="btn-sm">Restart</button>
      </div>
      <div class="card tz-info">
        <span class="num small">{{ overview.timezone_name }} (UTC{{ overview.timezone_offset >= 0 ? '+' : '' }}{{ overview.timezone_offset }})</span>
        <span class="lbl">System Timezone</span>
        <span class="num small">{{ overview.system_time }}</span>
        <span class="lbl">System Time</span>
      </div>
    </div>

    <div class="tabs">
      <button
        v-for="item in adminTabs"
        :key="item.key"
        :class="{active: tab === item.key}"
        @click="goToTab(item.key)"
      >
        {{ item.label }}
      </button>
    </div>

    <!-- Door Log tab -->
    <section v-if="tab === 'doorlog'">
      <h3>Door Log</h3>
      <DoorLog />
    </section>

    <!-- Users tab -->
    <section v-if="tab === 'users'">
      <div class="section-header">
        <h3>User Management</h3>
        <button @click="showCreate = !showCreate" class="btn-primary">+ New User</button>
      </div>

      <form v-if="showCreate" @submit.prevent="createUser" class="create-form">
        <input v-model="newUser.username" placeholder="Username" required />
        <input v-model="newUser.password" type="password" placeholder="Password (guest min 4, others min 8)" required />
        <select v-model="newUser.role">
          <option value="user">User</option>
          <option value="guest">Guest</option>
          <option value="cleaner">Cleaner</option>
          <option value="admin">Admin</option>
        </select>
        <button type="submit">Create</button>
        <p v-if="createError" class="error">{{ createError }}</p>
      </form>

      <UserTable :users="users" @refresh="loadUsers" />
    </section>

    <!-- Button History tab -->
    <section v-if="tab === 'buttonhistory'">
      <h3>Button History</h3>
      <ButtonHistoryTable />
    </section>

    <!-- Audit tab -->
    <section v-if="tab === 'audit'">
      <h3>Audit Log</h3>
      <p v-if="auditError" class="error">{{ auditError }}</p>
      <AuditLog :entries="auditEntries" />
      <button
        v-if="auditPage < auditPages"
        @click="loadMoreAudit"
        class="btn-sm mt"
        :disabled="auditLoading"
      >
        {{ auditLoading ? 'Loading...' : `Load more (${auditEntries.length}/${auditTotal})` }}
      </button>
    </section>


    <!-- ngrok Tunnel tab -->
    <section v-if="tab === 'settings'">
      <h3>ngrok Tunnel Settings</h3>
      <p class="hint">Changes take effect immediately — no restart needed.</p>
      <SettingsPanel :onlySection="null" />
    </section>

    <!-- Email tab -->
    <section v-if="tab === 'email'">
      <h3>Email Notifications</h3>
      <p class="hint">Configure SMTP server and recipient for notification emails. These settings are used to send alerts when a user presses a button.</p>
      <SettingsPanel :onlySection="'email'" />
    </section>

    <!-- Calendar tab -->
    <section v-if="tab === 'calendar'">
      <h3>Google Calendar Settings</h3>
      <SettingsPanel :onlySection="'ical'" />
      <SettingsPanel :onlySection="'guest_password'" />
      <SettingsPanel :onlySection="'schedule'" />
      <SettingsPanel :onlySection="'cleaner'" />
      <div class="btn-row mt">
        <button @click="triggerSync" :disabled="syncing" class="btn-primary">
          {{ syncing ? 'Syncing…' : 'Sync Now' }}
        </button>
        <button @click="restartScheduler" :disabled="restarting" class="btn-secondary">
          {{ restarting ? 'Restarting…' : 'Apply Schedule Changes' }}
        </button>
      </div>
      <div v-if="syncDetails" class="sync-summary">
        <p v-for="(msg, i) in syncMessages" :key="i" :class="msg.type">{{ msg.text }}</p>
      </div>
      <p v-if="syncError" class="error">{{ syncError }}</p>
      <p v-if="restartMsg" class="success">{{ restartMsg }}</p>
      <p v-if="restartError" class="error">{{ restartError }}</p>
    </section>

    <!-- WiFi Networks tab -->
    <section v-if="tab === 'wifi'">
      <h3>WiFi Networks</h3>
      <p class="hint">Manage the networks your Raspberry Pi can connect to. Use this when moving the Pi to a new location with a different WiFi.</p>
      <WifiManager />
    </section>

    <!-- Door Images tab -->
    <section v-if="tab === 'doors'">
      <h3>Door Images</h3>
      <p class="hint">Upload background photos shown on the guest dashboard door cards.</p>

      <div class="door-upload-grid">
        <div v-for="door in doorSlots" :key="door.key" class="door-slot">
          <h4>{{ door.label }}</h4>
          <div class="door-preview" :style="doorImages[door.key] ? `background-image:url('${doorImages[door.key]}?t=${cacheBust}')` : ''">
            <span v-if="!doorImages[door.key]" class="no-img">No image uploaded</span>
          </div>
          <label class="upload-label">
            <input type="file" accept="image/*" @change="uploadDoorImage(door.key, $event)" />
            Choose photo
          </label>
          <p v-if="doorUploadMsg[door.key]" class="success">{{ doorUploadMsg[door.key] }}</p>
          <p v-if="doorUploadErr[door.key]" class="error">{{ doorUploadErr[door.key] }}</p>
        </div>
      </div>
    </section>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ButtonHistoryTable from '../components/ButtonHistoryTable.vue'
import DoorLog from '../components/DoorLog.vue'
import api from '../api.js'
import UserTable from '../components/UserTable.vue'
import AuditLog from '../components/AuditLog.vue'
import SettingsPanel from '../components/SettingsPanel.vue'
import WifiManager from '../components/WifiManager.vue'

// ...existing code...
const route = useRoute()
const router = useRouter()
const adminTabs = [
  { key: 'users', slug: 'users', label: 'Users' },
  { key: 'audit', slug: 'audit', label: 'Audit Log' },
  { key: 'calendar', slug: 'calendar', label: 'Calendar Sync' },
  { key: 'settings', slug: 'ngrok', label: 'ngrok Tunnel' },
  { key: 'email', slug: 'email', label: 'Email' },
  { key: 'wifi', slug: 'wifi', label: 'WiFi Networks' },
  { key: 'doors', slug: 'door-images', label: 'Door Images' },
  { key: 'doorlog', slug: 'door-log', label: 'Door Log' },
  { key: 'buttonhistory', slug: 'button-history', label: 'Button History' },
]
const tabBySlug = Object.fromEntries(adminTabs.map((item) => [item.slug, item.key]))
const slugByTab = Object.fromEntries(adminTabs.map((item) => [item.key, item.slug]))
const tab = computed(() => tabBySlug[route.params.tab] || 'users')
const overview = ref(null)
const users = ref([])
const auditEntries = ref([])
const auditPage = ref(1)
const auditPages = ref(1)
const auditTotal = ref(0)
const auditLoading = ref(false)
const auditError = ref('')
const auditPerPage = 50
const showCreate = ref(false)
const createError = ref('')
const syncing = ref(false)
const syncDetails = ref(null)
const syncError = ref('')

function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso + 'T12:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' })
}

const syncMessages = computed(() => {
  const d = syncDetails.value
  if (!d) return []
  if (d.status === 'no_url')
    return [{ type: 'warn', text: 'No iCal URL configured — go to Calendar Settings and paste the URL.' }]
  if (d.status === 'fetch_error')
    return [{ type: 'error', text: `Could not fetch calendar: ${d.error}` }]
  if (d.status === 'error')
    return [{ type: 'error', text: `Sync error: ${d.error}` }]
  if (d.status === 'pending_checkin')
    return [{ type: 'info', text: `Calendar event found: "${d.guest_event_title}". Guest access will activate at check-in time.` }]
  if (d.status === 'checked_out')
    return [{ type: 'success', text: `Checkout passed for "${d.guest_event_title}". Guest access is removed and cleaner access is active.` }]
  const msgs = []
  if (d.guest_created)
    msgs.push({ type: 'success', text: `Guest account created: ${d.guest_username} (from "${d.guest_event_title}") — active until ${formatDate(d.guest_valid_until)}` })
  if (d.guest_updated)
    msgs.push({ type: 'info', text: `Guest account kept: ${d.guest_username} — stay active until ${formatDate(d.guest_valid_until)}` })
  if (d.guests_deleted > 0)
    msgs.push({ type: 'success', text: `${d.guests_deleted} guest account(s) deleted.` })
  if (d.cleaner_created)
    msgs.push({ type: 'success', text: 'Cleaner account created and activated.' })
  if (d.cleaner_activated)
    msgs.push({ type: 'success', text: 'Cleaner account activated.' })
  if (d.cleaner_deactivated)
    msgs.push({ type: 'info', text: 'Cleaner account deactivated — guest is in the property.' })
  if (!msgs.length)
    msgs.push({ type: 'info', text: 'Calendar checked — no changes needed.' })
  return msgs
})
const restarting = ref(false)
const restartMsg = ref('')
const restartError = ref('')
const scheduleInfo = ref(null)

// Door images
const doorSlots = [
  { key: 'building_door', label: 'Building Door' },
  { key: 'apartment_door', label: 'Apartment Door' },
]
const doorImages = ref({ building_door: null, apartment_door: null })
const doorUploadMsg = ref({ building_door: '', apartment_door: '' })
const doorUploadErr = ref({ building_door: '', apartment_door: '' })
const cacheBust = ref(Date.now())

const newUser = ref({ username: '', password: '', role: 'user' })

function goToTab(key) {
  router.push(`/admin/${slugByTab[key] || 'users'}`)
}

onMounted(async () => {
  await Promise.all([loadOverview(), loadUsers(), loadScheduleInfo(), loadDoorImages()])

  // Auto-refresh audit log when Audit Log tab is active
  let auditInterval = null
  watch(tab, (val) => {
    if (val === 'audit') {
      loadAudit({ page: 1, append: false })
      auditInterval = setInterval(() => {
        if (auditPage.value === 1 && !auditLoading.value) {
          loadAudit({ page: 1, append: false, silent: true })
        }
      }, 5000)
    } else if (auditInterval) {
      clearInterval(auditInterval)
      auditInterval = null
    }
  }, { immediate: true })
})

watch(
  () => route.params.tab,
  (slug) => {
    if (!tabBySlug[slug]) {
      router.replace('/admin/users')
    }
  },
  { immediate: true }
)

async function loadDoorImages() {
  try {
    const { data } = await api.get('/uploads/images')
    doorImages.value = data
  } catch (_) {}
}

async function uploadDoorImage(key, event) {
  const file = event.target.files[0]
  if (!file) return
  doorUploadMsg.value[key] = ''
  doorUploadErr.value[key] = ''
  const form = new FormData()
  form.append('file', file)
  try {
    const { data } = await api.post(`/uploads/images/${key}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    doorImages.value[key] = data.url
    cacheBust.value = Date.now()
    doorUploadMsg.value[key] = 'Image uploaded successfully.'
    setTimeout(() => { doorUploadMsg.value[key] = '' }, 3000)
  } catch (e) {
    doorUploadErr.value[key] = e.response?.data?.error || 'Upload failed.'
  }
}

async function loadScheduleInfo() {
  try {
    const { data } = await api.get('/admin/settings')
    scheduleInfo.value = {
      checkout: data.values['CHECKOUT_TIME']?.value || '12:00',
      checkin:  data.values['CHECKIN_TIME']?.value  || '14:00',
    }
  } catch (_) {}
}

async function loadOverview() {
  const { data } = await api.get('/admin/overview')
  overview.value = data
}

async function loadUsers() {
  const { data } = await api.get('/admin/users')
  users.value = data
}

async function loadAudit({ page = 1, append = false, silent = false } = {}) {
  auditLoading.value = true
  if (!silent) auditError.value = ''
  try {
    const { data } = await api.get(`/admin/audit?page=${page}&per_page=${auditPerPage}`)
    auditEntries.value = append ? [...auditEntries.value, ...data.items] : data.items
    auditPage.value = data.page
    auditPages.value = data.pages || 1
    auditTotal.value = data.total || auditEntries.value.length
  } catch (e) {
    auditError.value = e.response?.data?.error || 'Could not load audit log.'
  } finally {
    auditLoading.value = false
  }
}

async function loadMoreAudit() {
  if (auditLoading.value || auditPage.value >= auditPages.value) return
  await loadAudit({ page: auditPage.value + 1, append: true })
}

async function createUser() {
  createError.value = ''
  try {
    await api.post('/admin/users', newUser.value)
    newUser.value = { username: '', password: '', role: 'user' }
    showCreate.value = false
    await loadUsers()
  } catch (e) {
    createError.value = e.response?.data?.error || 'Failed to create user.'
  }
}

async function restartNgrok() {
  await api.post('/admin/ngrok/restart')
  await loadOverview()
}

async function restartScheduler() {
  restarting.value = true
  restartMsg.value = ''
  restartError.value = ''
  try {
    const { data } = await api.post('/admin/scheduler/restart')
    restartMsg.value = `Scheduler restarted — checkout: ${data.checkout_time}, check-in: ${data.checkin_time}`
    await loadScheduleInfo()
    setTimeout(() => { restartMsg.value = '' }, 5000)
  } catch (e) {
    restartError.value = e.response?.data?.error || 'Failed to restart scheduler.'
  } finally {
    restarting.value = false
  }
}

async function triggerSync() {
  syncing.value = true
  syncDetails.value = null
  syncError.value = ''
  try {
    const { data } = await api.post('/calendar/sync')
    syncDetails.value = data
    await loadUsers()
  } catch (e) {
    syncError.value = e.response?.data?.error || 'Sync failed.'
  } finally {
    syncing.value = false
  }
}
</script>

<style scoped>
h2 { margin-bottom: 1.2rem; }
.cards { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.card {
  background: white; border-radius: 10px; padding: 1.2rem 1.5rem;
  flex: 1; min-width: 160px; display: flex; flex-direction: column;
  box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}
.num { font-size: 1.8rem; font-weight: 700; color: #0f3460; }
.num.small { font-size: 0.9rem; word-break: break-all; }
.lbl { font-size: 0.8rem; color: #888; margin-top: 0.2rem; }
.tabs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1.5rem; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
.tabs button {
  padding: 0.4rem 1rem; border: none; background: none; cursor: pointer;
  font-size: 0.95rem; border-radius: 6px 6px 0 0; color: #666;
  flex: 0 0 auto; white-space: nowrap;
}
.tabs button.active { background: #0f3460; color: white; }
.section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
.btn-primary {
  padding: 0.5rem 1rem; background: #0f3460; color: white;
  border: none; border-radius: 6px; cursor: pointer;
}
.btn-sm { padding: 0.3rem 0.7rem; background: #eee; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; }
.btn-secondary {
  padding: 0.5rem 1rem; background: #6c757d; color: white;
  border: none; border-radius: 6px; cursor: pointer;
}
.btn-secondary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-row { display: flex; gap: 0.75rem; flex-wrap: wrap; align-items: center; margin-bottom: 0.75rem; }
.schedule-info { display: flex; gap: 1.5rem; margin-bottom: 1rem; font-size: 0.9rem; color: #555; }
.create-form { background: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; }
.create-form input, .create-form select {
  padding: 0.5rem; border: 1px solid #ddd; border-radius: 4px; font-size: 0.9rem;
}
.create-form button { padding: 0.5rem 1rem; background: #27ae60; color: white; border: none; border-radius: 4px; cursor: pointer; }
.error { color: #e74c3c; font-size: 0.88rem; }
.success { color: #27ae60; font-size: 0.9rem; margin-top: 0.5rem;}
.info { color: #2980b9; font-size: 0.9rem; margin-top: 0.5rem; }
.warn { color: #e67e22; font-size: 0.9rem; margin-top: 0.5rem; }
.sync-summary { margin-top: 0.5rem; }
.hint { color: #666; margin-bottom: 1rem; }
.hint code { background: #f0f0f0; padding: 0.2rem 0.4rem; border-radius: 3px; font-size: 0.85rem; }
.mt { margin-top: 0.75rem; }
.door-upload-grid { display: flex; gap: 1.5rem; flex-wrap: wrap; }
.door-slot { flex: 1; min-width: 260px; background: white; border-radius: 10px; padding: 1.2rem; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.door-slot h4 { margin-bottom: 0.75rem; color: #0f3460; }
.door-preview {
  width: 100%; height: 200px; border-radius: 6px; background: #e8eaf0;
  background-size: cover; background-position: center;
  display: flex; align-items: center; justify-content: center;
  margin-bottom: 0.75rem;
}
.no-img { color: #aaa; font-size: 0.85rem; }
.upload-label {
  display: inline-block; padding: 0.45rem 1rem;
  background: #0f3460; color: white; border-radius: 6px;
  cursor: pointer; font-size: 0.9rem;
}
.upload-label input[type="file"] { display: none; }
</style>
