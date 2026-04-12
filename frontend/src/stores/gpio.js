import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api.js'

export const useGpioStore = defineStore('gpio', () => {
  const pins = ref([])

  async function fetchPins() {
    const { data } = await api.get('/gpio/pins')
    pins.value = data
  }

  async function togglePin(pinNumber) {
    const { data } = await api.post(`/gpio/pins/${pinNumber}/toggle`)
    const idx = pins.value.findIndex(p => p.pin_number === pinNumber)
    if (idx !== -1) pins.value[idx] = data
  }

  async function addPin(pinNumber, label, direction) {
    const { data } = await api.post('/gpio/pins', { pin_number: pinNumber, label, direction })
    pins.value.push(data)
  }

  async function deletePin(pinNumber) {
    await api.delete(`/gpio/pins/${pinNumber}`)
    pins.value = pins.value.filter(p => p.pin_number !== pinNumber)
  }

  return { pins, fetchPins, togglePin, addPin, deletePin }
})
