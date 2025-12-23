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
            <label class="text-sm">Nueva Contraseña</label>
            <input v-model="pass1" type="password" required class="w-full border p-2 rounded">
        </div>
        <div>
            <label class="text-sm">Confirmar Contraseña</label>
            <input v-model="pass2" type="password" required class="w-full border p-2 rounded">
        </div>
        <button type="submit" class="w-full bg-gray-800 text-white py-2 rounded hover:bg-black">Actualizar</button>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import api from '../api/axios';

const authStore = useAuthStore();
const pass1 = ref('');
const pass2 = ref('');

const changePassword = async () => {
    if(pass1.value !== pass2.value) return alert("Las contraseñas no coinciden");
    
    try {
        // Usamos el endpoint de update user (PUT /users/{id})
        // Nota: Un usuario normal solo debería poder editarse a si mismo.
        // Si el endpoint pide ser Admin, habría que crear uno nuevo /users/me en backend.
        // Por simplicidad, asumiremos que creamos /users/me o que el endpoint permite editarse a uno mismo.
        
        // FIX RÁPIDO: Crear endpoint /users/me en backend para editarse uno mismo, 
        // o usar el ID del store si el backend lo permite.
        await api.put(`/users/${authStore.user.id}`, { password: pass1.value });
        alert("Contraseña cambiada. Vuelve a iniciar sesión.");
        authStore.logout();
    } catch (error) {
        alert("Error actualizando contraseña");
    }
};
</script>