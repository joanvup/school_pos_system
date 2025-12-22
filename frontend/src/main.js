import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth' // Importamos el store
import { useConfigStore } from './stores/config';

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// --- SOLUCIÓN AL ERROR ---
// No llamamos a initializeStore().
// En su lugar, verificamos si hay token y refrescamos los datos del usuario.
const authStore = useAuthStore()

if (authStore.token) {
    // Si hay un token guardado, intentamos traer los datos frescos del usuario
    authStore.fetchUserProfile().catch(() => {
        // Si el token expiró o es inválido, cerramos sesión
        authStore.logout()
    })
}
// CARGAR CONFIGURACIÓN GLOBAL ANTES DE MONTAR
const configStore = useConfigStore();
configStore.fetchSettings().then(() => {
    app.mount('#app');
});