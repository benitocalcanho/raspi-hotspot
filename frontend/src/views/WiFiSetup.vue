<template>
  <div class="wifi-page">
    <div class="wifi-card">
      <h1>WiFi Setup</h1>
      <p class="subtitle">Connect your Raspberry Pi to the internet</p>

      <!-- Step 1: scan -->
      <div v-if="step === 'scan'">
        <button @click="scan" :disabled="scanning" class="btn-primary full">
          {{ scanning ? 'Scanning…' : 'Scan for Networks' }}
        </button>
        <p v-if="scanError" class="error">{{ scanError }}</p>
      </div>

      <!-- Step 2: select -->
      <div v-if="step === 'select'">
        <h3>Available Networks</h3>
        <ul class="network-list">
          <li
            v-for="net in networks"
            :key="net.ssid"
            :class="{ selected: selectedSsid === net.ssid }"
            @click="selectedSsid = net.ssid"
          >
            <span class="ssid">{{ net.ssid }}</span>
            <span class="meta">{{ net.signal }}% · {{ net.security }}</span>
          </li>
        </ul>
        <button @click="step = 'password'" :disabled="!selectedSsid" class="btn-primary full mt">
          Continue →
        </button>
      </div>

      <!-- Step 3: password -->
      <div v-if="step === 'password'">
        <p>Connecting to <strong>{{ selectedSsid }}</strong></p>
        <div class="field mt">
          <label>WiFi Password</label>
          <input v-model="passphrase" type="password" placeholder="Enter WiFi password" />
        </div>
        <button @click="connect" :disabled="connecting" class="btn-primary full mt">
          {{ connecting ? 'Connecting…' : 'Connect' }}
        </button>
        <button @click="step = 'select'" class="btn-back mt">← Back</button>
        <p v-if="connectError" class="error">{{ connectError }}</p>
      </div>

      <!-- Step 4: done -->
      <div v-if="step === 'done'" class="done">
        <p>Connected to <strong>{{ selectedSsid }}</strong>!</p>
        <p class="hint">You can now close this page and access the app on your local network.</p>
        <a href="/login" class="btn-primary full mt" style="text-align:center;display:block;">Go to Login →</a>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import api from '../api.js'

const step = ref('scan')
const networks = ref([])
const selectedSsid = ref('')
const passphrase = ref('')
const scanning = ref(false)
const connecting = ref(false)
const scanError = ref('')
const connectError = ref('')

async function scan() {
  scanning.value = true
  scanError.value = ''
  try {
    const { data } = await api.get('/wifi/scan')
    networks.value = data
    step.value = 'select'
  } catch (e) {
    scanError.value = e.response?.data?.error || 'Scan failed.'
  } finally {
    scanning.value = false
  }
}

async function connect() {
  connecting.value = true
  connectError.value = ''
  try {
    await api.post('/wifi/connect', { ssid: selectedSsid.value, passphrase: passphrase.value })
    step.value = 'done'
  } catch (e) {
    connectError.value = e.response?.data?.error || 'Connection failed.'
  } finally {
    connecting.value = false
  }
}
</script>

<style scoped>
.wifi-page {
  min-height: 100vh; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #0f3460 0%, #16213e 100%);
}
.wifi-card { background: white; border-radius: 12px; padding: 2rem; width: 100%; max-width: 420px; }
h1 { font-size: 1.6rem; margin-bottom: 0.2rem; }
.subtitle { color: #666; margin-bottom: 1.5rem; }
h3 { margin-bottom: 0.75rem; }
.network-list { list-style: none; max-height: 260px; overflow-y: auto; border: 1px solid #eee; border-radius: 8px; }
.network-list li {
  padding: 0.75rem 1rem; cursor: pointer; border-bottom: 1px solid #f0f0f0;
  display: flex; justify-content: space-between; align-items: center;
  transition: background 0.15s;
}
.network-list li:hover { background: #f5f7fa; }
.network-list li.selected { background: #e8f0fe; }
.ssid { font-weight: 600; }
.meta { font-size: 0.8rem; color: #888; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
.field label { font-size: 0.85rem; font-weight: 600; }
.field input { padding: 0.6rem; border: 1px solid #ddd; border-radius: 6px; font-size: 1rem; }
.btn-primary { padding: 0.7rem 1.2rem; background: #0f3460; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 0.95rem; }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-back { padding: 0.5rem 1rem; background: #eee; border: none; border-radius: 6px; cursor: pointer; }
.full { width: 100%; }
.mt { margin-top: 0.75rem; }
.error { color: #e74c3c; font-size: 0.88rem; margin-top: 0.5rem; }
.done p { margin-bottom: 0.5rem; }
.hint { color: #888; font-size: 0.9rem; }
</style>
