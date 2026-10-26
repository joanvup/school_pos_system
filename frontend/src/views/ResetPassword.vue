<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="bg-white p-10 rounded-[40px] shadow-xl max-w-md w-full border border-gray-100">
        <div class="text-center mb-8">
            <div class="text-5xl mb-4">🔐</div>
            <h2 class="text-3xl font-black tracking-tighter">Nueva Contraseña</h2>
            <p class="text-gray-400 text-sm font-medium">Define tu nueva clave de acceso</p>
        </div>

        <form @submit.prevent="handleReset" class="space-y-4">
            <input v-model="newPassword" type="password" placeholder="Nueva contraseña" required
                   autocomplete="new-password"
                   class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
            
            <input v-model="confirmPassword" type="password" placeholder="Confirmar contraseña" required
                   autocomplete="new-password"
                   class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">

            <p class="text-xs text-gray-400">
                Mínimo 10 caracteres, con letras y números.
            </p>

            <div v-if="error" class="bg-red-50 text-red-600 p-4 rounded-2xl text-sm font-bold border border-red-100">
                {{ error }}
            </div>

            <div v-if="success" class="bg-emerald-50 text-emerald-700 p-4 rounded-2xl text-sm font-bold border border-emerald-100">
                {{ success }}
            </div>

            <button type="submit" :disabled="loading || !token"
                    class="w-full bg-primary text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-200 disabled:opacity-50">
                {{ loading ? 'Actualizando...' : 'ACTUALIZAR CONTRASEÑA' }}
            </button>

            <router-link to="/login" class="block text-center text-xs font-bold text-gray-400 uppercase tracking-widest pt-2">
                Volver al inicio de sesión
            </router-link>
        </form>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '../api/axios';

const route = useRoute();
const router = useRouter();
const token = computed(() => (typeof route.query.token === 'string' ? route.query.token : ''));
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);
const error = ref(token.value ? '' : 'El enlace no incluye un token válido.');
const success = ref('');

const validate = () => {
    if (newPassword.value !== confirmPassword.value) {
        return 'Las contraseñas no coinciden';
    }
    if (newPassword.value.length < 10) {
        return 'La contraseña debe tener al menos 10 caracteres';
    }
    if (!/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
        return 'La contraseña debe incluir letras y números';
    }
    return '';
};

const handleReset = async () => {
    error.value = validate();
    if (error.value) return;

    loading.value = true;
    try {
        await api.post('/auth/reset-password', {
            token: token.value,
            new_password: newPassword.value,
        });
        success.value = 'Contraseña actualizada. Redirigiendo al inicio de sesión...';
        window.setTimeout(() => router.push({ path: '/login', query: { changed: '1' } }), 1500);
    } catch (err) {
        error.value = err.response?.data?.detail || 'El enlace ha expirado o es inválido.';
    } finally {
        loading.value = false;
    }
};
</script>
