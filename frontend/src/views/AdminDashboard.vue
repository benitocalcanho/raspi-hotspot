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
    </div>

    <div class="tabs">
      <button :class="{active: tab==='users'}" @click="tab='users'">Users</button>
      <button :class="{active: tab==='audit'}" @click="tab='audit'">Audit Log</button>
      <button :class="{active: tab==='calendar'}" @click="tab='calendar'">Calendar Sync</button>
    </div>

    <!-- Users tab -->
    <section v-if="tab === 'users'">
      <div class="section-header">
        <h3>User Management</h3>
        <button @click="showCreate = !showCreate" class="btn-primary">+ New User</button>
      </div>

      <form v-if="showCreate" @submit.prevent="createUser" class="create-form">
        <input v-model="newUser.username" placeholder="Username" required />
        <input v-model="newUser.email" type="email" placeholder="Email" required />
        <input v-model="newUser.password" type="password" placeholder="Password (min 8 chars)" required />
        <select v-model="newUser.role">
          <option value="user">User</option>
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

    <!-- Calendar tab -->
    <section v-if="tab === 'calendar'">
      <h3>Google Calendar Sync</h3>
      <p class="hint">
        Add events titled <code>CREATE_USER | username | email | password</code> to your calendar.
        The Pi will automatically create the user account.
      </p>
      <button @click="triggerSync" :disabled="syncing" class="btn-primary">
        {{ syncing ? 'Syncing…' : 'Sync Now' }}
      </button>
      <p v-if="syncResult !== null" class="success">Created {{ syncResult }} user(s).</p>
      <p v-if="syncError" class="error">{{ syncError }}</p>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api.js'
import UserTable from '../components/UserTable.vue'
import AuditLog from '../components/AuditLog.vue'

const tab = ref('users')
const overview = ref(null)
const users = ref([])
const auditEntries = ref([])
const showCreate = ref(false)
const createError = ref('')
const syncing = ref(false)
const syncResult = ref(null)
const syncError = ref('')

const newUser = ref({ username: '', email: '', password: '', role: 'user' })

onMounted(async () => {
  await Promise.all([loadOverview(), loadUsers(), loadAudit()])
})

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
    newUser.value = { username: '', email: '', password: '', role: 'user' }
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
</style>
