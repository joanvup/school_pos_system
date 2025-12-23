<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100 p-4">
    <div class="max-w-md w-full bg-white rounded-xl shadow-lg p-8">
      <div class="text-center mb-8">
        <h2 class="text-3xl font-bold text-gray-900">School POS</h2>
        <p class="text-gray-500 mt-2">Ingresa a tu cuenta</p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-6">
        <div>
          <label class="block text-sm font-medium text-gray-700">Email</label>
          <input 
            v-model="email" 
            type="email" 
            required 
            class="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
            placeholder="usuario@colegio.com"
          >
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700">Contraseña</label>
          <input 
            v-model="password" 
            type="password" 
            required 
            class="mt-1 w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-primary outline-none transition"
            placeholder="••••••••"
          >
        </div>

        <div v-if="errorMessage" class="text-red-500 text-sm text-center bg-red-50 p-2 rounded">
          {{ errorMessage }}
        </div>

        <button 
          type="submit" 
          :disabled="loading"
          class="w-full bg-primary hover:bg-secondary text-white font-bold py-3 rounded-lg transition transform active:scale-95 flex justify-center"
        >
          <span v-if="!loading">Ingresar</span>
          <span v-else>Cargando...</span>
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';

const authStore = useAuthStore();
const router = useRouter();

const email = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref('');

const handleLogin = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    await authStore.login(email.value, password.value);
    
    // --- LÓGICA DE REDIRECCIÓN POR ROL ---
    const role = authStore.user?.role;

    if (role === 'padre') {
        router.push('/my-family');
    } else if (role === 'empleado') {
        router.push('/my-card');
    } else if (role === 'vendedor') {
        router.push('/pos');
    } else {
        // Admin y Supervisor
        router.push('/dashboard');
    }
    // -------------------------------------
    
  } catch (error) {
    errorMessage.value = 'Credenciales incorrectas o usuario inactivo';
  } finally {
    loading.value = false;
  }
};
</script>