<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <h1 class="text-2xl font-bold text-gray-800">Gestión de Usuarios</h1>
      <button @click="openModal()" class="bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg shadow transition">
        + Nuevo Usuario
      </button>
    </div>

    <!-- BARRA DE BÚSQUEDA Y FILTROS -->
    <div class="bg-white p-4 rounded-xl shadow flex flex-col md:flex-row gap-4 items-center justify-between">
        <div class="relative w-full md:w-96">
            <span class="absolute left-3 top-2.5 text-gray-400">🔍</span>
            <input 
                v-model="searchQuery" 
                @input="handleSearch"
                type="text" 
                placeholder="Buscar por nombre o email..." 
                class="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-primary outline-none"
            >
        </div>
        
        <!-- PAGINACIÓN -->
        <div class="flex items-center gap-2">
            <button 
                @click="prevPage" 
                :disabled="page === 1"
                class="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
            >
                ◀ Anterior
            </button>
            <span class="text-sm font-bold text-gray-600">Pág. {{ page }}</span>
            <button 
                @click="nextPage" 
                :disabled="users.length < limit" 
                class="px-3 py-1 border rounded hover:bg-gray-100 disabled:opacity-50"
            >
                Siguiente ▶
            </button>
        </div>
    </div>

    <!-- TABLA -->
    <div class="bg-white rounded-xl shadow overflow-hidden">
      <div v-if="loading" class="p-8 text-center text-gray-500">Cargando usuarios...</div>
      
      <div v-else-if="users.length === 0" class="p-8 text-center text-gray-500">
          No se encontraron usuarios.
      </div>

      <table v-else class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Usuario</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rol</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tarjeta</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="user in users" :key="user.id">
            <td class="px-6 py-4">
              <div class="text-sm font-medium text-gray-900">{{ user.full_name }}</div>
              <div class="text-xs text-gray-500">{{ user.email }}</div>
            </td>
            <td class="px-6 py-4">
               <span class="px-2 py-1 text-xs font-semibold rounded-full uppercase bg-gray-100 text-gray-800">
                {{ user.role }}
               </span>
            </td>
            <!-- Columna Tarjeta en Users.vue -->
            <td class="px-6 py-4">
                <!-- CASO 1: TIENE TARJETA -->
                <div v-if="user.card" class="flex items-center gap-2">
                    <span class="bg-gray-100 text-gray-800 text-xs font-mono px-2 py-1 rounded border border-gray-300">
                        {{ user.card.uid }}
                    </span>
                <!-- Opcional: Botón pequeño para re-asignar o bloquear -->
                    <button @click="openCardModal(user)" class="text-blue-500 text-xs hover:underline" title="Cambiar tarjeta">
                        ✏️
                    </button>
                </div>

                <!-- CASO 2: NO TIENE TARJETA (Y NO ES PADRE) -->
                <div v-else-if="user.role !== 'padre'">
                    <button 
                        @click="openCardModal(user)" 
                        class="text-accent border border-accent px-2 py-0.5 rounded text-xs hover:bg-orange-50 font-bold"
                    >
                        💳 Asignar
                    </button>
                </div>

                <!-- CASO 3: ES PADRE (NO APLICA) -->
                <span v-else class="text-gray-300 text-xs">-</span>
            </td>
            <td class="px-6 py-4 text-right text-sm font-medium">
              <button @click="openModal(user)" class="text-indigo-600 hover:text-indigo-900">Editar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- (MANTENER LOS MISMOS MODALES QUE TENIAS ANTES) -->
    <!-- ... Copia aquí el Modal de Crear Usuario y el Modal de Tarjeta del paso anterior ... -->
    <!-- Por brevedad, asumo que mantienes los modales <div v-if="showModal">...</div> -->
    
    <!-- MODAL 1: CREAR/EDITAR USUARIO (Repetido para completitud si lo necesitas) -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
       <!-- ... contenido del modal ... -->
       <div class="bg-white rounded-lg p-6 w-96">
           <h3 class="font-bold mb-4">Usuario</h3>
           <form @submit.prevent="saveUser" class="space-y-4">
               <input v-model="form.full_name" placeholder="Nombre" class="w-full border p-2 rounded" required>
               <input v-model="form.email" placeholder="Email" class="w-full border p-2 rounded" required :disabled="isEditing">
               <select v-model="form.role" class="w-full border p-2 rounded">
                   <option value="padre">Padre de Familia</option>
                   <option value="empleado">Empleado</option>
                   <option value="vendedor">Vendedor</option>
                   <option value="supervisor">Supervisor</option>
                   <option value="admin">Administrador</option>
               </select>
               <input v-model="form.password" type="password" placeholder="Password" class="w-full border p-2 rounded" :required="!isEditing">
               <div class="flex justify-end gap-2">
                   <button type="button" @click="showModal=false" class="px-4 py-2 bg-gray-200 rounded">Cancelar</button>
                   <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded">Guardar</button>
               </div>
           </form>
       </div>
    </div>

    <!-- MODAL 2: TARJETA -->
    <div v-if="showCardModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
       <div class="bg-white rounded-lg p-6 w-96 text-center">
           <h3 class="font-bold">Asignar Tarjeta</h3>
           <input v-model="cardUid" @keyup.enter="assignCard" class="w-full border-2 border-blue-500 p-2 mt-4 text-center font-bold" placeholder="Escanear aquí..." autofocus>
           <button @click="showCardModal=false" class="mt-4 underline text-gray-500">Cancelar</button>
       </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import api from '../api/axios';
