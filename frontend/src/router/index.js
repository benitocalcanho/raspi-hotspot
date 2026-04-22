import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import UserDashboard from '../views/UserDashboard.vue'
// import CleanerDashboard from '../views/CleanerDashboard.vue'
import GuestDashboard from '../views/GuestDashboard.vue'
import WiFiSetup from '../views/WiFiSetup.vue'
import GpioControl from '../views/GpioControl.vue'

function homeForRole(role) {
  if (role === 'admin') return '/admin'
  if (['cleaner', 'guest', 'user'].includes(role)) return '/guest'
  return '/dashboard'
}

const routes = [
  { path: '/', redirect: '/login' },
  { path: '/login', component: Login, meta: { public: true } },
  { path: '/wifi-setup', component: WiFiSetup, meta: { public: true } },
  {
    path: '/admin',
    component: AdminDashboard,
    meta: { requiresAuth: true, requiresAdmin: true },
  },
  {
    path: '/dashboard',
    component: UserDashboard,
    meta: { requiresAuth: true },
  },
  // Cleaner now uses the guest dashboard
  {
    path: '/guest',
    component: GuestDashboard,
    meta: { requiresAuth: true, allowedRoles: ['guest', 'cleaner', 'user'] },
  },
  {
    path: '/gpio',
    component: GpioControl,
    meta: { requiresAuth: true },
  },
]


const router = createRouter({
  history: createWebHistory(),
  routes,
})

let sessionRestored = false
let sessionPromise = null

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  // On first navigation, restore session if needed
  if (!sessionRestored) {
    sessionRestored = true
    if (localStorage.getItem('access_token')) {
      sessionPromise = authStore.fetchCurrentUser()
      await sessionPromise
    }
  } else if (sessionPromise) {
    await sessionPromise
  }

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return '/login'
  }
  if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    return homeForRole(authStore.user?.role)
  }
  if (to.meta.allowedRoles && !to.meta.allowedRoles.includes(authStore.user?.role)) {
    return homeForRole(authStore.user?.role)
  }
  if (to.meta.requiresRole && authStore.user?.role !== to.meta.requiresRole) {
    return homeForRole(authStore.user?.role)
  }
  if (to.path === '/dashboard' && authStore.isLoggedIn && authStore.user?.role !== 'user') {
    return homeForRole(authStore.user?.role)
  }
  if (to.path === '/login' && authStore.isLoggedIn) {
    return homeForRole(authStore.user?.role)
  }
})

export default router
