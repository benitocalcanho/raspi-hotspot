<template>
  <div class="settings-panel">
    <p v-if="loading" class="hint">Loading settings…</p>

    <template v-else>
      <div v-for="section in sections" :key="section.id" class="setting-section">
        <h4>{{ section.label }}</h4>
        <p class="section-desc">{{ section.desc }}</p>

        <div v-for="key in section.keys" :key="key" class="field">
          <!-- Special: guest password mode radio -->
          <template v-if="key === 'CALENDAR_GUEST_PASSWORD_MODE'">
            <label>Guest Password Source</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="form['CALENDAR_GUEST_PASSWORD_MODE']" value="fixed" />
                Fixed password (type it below)
              </label>
              <label class="radio-label">
                <input type="radio" v-model="form['CALENDAR_GUEST_PASSWORD_MODE']" value="from_event" />
                Last word of calendar event title (e.g. last 4 digits of phone number)
              </label>
            </div>
          </template>

          <!-- Special: fixed password — only show when mode is fixed -->
          <template v-else-if="key === 'CALENDAR_GUEST_DEFAULT_PASSWORD'">
            <div v-if="form['CALENDAR_GUEST_PASSWORD_MODE'] === 'fixed' || !form['CALENDAR_GUEST_PASSWORD_MODE']">
              <label>Fixed Guest Password</label>
              <input type="text" v-model="form[key]" :placeholder="inputPlaceholder(key)" />
            </div>
          </template>

          <!-- All other fields -->
          <template v-else>
            <label>
              {{ schema[key]?.label }}
              <span v-if="!values[key]?.is_set" class="badge-unset">Not set</span>
            </label>
            <textarea
              v-if="schema[key]?.multiline"
              v-model="form[key]"
              :placeholder="values[key]?.is_set ? '(currently set — paste new JSON to replace)' : 'Paste credentials.json content here'"
              rows="5"
            />
            <input
              v-else
              type="text"
              v-model="form[key]"
              :placeholder="inputPlaceholder(key)"
            />
          </template>
        </div>

        <div class="section-footer">
          <button
            class="btn-primary"
            @click="saveSection(section)"
            :disabled="saving === section.id"
          >
            {{ saving === section.id ? 'Saving…' : 'Save' }}
          </button>
          <span v-if="saved === section.id" class="success">Saved!</span>
          <span v-if="sectionError[section.id]" class="error">{{ sectionError[section.id] }}</span>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
// Always show fields as plaintext — this is the admin dashboard
function showAsPlaintext(_key) {
  return true
}
import { ref, onMounted, computed } from 'vue'
import api from '../api.js'

// Props
const props = defineProps({
  // If set, only show this section
  onlySection: { type: String, default: null },
})

// State fields
const loading = ref(true)         // True while loading settings from API
const schema = ref({})            // Settings schema (field definitions)
const values = ref({})            // Current values for each setting
const form = ref({ CALENDAR_GUEST_PASSWORD_MODE: 'fixed' })  // Form model; mode pre-initialized so radio always has a default
const saving = ref(null)          // Section ID currently being saved
const saved = ref(null)           // Section ID that was just saved
const sectionError = ref({})      // Error messages per section

// Section definitions for the settings UI
const allSections = [
  // Calendar-related sections removed from default Settings tab, will be shown only in Calendar tab
  {
    id: 'schedule',
    label: 'Guest Schedule',
    desc: 'Daily times when guests are checked out and checked in. Use 24-hour HH:MM format (e.g. 12:00 and 14:00).',
    keys: ['CHECKOUT_TIME', 'CHECKIN_TIME'],
  },
  {
    id: 'ngrok',
    label: 'ngrok Tunnel',
    desc: 'Expose your Pi to guests over the internet. Get your token at dashboard.ngrok.com.',
    keys: ['NGROK_AUTHTOKEN', 'NGROK_STATIC_DOMAIN'],
  },
  {
    id: 'cleaner',
    label: 'Cleaner Account',
    desc: 'Set the username and password for the cleaner. Only one cleaner account is active at a time. Role is always "cleaner".',
    keys: ['CLEANER_USERNAME', 'CLEANER_PASSWORD'],
  },
  {
    id: 'calendar_rules',
    label: 'Calendar Rules',
    desc: 'Controls how guests are created from calendar events.',
    keys: ['CALENDAR_GUEST_DEFAULT_PASSWORD'],
  },
]

