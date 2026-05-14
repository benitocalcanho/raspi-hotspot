import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const useGpioStore = defineStore('gpio', () => {
  const pins = ref([])
  const loading = ref(false)
  const error = ref('')

  async function fetchPins() {
    loading.value = true
    error.value = ''
    try {
      const { data } = await api.get('/gpio/pins')
      pins.value = data
    } catch (err) {
      error.value = err.response?.data?.error || 'Could not load GPIO pins.'
      pins.value = []
      throw err
    } finally {
      loading.value = false
    }
  }

  async function pulsePin(pinNumber, duration = 20) {
    const { data } = await api.post(`/gpio/pins/${pinNumber}/pulse`, { duration })
    const idx = pins.value.findIndex(p => p.pin_number === pinNumber)
    if (idx !== -1) pins.value[idx] = data
    setTimeout(() => {
      fetchPins().catch(() => {})
    }, (duration * 1000) + 500)
  }

  async function addPin(pinNumber, label, direction) {
    const { data } = await api.post('/gpio/pins', { pin_number: pinNumber, label, direction })
    pins.value.push(data)
  }

  async function deletePin(pinNumber) {
    await api.delete(`/gpio/pins/${pinNumber}`)
    pins.value = pins.value.filter(p => p.pin_number !== pinNumber)
  }

  return { pins, loading, error, fetchPins, pulsePin, addPin, deletePin }
})
