import { defineStore } from 'pinia';
import api from '../api/axios';
import router from '../router';

// Evita que varias guardas simultáneas disparen /users/me en paralelo.
let initPromise = null;

export const useAuthStore = defineStore('auth', {
    state: () => ({
        user: null,
        initialized: false,
        loading: false,
        error: null,
    }),

    getters: {
        isAuthenticated: (state) => !!state.user,
        currentUser: (state) => state.user,
        mustChangePassword: (state) => !!state.user?.must_change_password,
        isAdmin: (state) => state.user?.role === 'admin',
        isSupervisor: (state) => state.user?.role === 'supervisor',
        isSeller: (state) => state.user?.role === 'vendedor',
        isParent: (state) => state.user?.role === 'padre',
        isEmployee: (state) => state.user?.role === 'empleado',
        homePath: (state) => {
            const role = state.user?.role;
            if (role === 'padre') return '/my-family';
            if (role === 'empleado') return '/my-card';
            if (role === 'vendedor') return '/pos';
            return '/dashboard';
        },
    },

    actions: {
        // Revalida la cookie de sesión contra el backend. Se llama desde el router.
        async initialize() {
            if (this.initialized) return;
            if (!initPromise) {
                initPromise = (async () => {
                    try {
                        const { data } = await api.get('/users/me', {
                            skipAuthRedirect: true,
                        });
                        this.user = data;
                    } catch {
                        this.user = null;
                    } finally {
                        this.initialized = true;
                        initPromise = null;
                    }
                })();
            }
            return initPromise;
        },

        async login(email, password) {
            this.loading = true;
            this.error = null;

            // Formato x-www-form-urlencoded requerido por FastAPI OAuth2
            const params = new URLSearchParams();
            params.append('username', email);
            params.append('password', password);

            try {
                await api.post('/auth/login/access-token', params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                });
                await this.fetchUserProfile();
                this.initialized = true;
                return true;
            } catch (err) {
                this.error = err.response?.data?.detail || 'Credenciales incorrectas';
                throw err;
            } finally {
                this.loading = false;
            }
        },

        async fetchUserProfile() {
            const { data } = await api.get('/users/me', {
                skipAuthRedirect: true,
            });
            this.user = data;
            return data;
        },

        clearSession() {
            this.user = null;
            this.initialized = true;
            // Limpia tokens de versiones anteriores que quedaron en localStorage.
            localStorage.removeItem('token');
            localStorage.removeItem('user');
        },

        async logout() {
            try {
                await api.post('/auth/logout', null, { skipAuthRedirect: true });
            } catch {
                // Si el backend no responde, igual limpiamos el estado local.
            }
            this.clearSession();
            await router.push('/login');
        },
    },
});
