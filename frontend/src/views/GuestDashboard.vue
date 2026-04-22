<template>
  <div class="guest-page">
    <!-- Floating sign-out button -->
    <button class="signout-btn" @click="logout">{{ $t('signout') }}</button>

    <div
      class="door-card"
      :style="images.building_door ? `background-image: url('${images.building_door}')` : ''"
    >
      <div class="door-overlay">
        <p class="door-label">{{ $t('building_door') }}</p>
        <button
          class="unlock-btn"
          :class="{ unlocking: active === 'building' }"
          :style="active === 'building' ? `--progress: ${progress}%` : ''"
          :disabled="active !== null"
          @click="unlock('building')"
        >
          {{ active === 'building' ? $t('push_door') : '🔓 ' + $t('unlock_door') }}
        </button>
      </div>
    </div>

    <div
      class="door-card"
      :style="images.apartment_door ? `background-image: url('${images.apartment_door}')` : ''"
    >
      <div class="door-overlay">
        <p class="door-label">{{ $t('apartment_door') }}</p>
        <button
          class="unlock-btn"
          :class="{ unlocking: active === 'apartment' }"
          :style="active === 'apartment' ? `--progress: ${progress}%` : ''"
          :disabled="active !== null"
          @click="unlock('apartment')"
        >
          {{ active === 'apartment' ? $t('push_door') : '🔓 ' + $t('unlock_door') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '../api.js'
import { useAuthStore } from '../stores/auth.js'

const images = ref({ building_door: null, apartment_door: null })
const router = useRouter()
const authStore = useAuthStore()

const DURATION = 5000  // ms — matches GPIO relay pulse duration
const active = ref(null)   // 'building' | 'apartment' | null
const progress = ref(100)  // 100 → 0 over DURATION ms

onMounted(async () => {
  try {
    const { data } = await api.get('/uploads/images')
    images.value = data
  } catch (_) {}
})

async function unlock(door) {
  if (active.value !== null) return
  active.value = door
  progress.value = 100

  // Log virtual button press to backend
  try {
    console.log('Attempting to log button press:', door)
    await api.post('/admin/audit/button_press', { button: door })
  } catch (e) {
    console.error('Button press log failed:', e)
  }

  // GPIO relay trigger will be wired here

  const start = performance.now()
  const tick = (now) => {
    const elapsed = now - start
    progress.value = Math.max(0, 100 - (elapsed / DURATION) * 100)
    if (elapsed < DURATION) {
      requestAnimationFrame(tick)
    } else {
      active.value = null
      progress.value = 100
    }
  }
  requestAnimationFrame(tick)
}

async function logout() {
  await authStore.logout()
  router.push('/login')
}

// Helper: progress < 90 means red is visible
function progressAttr(door) {
  return active.value === door && progress.value < 90 ? { 'data-progress': '' } : {}
}
</script>

<style scoped>
.guest-page {
  display: flex;
  flex-direction: column;
  gap: 0;
  height: 100dvh;       /* fills screen, respects mobile browser chrome */
  position: relative;
}

.signout-btn {
  position: fixed;
  top: 0.9rem;
  right: 1rem;
  z-index: 200;
  background: rgba(0,0,0,0.45);
  color: white;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 20px;
  padding: 0.4rem 1rem;
  font-size: 0.85rem;
  cursor: pointer;
  backdrop-filter: blur(4px);
}

.door-card {
  flex: 1;
  background-color: #1a1a2e;
  background-size: cover;
  background-position: center;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.door-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1.2rem;
}

.door-label {
  color: rgba(255,255,255,0.85);
  font-size: 1rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}

.unlock-btn {
  padding: 1.1rem 3rem;
  font-size: 1.4rem;
  font-weight: 700;
  background: rgba(255, 255, 255, 0.93);
  color: #0f3460;
  border: none;
  border-radius: 50px;
  cursor: pointer;
  box-shadow: 0 4px 24px rgba(0,0,0,0.4);
  transition: transform 0.1s, box-shadow 0.1s;
  min-width: 200px;
  min-height: 60px;
  touch-action: manipulation;
  /* progress bar lives here — set via --progress custom property */
  background-image: none;
  position: relative;
  overflow: hidden;
}

/* Drain animation: red fills from left, white retreats to the right */
.unlock-btn.unlocking {
  background: linear-gradient(
    to left,
    rgba(255,255,255,0.93) var(--progress, 100%),
    #e74c3c var(--progress, 100%)
  );
  color: #0f3460;
}

.unlock-btn.unlocking[data-progress] {
  color: #fff;
}

.unlock-btn:disabled:not(.unlocking) {
  opacity: 0.5;
  cursor: not-allowed;
}

.unlock-btn:active:not(:disabled) {
  transform: scale(0.96);
  box-shadow: 0 2px 10px rgba(0,0,0,0.3);
}
</style>
