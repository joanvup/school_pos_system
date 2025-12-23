import { defineStore } from 'pinia';
import api from '../api/axios';
import router from '../router';

export const useAuthStore = defineStore('auth', {
    state: () => ({
        token: localStorage.getItem('token') || null,
        user: JSON.parse(localStorage.getItem('user')) || null, // Persistir usuario al recargar F5
        loading: false,
        error: null
    }),

    getters: {
        isAuthenticated: (state) => !!state.token,
        currentUser: (state) => state.user,
        // Helpers rápidos de roles
        isAdmin: (state) => state.user?.role === 'admin',
        isSupervisor: (state) => state.user?.role === 'supervisor',
        isSeller: (state) => state.user?.role === 'vendedor',
        isParent: (state) => state.user?.role === 'padre',
        isEmployee: (state) => state.user?.role === 'empleado',
    },

    actions: {
        // 1. Iniciar Sesión
        async login(email, password) {
            this.loading = true;
            this.error = null;

            // Formato x-www-form-urlencoded requerido por FastAPI OAuth2
            const params = new URLSearchParams();
            params.append('username', email);
            params.append('password', password);

            try {
                // Paso A: Obtener Token
                const { data } = await api.post('/auth/login/access-token', params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });

                this.token = data.access_token;
                localStorage.setItem('token', this.token);

                // Paso B: Obtener datos del usuario (Rol, Nombre)
                await this.fetchUserProfile();

                return true;
            } catch (err) {
                console.error("Error Login:", err);
                this.error = err.response?.data?.detail || "Credenciales incorrectas";
                throw err;
            } finally {
                this.loading = false;
            }
        },

        // 2. Obtener datos del usuario actual (Quién soy)
        async fetchUserProfile() {
            try {
                // NOTA: Requiere que exista el endpoint GET /users/me en el backend
                const { data } = await api.get('/users/me');
                this.user = data;
                localStorage.setItem('user', JSON.stringify(data));
            } catch (error) {
                console.error("Error obteniendo perfil:", error);
                this.logout(); // Si falla el perfil, el token no sirve
            }
        },

        // 3. Cerrar Sesión
        logout() {
            this.token = null;
            this.user = null;
            localStorage.removeItem('token');
            localStorage.removeItem('user');
            router.push('/login');
        }
    }
});