const sections = computed(() => {
  if (!props.onlySection) {
    // Show all except email, ical, schedule, cleaner, and calendar_rules sections in Settings tab
    return allSections.filter(s => !['email', 'ical', 'schedule', 'cleaner', 'calendar_rules'].includes(s.id))
  }
  if (props.onlySection === 'email') {
    // Only show email section in Email tab
    return [
      {
        id: 'email',
        label: 'Email Notifications',
        desc: 'Configure SMTP server and recipient for notification emails. These settings are used to send alerts when a user presses a button.',
        keys: ['SMTP_HOST', 'SMTP_PORT', 'SMTP_USER', 'SMTP_PASS', 'EMAIL_SENDER', 'EMAIL_RECIPIENT'],
      },
    ]
  }
  // Calendar tab sections
  const calendarSections = {
    ical: {
      id: 'ical',
      label: 'Google Calendar (iCal — recommended)',
      desc: 'Paste the private iCal URL from Google Calendar → Settings → "Secret address in iCal format". No API keys needed. One event per day = one active guest.',
      keys: ['ICAL_URL'],
    },
    guest_password: {
      id: 'guest_password',
      label: 'Guest Password',
      desc: 'How the password is assigned to guests created from calendar events.',
      keys: ['CALENDAR_GUEST_PASSWORD_MODE', 'CALENDAR_GUEST_DEFAULT_PASSWORD'],
    },
    schedule: {
      id: 'schedule',
      label: 'Guest Schedule',
      desc: 'Daily times when guests are checked out and checked in. Use 24-hour HH:MM format (e.g. 12:00 and 14:00).',
      keys: ['CHECKOUT_TIME', 'CHECKIN_TIME'],
    },
    cleaner: {
      id: 'cleaner',
      label: 'Cleaner Account',
      desc: 'Set the username and password for the cleaner. Only one cleaner account is active at a time. Role is always "cleaner".',
      keys: ['CLEANER_USERNAME', 'CLEANER_PASSWORD'],
    },
    calendar_rules: {
      id: 'calendar_rules',
      label: 'Calendar Rules',
      desc: 'Controls how guests are created from calendar events.',
      keys: ['CALENDAR_GUEST_DEFAULT_PASSWORD'],
    },
  }
  if (calendarSections[props.onlySection]) {
    return [calendarSections[props.onlySection]]
  }
  return allSections.filter(s => s.id === props.onlySection)
})

onMounted(async () => {
  try {
    const { data } = await api.get('/admin/settings')
    schema.value = data.schema
    values.value = data.values
    // Pre-populate all fields with their current value; default mode to 'fixed'
    for (const [key, _meta] of Object.entries(data.schema)) {
      const val = data.values[key]?.value
      if (val) {
        form.value[key] = val
      } else if (key === 'CALENDAR_GUEST_PASSWORD_MODE') {
        form.value[key] = 'fixed'
      }
    }
  } finally {
    loading.value = false
  }
})

function inputPlaceholder(key) {
  const val = values.value[key]
  return val?.is_set ? '' : 'Not configured'
}

async function saveSection(section) {
  saving.value = section.id
  saved.value = null
  sectionError.value = { ...sectionError.value, [section.id]: null }

  // Build payload: include all fields from this section that have a value in form
  const payload = {}
  for (const key of section.keys) {
    const v = form.value[key]
    if (v && v.trim()) {
      payload[key] = v.trim()
    }
  }

  // Cleaner password validation (frontend)
  if (section.id === 'cleaner' && payload.CLEANER_PASSWORD && payload.CLEANER_PASSWORD.length < 8) {
    sectionError.value = {
      ...sectionError.value,
      [section.id]: 'Cleaner password must be at least 8 characters.'
    }
    saving.value = null
    return
  }

  if (Object.keys(payload).length === 0) {
    // Always include mode so a radio-only change still saves
    if (section.keys.includes('CALENDAR_GUEST_PASSWORD_MODE')) {
      payload['CALENDAR_GUEST_PASSWORD_MODE'] = form.value['CALENDAR_GUEST_PASSWORD_MODE'] || 'fixed'
    } else {
      saving.value = null
      return
    }
  }

  try {
    const { data } = await api.patch('/admin/settings', payload)
    // Refresh values so badges update
    const { data: fresh } = await api.get('/admin/settings')
    values.value = fresh.values
    // Re-fill all fields from fresh values; never reset mode to empty
    for (const key of section.keys) {
      const val = fresh.values[key]?.value
      if (val) {
        form.value[key] = val
      } else if (key === 'CALENDAR_GUEST_PASSWORD_MODE') {
        // keep whatever the user selected — it was just saved
      } else {
        form.value[key] = ''
      }
    }
    saved.value = section.id
    setTimeout(() => { if (saved.value === section.id) saved.value = null }, 3000)
  } catch (e) {
    sectionError.value = {
      ...sectionError.value,
      [section.id]: e.response?.data?.error || 'Failed to save settings.',
    }
  } finally {
    saving.value = null
  }
}
</script>

<style scoped>
.settings-panel { max-width: 640px; }
.radio-group { display: flex; flex-direction: column; gap: 8px; margin-top: 4px; }
.radio-label { display: flex; align-items: center; gap: 8px; cursor: pointer; font-weight: normal; }
.setting-section {
  background: white;
  border-radius: 10px;
  padding: 1.2rem 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.07);
}
.setting-section h4 { margin: 0 0 0.25rem; font-size: 1rem; color: #0f3460; }
.section-desc { color: #888; font-size: 0.82rem; margin: 0 0 1rem; }
.field { display: flex; flex-direction: column; margin-bottom: 0.9rem; gap: 0.3rem; }
.field label { font-size: 0.85rem; font-weight: 600; color: #444; display: flex; align-items: center; gap: 0.5rem; }
.field input, .field textarea {
  padding: 0.5rem 0.7rem;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 0.9rem;
  font-family: monospace;
  resize: vertical;
}
.field input:focus, .field textarea:focus {
  outline: none;
  border-color: #0f3460;
}
.badge-set { background: #d4edda; color: #155724; font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 10px; font-weight: 500; }
.badge-unset { background: #f8d7da; color: #721c24; font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 10px; font-weight: 500; }
.section-footer { display: flex; align-items: center; gap: 0.75rem; margin-top: 0.5rem; }
.btn-primary {
  padding: 0.45rem 1rem; background: #0f3460; color: white;
  border: none; border-radius: 6px; cursor: pointer; font-size: 0.9rem;
}
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.success { color: #27ae60; font-size: 0.88rem; }
.error { color: #e74c3c; font-size: 0.88rem; }
.hint { color: #888; }
</style>
