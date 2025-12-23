<template>
  <div class="flex h-screen bg-gray-100">
    <!-- Sidebar -->
    <aside class="w-64 bg-white shadow-md hidden md:flex flex-col">
      <div class="p-6 text-center border-b flex flex-col items-center">
        <!-- LOGO DINÁMICO -->
        <div v-if="configStore.logoUrl" class="w-20 h-20 mb-3 bg-white rounded-2xl p-2 shadow-sm border border-gray-100 flex items-center justify-center">
            <img :src="configStore.logoUrl" class="max-h-full max-w-full object-contain">
        </div>
        <div v-else class="text-4xl mb-2">🏫</div>

        <!-- NOMBRE DINÁMICO -->
        <h1 class="text-xl font-black text-primary leading-tight uppercase tracking-tighter">
            {{ configStore.settings.school_name }}
        </h1>
        <p class="text-[10px] text-gray-400 font-bold uppercase tracking-[0.2em] mt-1">Gestión Digital</p>
      </div>

      <nav class="flex-1 p-4 space-y-2 overflow-y-auto">
        
        <!-- DASHBOARD: ADMIN Y SUPERVISOR -->
        <router-link v-if="['admin', 'supervisor'].includes(role)" to="/dashboard" class="menu-item" active-class="active">
          <span>📊 Dashboard</span>
        </router-link>

        <!-- REPORTES: ADMIN Y SUPERVISOR (NUEVO) -->
        <router-link v-if="['admin', 'supervisor'].includes(role)" to="/reports" class="menu-item" active-class="active">
          <span>📈 Reportes</span>
        </router-link>

        <!-- SOLO ADMIN -->
        <router-link v-if="role === 'admin'" to="/users" class="menu-item" active-class="active">
          <span>👥 Usuarios</span>
        </router-link>
        
        <router-link v-if="role === 'admin'" to="/bulk-import" class="menu-item" active-class="active">
          <span>📥 Carga Masiva</span>
        </router-link>
        
        <router-link v-if="role === 'admin'" to="/students" class="menu-item" active-class="active">
          <span>🎓 Estudiantes</span>
        </router-link>

        <!-- POS: VENDEDOR, ADMIN, SUPERVISOR -->
        <router-link v-if="['admin', 'supervisor', 'vendedor'].includes(role)" to="/pos" class="menu-item" active-class="active">
          <span>🛒 Caja (POS)</span>
        </router-link>

        <!-- INVENTARIO: ADMIN Y SUPERVISOR -->
        <router-link v-if="['admin', 'supervisor'].includes(role)" to="/inventory" class="menu-item" active-class="active">
          <span>📦 Inventario</span>
        </router-link>


        <!-- PADRES -->
        <router-link v-if="role === 'padre'" to="/my-family" class="menu-item" active-class="active">
          <span>👨‍👩‍👧‍👦 Mi Familia</span>
        </router-link>

        <!-- EMPLEADO -->
        <router-link v-if="role === 'empleado'" to="/my-card" class="menu-item" active-class="active">
          <span>💳 Mi Tarjeta</span>
        </router-link>

        <!-- PERFIL (TODOS) -->
        <router-link to="/profile" class="menu-item" active-class="active">
          <span>👤 Mi Perfil</span>
        </router-link>

        <!-- SOLO ADMIN -->
        <router-link v-if="role === 'admin'" to="/settings" class="menu-item" active-class="active">
          <span>⚙️ Configuración</span>
        </router-link>

      </nav>
      <!-- Al final del nav, antes del botón de Cerrar Sesión -->
      <div class="mt-auto p-4 px-6">
          <div class="bg-gray-50 rounded-2xl p-4 border border-gray-100">
              <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Soporte Técnico</p>
              <a :href="'mailto:' + configStore.settings.school_support_email" class="text-xs font-bold text-primary truncate block hover:underline">
                  {{ configStore.settings.school_support_email || 'soporte@colegio.com' }}
              </a>
          </div>
      </div>

      <div class="p-4 border-t">
        <button @click="authStore.logout()" class="w-full flex items-center justify-center px-4 py-2 text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition">
          Cerrar Sesión
        </button>
      </div>
    </aside>

    <!-- Contenido Principal -->
    <main class="flex-1 overflow-y-auto p-4 md:p-8">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useConfigStore } from '../stores/config';
const configStore = useConfigStore();

const authStore = useAuthStore();

// Computed seguro: si user es null, devuelve string vacío para que no rompa el .includes()
const role = computed(() => {
    return authStore.user?.role || '';
});
</script>

<style scoped>
.menu-item {
    @apply flex items-center px-4 py-3 text-gray-700 rounded-lg hover:bg-gray-100 transition mb-1;
}
.active {
    @apply bg-blue-600 text-white hover:bg-blue-700;
}
</style>