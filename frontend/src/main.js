

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import i18n from './i18n'

import { useAuthStore } from './stores/auth.js'


const pinia = createPinia()
const app = createApp(App)
app.use(pinia)
app.use(router)
app.use(i18n)

// Restore session if access_token exists
const authStore = useAuthStore()
if (localStorage.getItem('access_token')) {
	authStore.fetchCurrentUser()
}

app.mount('#app')
