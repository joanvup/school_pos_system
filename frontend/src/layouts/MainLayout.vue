<template>
  <div class="flex h-screen bg-gray-100 overflow-hidden font-sans">
    
    <!-- 1. HEADER MÓVIL (Visible solo en < md) -->
    <header class="md:hidden fixed top-0 left-0 right-0 h-16 bg-white shadow-sm border-b border-gray-100 z-40 flex items-center justify-between px-4">
        <button @click="isSidebarOpen = true" class="p-2 rounded-xl bg-gray-50 text-primary">
            <!-- Icono Hamburguesa -->
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16m-7 6h7" />
            </svg>
        </button>
        
        <div class="flex items-center gap-2">
            <img v-if="configStore.logoUrl" :src="configStore.logoUrl" class="h-8 w-auto">
            <span class="font-black text-primary text-sm uppercase tracking-tighter truncate max-w-[150px]">
                {{ configStore.settings.school_name }}
            </span>
        </div>

        <div class="w-10"></div> <!-- Espaciador para centrar logo -->
    </header>

    <!-- 2. BACKDROP (Fondo oscuro al abrir menú en móvil) -->
    <Transition name="fade">
        <div v-if="isSidebarOpen" @click="isSidebarOpen = false" class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40 md:hidden"></div>
    </Transition>

    <!-- 3. SIDEBAR (Escritorio y Móvil) -->
    <aside 
        :class="[
            'fixed inset-y-0 left-0 z-50 w-72 bg-white shadow-2xl md:shadow-none transform transition-transform duration-300 ease-in-out md:relative md:translate-x-0',
            isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
        ]"
    >
      <div class="flex flex-col h-full">
        
        <!-- Header del Sidebar -->
        <div class="p-6 text-center border-b flex flex-col items-center relative">
            <!-- Botón cerrar (Solo móvil) -->
            <button @click="isSidebarOpen = false" class="md:hidden absolute top-4 right-4 text-gray-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>

            <div v-if="configStore.logoUrl" class="w-20 h-20 mb-3 bg-white rounded-2xl p-2 shadow-sm border border-gray-100 flex items-center justify-center">
                <img :src="configStore.logoUrl" class="max-h-full max-w-full object-contain">
            </div>
            <div v-else class="text-4xl mb-2">🏫</div>

            <h1 class="text-xl font-black text-primary leading-tight uppercase tracking-tighter">
                {{ configStore.settings.school_name }}
            </h1>
            <p class="text-[10px] text-gray-400 font-bold uppercase tracking-[0.2em] mt-1">{{ role }}</p>
        </div>

        <!-- Navegación -->
        <nav class="flex-1 p-4 space-y-2 overflow-y-auto custom-scrollbar">
            <!-- Usamos un componente wrapper para cerrar el menú al hacer click -->
            <div @click="handleNavClick">
                <router-link v-if="['admin', 'supervisor'].includes(role)" to="/dashboard" class="menu-item" active-class="active">
                  <span class="mr-3">📊</span> Dashboard
                </router-link>

                <router-link v-if="['admin', 'supervisor'].includes(role)" to="/reports" class="menu-item" active-class="active">
                  <span class="mr-3">📈</span> Reportes
                </router-link>

                <router-link v-if="role === 'admin'" to="/users" class="menu-item" active-class="active">
                  <span class="mr-3">👥</span> Usuarios
                </router-link>
                
                <router-link v-if="role === 'admin'" to="/bulk-import" class="menu-item" active-class="active">
                  <span class="mr-3">📥</span> Carga Masiva
                </router-link>
                
                <router-link v-if="role === 'admin'" to="/students" class="menu-item" active-class="active">
                  <span class="mr-3">🎓</span> Estudiantes
                </router-link>

                <router-link v-if="['admin', 'supervisor', 'vendedor'].includes(role)" to="/pos" class="menu-item" active-class="active">
                  <span class="mr-3">🛒</span> Caja (POS)
                </router-link>

                <router-link v-if="['admin', 'supervisor'].includes(role)" to="/inventory" class="menu-item" active-class="active">
                  <span class="mr-3">📦</span> Inventario
                </router-link>

                <router-link v-if="role === 'padre'" to="/my-family" class="menu-item" active-class="active">
                  <span class="mr-3">👨‍👩‍👧‍👦</span> Mi Familia
                </router-link>

                <router-link v-if="role === 'empleado'" to="/my-card" class="menu-item" active-class="active">
                  <span class="mr-3">💳</span> Mi Tarjeta
                </router-link>

                <router-link to="/profile" class="menu-item" active-class="active">
                  <span class="mr-3">👤</span> Mi Perfil
                </router-link>

                <router-link v-if="role === 'admin'" to="/settings" class="menu-item" active-class="active">
                  <span class="mr-3">⚙️</span> Configuración
                </router-link>

                <router-link v-if="role === 'admin'" to="/balance-audit" class="menu-item" active-class="active">
                  <span class="mr-3">⚖️</span> Confrontar Saldos
                </router-link>
            </div>
        </nav>

        <!-- Footer del Sidebar -->
        <div class="p-4 border-t space-y-4">
            <div class="bg-gray-50 rounded-2xl p-4 border border-gray-100">
                <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Soporte</p>
                <a :href="'mailto:' + configStore.settings.school_support_email" class="text-xs font-bold text-primary truncate block hover:underline">
                    {{ configStore.settings.school_support_email }}
                </a>
            </div>
            
            <button @click="authStore.logout()" class="w-full flex items-center justify-center px-4 py-3 text-red-600 bg-red-50 hover:bg-red-100 rounded-2xl font-bold transition-colors">
              Cerrar Sesión
            </button>
        </div>
      </div>
    </aside>

    <!-- 4. CONTENIDO PRINCIPAL -->
    <main class="flex-1 overflow-y-auto p-4 md:p-8 pt-20 md:pt-8 transition-all duration-300">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useConfigStore } from '../stores/config';

const authStore = useAuthStore();
const configStore = useConfigStore();
const isSidebarOpen = ref(false);

const role = computed(() => authStore.user?.role || '');

// Función para cerrar el menú en móvil al hacer clic en una opción
const handleNavClick = () => {
    if (window.innerWidth < 768) {
        isSidebarOpen.value = false;
    }
};
</script>

<style scoped>
.menu-item {
    @apply flex items-center px-4 py-3 text-gray-500 rounded-2xl font-bold text-sm transition-all duration-200 hover:bg-gray-50 hover:text-primary mb-1;
}
.active {
    @apply bg-primary text-white shadow-lg shadow-blue-100 hover:bg-primary hover:text-white !important;
}

/* Animaciones Transición */
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
</style>