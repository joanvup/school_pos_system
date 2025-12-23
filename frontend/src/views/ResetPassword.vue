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
                   class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
            
            <input v-model="confirmPassword" type="password" placeholder="Confirmar contraseña" required
                   class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">

            <button type="submit" :disabled="loading"
                    class="w-full bg-primary text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-200">
                {{ loading ? 'Actualizando...' : 'ACTUALIZAR CONTRASEÑA' }}
            </button>
        </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '../api/axios';

const route = useRoute();
const router = useRouter();
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);

const handleReset = async () => {
    if(newPassword.value !== confirmPassword.value) return alert("Las contraseñas no coinciden");
    
    loading.value = true;
    try {
        await api.post('/auth/reset-password', null, {
            params: {
                token: route.query.token,
                new_password: newPassword.value
            }
        });
        alert("✅ Contraseña actualizada. Ahora puedes iniciar sesión.");
        router.push('/login');
    } catch (e) {
        alert("El enlace ha expirado o es inválido.");
    } finally {
        loading.value = false;
    }
};
</script>