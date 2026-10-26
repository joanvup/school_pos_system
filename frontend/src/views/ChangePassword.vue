<template>
  <div class="max-w-md mx-auto mt-10 bg-white p-8 rounded-3xl shadow-sm border border-slate-100">
    <div class="mb-8">
      <h1 class="text-2xl font-black text-slate-900 tracking-tight">Cambiar contraseña</h1>
      <p v-if="forced" class="mt-3 text-sm text-amber-700 bg-amber-50 border border-amber-100 rounded-2xl p-4">
        Por seguridad, debes cambiar la contraseña antes de usar el sistema.
      </p>
      <p v-else class="mt-2 text-sm text-slate-500">
        Al cambiarla se cerrarán todas tus sesiones.
      </p>
    </div>

    <form @submit.prevent="submit" class="space-y-4">
      <div>
        <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Contraseña actual</label>
        <input v-model="currentPassword" type="password" required autocomplete="current-password"
               class="w-full p-4 bg-slate-50 border-2 border-slate-100 rounded-2xl outline-none focus:border-primary font-bold">
      </div>
      <div>
        <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Nueva contraseña</label>
        <input v-model="newPassword" type="password" required autocomplete="new-password"
               class="w-full p-4 bg-slate-50 border-2 border-slate-100 rounded-2xl outline-none focus:border-primary font-bold">
      </div>
      <div>
        <label class="block text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Confirmar contraseña</label>
        <input v-model="confirmPassword" type="password" required autocomplete="new-password"
               class="w-full p-4 bg-slate-50 border-2 border-slate-100 rounded-2xl outline-none focus:border-primary font-bold">
      </div>

      <p class="text-xs text-slate-400">
        Mínimo 10 caracteres, con letras y números. No uses contraseñas comunes.
      </p>

      <div v-if="error" class="bg-red-50 text-red-600 p-4 rounded-2xl text-sm font-bold border border-red-100">
        {{ error }}
      </div>

      <button type="submit" :disabled="loading"
              class="w-full bg-slate-900 hover:bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-widest disabled:opacity-50">
        {{ loading ? 'Actualizando...' : 'Actualizar contraseña' }}
      </button>
    </form>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import api from '../api/axios';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
const router = useRouter();

const currentPassword = ref('');
const newPassword = ref('');
const confirmPassword = ref('');
const loading = ref(false);
const error = ref('');

const forced = computed(() => authStore.mustChangePassword);

const validate = () => {
  if (newPassword.value !== confirmPassword.value) {
    return 'Las contraseñas no coinciden';
  }
  if (newPassword.value === currentPassword.value) {
    return 'La nueva contraseña debe ser diferente a la actual';
  }
  if (newPassword.value.length < 10) {
    return 'La contraseña debe tener al menos 10 caracteres';
  }
  if (!/[A-Za-z]/.test(newPassword.value) || !/\d/.test(newPassword.value)) {
    return 'La contraseña debe incluir letras y números';
  }
  return '';
};

const submit = async () => {
  error.value = validate();
  if (error.value) return;

  loading.value = true;
  try {
    await api.post('/auth/change-password', {
      current_password: currentPassword.value,
      new_password: newPassword.value,
    });
    authStore.clearSession();
    await router.push({ path: '/login', query: { changed: '1' } });
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudo actualizar la contraseña';
  } finally {
    loading.value = false;
  }
};
</script>
