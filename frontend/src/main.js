import { createApp } from 'vue'
import { createPinia } from 'pinia'
import './style.css'
import App from './App.vue'
import router from './router'
import { useConfigStore } from './stores/config';

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)

// La sesión se revalida en la guarda del router contra /users/me.
const configStore = useConfigStore();
configStore.fetchSettings().then(() => {
    app.mount('#app');
});