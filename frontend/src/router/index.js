import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'

import Login from '../views/Login.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import UserDashboard from '../views/UserDashboard.vue'
import WiFiSetup from '../views/WiFiSetup.vue'
import GpioControl from '../views/GpioControl.vue'

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

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.meta.requiresAuth && !authStore.isLoggedIn) {
    return '/login'
  }
  if (to.meta.requiresAdmin && authStore.user?.role !== 'admin') {
    return '/dashboard'
  }
  if (to.path === '/login' && authStore.isLoggedIn) {
    return authStore.user?.role === 'admin' ? '/admin' : '/dashboard'
  }
})

export default router
