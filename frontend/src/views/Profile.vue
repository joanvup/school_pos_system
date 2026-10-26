<template>
  <div class="max-w-lg bg-white p-8 rounded-xl shadow mx-auto mt-10">
    <h1 class="text-2xl font-bold mb-6">Mi Perfil</h1>
    
    <div class="mb-6">
        <label class="text-gray-500 text-sm">Nombre</label>
        <div class="text-lg font-bold">{{ authStore.user?.full_name }}</div>
    </div>
    
    <div class="mb-8">
        <label class="text-gray-500 text-sm">Email</label>
        <div class="text-lg">{{ authStore.user?.email }}</div>
    </div>

    <hr class="mb-6">

    <h2 class="text-lg font-bold mb-4">Cambiar Contraseña</h2>
    <form @submit.prevent="changePassword" class="space-y-4">
        <div>
            <label class="text-sm">Contraseña actual</label>
            <input v-model="currentPassword" type="password" required autocomplete="current-password"
                   class="w-full border p-2 rounded">
        </div>
        <div>
            <label class="text-sm">Nueva Contraseña</label>
            <input v-model="pass1" type="password" required autocomplete="new-password"
                   class="w-full border p-2 rounded">
        </div>
        <div>
            <label class="text-sm">Confirmar Contraseña</label>
            <input v-model="pass2" type="password" required autocomplete="new-password"
                   class="w-full border p-2 rounded">
        </div>

        <p class="text-xs text-gray-400">Mínimo 10 caracteres, con letras y números.</p>

        <div v-if="error" class="bg-red-50 text-red-600 p-3 rounded text-sm font-bold">
            {{ error }}
        </div>

        <button type="submit" :disabled="loading"
                class="w-full bg-gray-800 text-white py-2 rounded hover:bg-black disabled:opacity-50">
            {{ loading ? 'Actualizando...' : 'Actualizar' }}
        </button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import api from '../api/axios';

const authStore = useAuthStore();
const router = useRouter();
const currentPassword = ref('');
const pass1 = ref('');
const pass2 = ref('');
const loading = ref(false);
const error = ref('');

const validate = () => {
    if (pass1.value !== pass2.value) return 'Las contraseñas no coinciden';
    if (pass1.value === currentPassword.value) {
        return 'La nueva contraseña debe ser diferente a la actual';
    }
    if (pass1.value.length < 10) return 'La contraseña debe tener al menos 10 caracteres';
    if (!/[A-Za-z]/.test(pass1.value) || !/\d/.test(pass1.value)) {
        return 'La contraseña debe incluir letras y números';
    }
    return '';
};

const changePassword = async () => {
    error.value = validate();
    if (error.value) return;

    loading.value = true;
    try {
        await api.post('/auth/change-password', {
            current_password: currentPassword.value,
            new_password: pass1.value,
        });
        authStore.clearSession();
        alert('Contraseña cambiada. Inicie sesión nuevamente.');
        await router.push('/login');
    } catch (err) {
        error.value = err.response?.data?.detail || 'Error actualizando contraseña';
    } finally {
        loading.value = false;
    }
};
</script>
