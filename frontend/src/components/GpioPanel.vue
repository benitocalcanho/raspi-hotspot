<template>
  <div>
    <div v-if="showAdd" class="add-form">
      <h4>{{ $t('configure_new_pin') }}</h4>
      <input v-model.number="newPin.pin_number" type="number" :placeholder="$t('bcm_pin')" min="2" max="27" />
      <input v-model="newPin.label" :placeholder="$t('label_example')" />
      <select v-model="newPin.direction">
        <option value="output">{{ $t('output') }}</option>
        <option value="input">{{ $t('input') }}</option>
      </select>
      <button @click="addPin" class="btn-green">{{ $t('add_pin') }}</button>
      <p v-if="addError" class="error">{{ addError }}</p>
    </div>

    <div class="toolbar">
      <button class="btn-sm" @click="refreshPins" :disabled="gpioStore.loading">
        {{ gpioStore.loading ? 'Refreshing...' : 'Refresh' }}
      </button>
    </div>

    <p v-if="gpioStore.error" class="error">{{ gpioStore.error }}</p>

    <div v-if="gpioStore.pins.length" class="pin-grid">
      <div v-for="pin in gpioStore.pins" :key="pin.pin_number" class="pin-card">
        <div class="pin-header">
          <span class="label">{{ pin.label || `BCM${pin.pin_number}` }}</span>
          <span class="bcm">BCM {{ pin.pin_number }}</span>
        </div>
        <div class="pin-body">
          <span :class="['state', pin.state ? 'on' : 'off']">
            {{ pinStateLabel(pin, $t) }}
          </span>
          <button
            v-if="pin.direction === 'output'"
            @click="gpioStore.togglePin(pin.pin_number)"
            :class="['toggle-btn', pin.state ? 'on' : 'off']"
          >
            {{ $t('toggle') }}
          </button>
          <span v-else class="direction-badge">{{ $t('input_badge') }}</span>
        </div>
        <div v-if="showAdd" class="pin-footer">
          <button @click="gpioStore.deletePin(pin.pin_number)" class="btn-danger-sm">{{ $t('remove') }}</button>
        </div>
      </div>
    </div>
    <p v-else-if="!gpioStore.loading" class="empty">{{ $t('no_gpio_pins') }}</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useGpioStore } from '../stores/gpio.js'

// Props
const props = defineProps({
  // If true, show the "Add Pin" form
  showAdd: { type: Boolean, default: false }
})

// Pinia store for GPIO state and actions
const gpioStore = useGpioStore()

// Error message for add pin form
const addError = ref('')

// Model for new pin form
const newPin = ref({
  pin_number: null,   // BCM pin number
  label: '',          // Human-readable label
  direction: 'output' // Pin direction ('output' or 'input')
})

onMounted(refreshPins)

async function refreshPins() {
  try {
    await gpioStore.fetchPins()
  } catch {
    // Store exposes the user-facing error.
  }
}

// Add a new pin using the form values
async function addPin() {
  addError.value = ''
  try {
    await gpioStore.addPin(newPin.value.pin_number, newPin.value.label, newPin.value.direction)
    newPin.value = { pin_number: null, label: '', direction: 'output' }
  } catch (e) {
    addError.value = e.response?.data?.error || 'Failed to add pin.'
  }
}

function pinStateLabel(pin, t) {
  if (pin.direction !== 'input') {
    return pin.state ? t('on') : t('off')
  }
  if (pin.pin_number === 23 || /door sensor/i.test(pin.label || '')) {
    return pin.state ? 'Closed' : 'Open'
  }
  return pin.state ? 'Active' : 'Inactive'
}
</script>

<style scoped>
.add-form { background: #f8f9fa; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: flex-end; }
h4 { width: 100%; margin: 0; font-size: 0.9rem; color: #555; }
.add-form input, .add-form select { padding: 0.45rem 0.7rem; border: 1px solid #ddd; border-radius: 5px; font-size: 0.9rem; }
.btn-green { padding: 0.45rem 0.9rem; background: #27ae60; color: white; border: none; border-radius: 5px; cursor: pointer; }
.toolbar { display: flex; justify-content: flex-end; margin-bottom: 0.75rem; }
.btn-sm { padding: 0.3rem 0.7rem; background: #eef2f7; color: #344054; border: none; border-radius: 5px; cursor: pointer; font-size: 0.8rem; }
.btn-sm:disabled { cursor: wait; opacity: 0.7; }
.pin-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 1rem; }
.pin-card { background: white; border-radius: 10px; padding: 1rem; box-shadow: 0 2px 8px rgba(0,0,0,0.07); }
.pin-header { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 0.75rem; }
.label { font-weight: 700; font-size: 0.95rem; }
.bcm { font-size: 0.75rem; color: #aaa; }
.pin-body { display: flex; align-items: center; justify-content: space-between; }
.state { font-size: 0.85rem; font-weight: 700; padding: 0.2rem 0.5rem; border-radius: 20px; }
.state.on { background: #e8fde8; color: #27ae60; }
.state.off { background: #f0f0f0; color: #888; }
.toggle-btn { padding: 0.3rem 0.7rem; border: none; border-radius: 5px; cursor: pointer; font-size: 0.8rem; }
.toggle-btn.on { background: #e8fde8; color: #27ae60; }
.toggle-btn.off { background: #f0f0f0; color: #555; }
.direction-badge { font-size: 0.75rem; color: #2980b9; background: #e8f4fd; padding: 0.2rem 0.5rem; border-radius: 20px; }
.pin-footer { margin-top: 0.75rem; text-align: right; }
.btn-danger-sm { padding: 0.2rem 0.6rem; background: #fde8e8; color: #c0392b; border: none; border-radius: 4px; cursor: pointer; font-size: 0.78rem; }
.empty { color: #888; }
.error { color: #e74c3c; font-size: 0.85rem; }
</style>