import { debounce } from 'lodash'; // Si no tienes lodash, haremos un debounce manual

const users = ref([]);
const loading = ref(false);
const showModal = ref(false);
const isEditing = ref(false);
const form = ref({});
// Variables de Tarjeta
const showCardModal = ref(false);
const selectedUser = ref(null);
const cardUid = ref('');

// PAGINACIÓN Y BÚSQUEDA
const page = ref(1);
const limit = ref(10); // 10 usuarios por página
const searchQuery = ref('');
let searchTimeout = null;

const loadUsers = async () => {
    loading.value = true;
    try {
        const skip = (page.value - 1) * limit.value;
        const { data } = await api.get('/users/', {
            params: {
                skip: skip,
                limit: limit.value,
                search: searchQuery.value || undefined
            }
        });
        users.value = data;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

const nextPage = () => {
    page.value++;
    loadUsers();
};

const prevPage = () => {
    if (page.value > 1) {
        page.value--;
        loadUsers();
    }
};

// Debounce manual para no saturar API al escribir
const handleSearch = () => {
    page.value = 1; // Reset a primera página
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
        loadUsers();
    }, 500); // Espera 500ms después de dejar de escribir
};

// CRUD
const openModal = (user = null) => {
    if (user) {
        isEditing.value = true;
        form.value = { ...user, password: '' };
    } else {
        isEditing.value = false;
        form.value = { full_name: '', email: '', role: 'vendedor', password: '', is_active: true };
    }
    showModal.value = true;
};

const saveUser = async () => {
    try {
        if (isEditing.value) {
            const payload = { ...form.value };
            if (!payload.password) delete payload.password;
            await api.put(`/users/${form.value.id}`, payload);
        } else {
            await api.post('/users/', form.value);
        }
        showModal.value = false;
        loadUsers();
    } catch (error) {
        alert("Error gestionando usuario");
    }
};

// TARJETA
const openCardModal = (user) => {
    selectedUser.value = user;
    cardUid.value = '';
    showCardModal.value = true;
};
const assignCard = async () => {
    if(!cardUid.value) return;
    try {
        await api.post('/cards/', {
            uid: cardUid.value,
            user_id: selectedUser.value.id,
            daily_limit: 100000
        });
        alert("Tarjeta asignada");
        showCardModal.value = false;
    } catch (e) { alert("Error asignando"); }
};

onMounted(loadUsers);
</script>