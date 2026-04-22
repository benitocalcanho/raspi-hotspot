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
      <button :class="{active: tab==='users'}" @click="tab='users'">Users</button>
      <button :class="{active: tab==='audit'}" @click="tab='audit'">Audit Log</button>
      <button :class="{active: tab==='calendar'}" @click="tab='calendar'">Calendar Sync</button>
      <button :class="{active: tab==='settings'}" @click="tab='settings'">Settings</button>
      <button :class="{active: tab==='email'}" @click="tab='email'">Email</button>
      <button :class="{active: tab==='doors'}" @click="tab='doors'">Door Images</button>
      <button :class="{active: tab==='buttonhistory'}" @click="tab='buttonhistory'">Button History</button>
    </div>

    <!-- Users tab -->
    <section v-if="tab === 'users'">
      <div class="section-header">
        <h3>User Management</h3>
        <button @click="showCreate = !showCreate" class="btn-primary">+ New User</button>
      </div>
    <!-- Button History tab -->
    <section v-if="tab === 'buttonhistory'">
      <h3>Button History</h3>
      <ButtonHistoryTable />
    </section>

      <form v-if="showCreate" @submit.prevent="createUser" class="create-form">
        <input v-model="newUser.username" placeholder="Username" required />
        <input v-model="newUser.password" type="password" placeholder="Password (min 8 chars)" required />
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

    <!-- Audit tab -->
    <section v-if="tab === 'audit'">
      <h3>Audit Log</h3>
      <AuditLog :entries="auditEntries" />
      <button @click="loadAudit" class="btn-sm mt">Load more</button>
    </section>

    <!-- Settings tab -->
    <section v-if="tab === 'settings'">
      <h3>App Settings</h3>
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
      <h3>Google Calendar Sync</h3>
      <p class="hint">
        Set your private iCal URL in <strong>Settings</strong>. Events starting today will create the guest account at check-in time.
      </p>

      <div class="schedule-info" v-if="scheduleInfo">
        <span>Check-out: <strong>{{ scheduleInfo.checkout }}</strong></span>
        <span>Check-in: <strong>{{ scheduleInfo.checkin }}</strong></span>
      </div>

      <div class="btn-row">
        <button @click="triggerSync" :disabled="syncing" class="btn-primary">
          {{ syncing ? 'Syncing…' : 'Sync Now' }}
        </button>
        <button @click="restartScheduler" :disabled="restarting" class="btn-secondary">
          {{ restarting ? 'Restarting…' : 'Apply Schedule Changes' }}
        </button>
      </div>
      <p v-if="syncResult !== null" class="success">Created {{ syncResult }} user(s).</p>
      <p v-if="syncError" class="error">{{ syncError }}</p>
      <p v-if="restartMsg" class="success">{{ restartMsg }}</p>
      <p v-if="restartError" class="error">{{ restartError }}</p>
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
import { ref, onMounted } from 'vue'
import ButtonHistoryTable from '../components/ButtonHistoryTable.vue'
import api from '../api.js'
import UserTable from '../components/UserTable.vue'
import AuditLog from '../components/AuditLog.vue'
import SettingsPanel from '../components/SettingsPanel.vue'

// ...existing code...
const tab = ref('users')
const overview = ref(null)
const users = ref([])
const auditEntries = ref([])
const showCreate = ref(false)
const createError = ref('')
const syncing = ref(false)
const syncResult = ref(null)
const syncError = ref('')
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


import { watch } from 'vue'

onMounted(async () => {
  await Promise.all([loadOverview(), loadUsers(), loadAudit(), loadScheduleInfo(), loadDoorImages()])

  // Auto-refresh audit log when Audit Log tab is active
  let auditInterval = null
  watch(tab, (val) => {
    if (val === 'audit') {
      loadAudit()
      auditInterval = setInterval(loadAudit, 5000)
    } else if (auditInterval) {
      clearInterval(auditInterval)
      auditInterval = null
    }
  }, { immediate: true })
})

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

async function loadAudit() {
  const { data } = await api.get('/admin/audit')
  auditEntries.value = data.items
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
  syncResult.value = null
  syncError.value = ''
  try {
    const { data } = await api.post('/calendar/sync')
    syncResult.value = data.users_created
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
.tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; border-bottom: 2px solid #eee; padding-bottom: 0.5rem; }
.tabs button {
  padding: 0.4rem 1rem; border: none; background: none; cursor: pointer;
  font-size: 0.95rem; border-radius: 6px 6px 0 0; color: #666;
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
