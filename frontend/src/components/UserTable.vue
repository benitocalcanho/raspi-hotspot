<template>
  <div class="user-table-wrap">
    <table v-if="users.length">
      <thead>
        <tr>
          <th>Username</th>
          <th>Role</th>
          <th>Status</th>
          <th>Created</th>
          <th>Source</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="user in users" :key="user.id">
          <td>{{ user.username }}</td>
          <td><span :class="['badge', user.role]">{{ user.role }}</span></td>
          <td>
            <span :class="['badge', user.is_active ? 'active' : 'inactive']">
              {{ user.is_active ? 'Active' : 'Suspended' }}
            </span>
          </td>
          <td>{{ formatDate(user.created_at) }}</td>
          <td>{{ user.created_by }}</td>
          <td class="actions">
            <button @click="toggleActive(user)" class="btn-act">
              {{ user.is_active ? 'Suspend' : 'Activate' }}
            </button>
            <button @click="renameUser(user)" class="btn-act">Rename</button>
            <button @click="setPassword(user)" class="btn-act">Password</button>
            <button @click="deleteUser(user)" class="btn-act danger">Delete</button>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else class="empty">No users found.</p>
  </div>
</template>

<script setup>
import api from '../api.js'

// Props
const props = defineProps({
  // Array of user objects to display
  users: Array
})

// Emits 'refresh' when user data should be reloaded
const emit = defineEmits(['refresh'])

// Format ISO date string as local date
function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

// Toggle user active/suspended status
async function toggleActive(user) {
  await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
  emit('refresh')
}

// Prompt for new username and update
async function renameUser(user) {
  const newUsername = prompt('New username:', user.username)
  if (newUsername === null) return
  const username = newUsername.trim()
  if (!username || username === user.username) return
  try {
    await api.patch(`/admin/users/${user.id}`, { username })
    emit('refresh')
  } catch (e) {
    alert(e.response?.data?.error || 'Failed to rename user.')
  }
}

// Prompt for new password and update
async function setPassword(user) {
  const newPassword = prompt(`Set new password for ${user.username}:`)
  if (newPassword === null) return
  const password = newPassword.trim()
  if (!password) return
  try {
    await api.patch(`/admin/users/${user.id}`, { password })
    emit('refresh')
  } catch (e) {
    alert(e.response?.data?.error || 'Failed to update password.')
  }
}

async function deleteUser(user) {
  if (!confirm(`Delete user "${user.username}"? This cannot be undone.`)) return
  await api.delete(`/admin/users/${user.id}`)
  emit('refresh')
}
</script>

<style scoped>
.user-table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }
th, td { padding: 0.7rem 1rem; text-align: left; border-bottom: 1px solid #f0f0f0; font-size: 0.88rem; }
th { background: #f8f9fa; font-weight: 600; color: #555; }
.badge { padding: 0.2rem 0.6rem; border-radius: 20px; font-size: 0.75rem; font-weight: 600; }
.badge.admin { background: #fde8e8; color: #c0392b; }
.badge.user { background: #e8f4fd; color: #2980b9; }
.badge.cleaner { background: #fef3e8; color: #e67e22; }
.badge.guest { background: #f0e8fd; color: #8e44ad; }
.badge.active { background: #e8fde8; color: #27ae60; }
.badge.inactive { background: #fafafa; color: #888; }
.actions { display: flex; gap: 0.4rem; }
.btn-act { padding: 0.25rem 0.6rem; border: none; border-radius: 4px; cursor: pointer; font-size: 0.8rem; background: #eee; }
.btn-act.danger { background: #fde8e8; color: #c0392b; }
.empty { color: #888; padding: 1rem 0; }
</style>
