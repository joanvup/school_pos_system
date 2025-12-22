<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">Gestión de Estudiantes</h1>
      <button @click="openCreateModal" class="bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg shadow transition">
        + Nuevo Estudiante
      </button>
    </div>

    <!-- Tabla de Estudiantes -->
    <div class="bg-white rounded-xl shadow overflow-hidden">
      <div v-if="loading" class="p-4 text-center text-gray-500">Cargando datos...</div>
      
      <table v-else class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Estudiante</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Grado/Curso</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Acudiente (ID)</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tarjeta RFID</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="student in students" :key="student.id">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-bold text-gray-900">{{ student.full_name }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">
                {{ student.grade }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              <!-- Mostramos el nombre del padre buscándolo en la lista de usuarios cargados -->
              {{ getParentName(student.parent_id) }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
               <!-- Verificaríamos si tiene tarjeta en un endpoint más completo, 
                    por ahora simulamos estado basado en si podemos asignarle otra -->
               <span v-if="student.has_card" class="text-green-600 font-bold text-xs">✔ Asignada</span>
               <span v-else class="text-gray-400 text-xs">Sin Tarjeta</span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button @click="openCardModal(student)" class="text-accent hover:text-orange-700 font-bold border border-accent px-3 py-1 rounded hover:bg-orange-50 transition">
                💳 Vincular Tarjeta
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- MODAL 1: Crear Estudiante -->
    <div v-if="showCreate" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold mb-4">Registrar Estudiante</h3>
        
        <form @submit.prevent="createStudent" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">Nombre Completo</label>
            <input v-model="form.full_name" required type="text" class="mt-1 block w-full border border-gray-300 rounded p-2 outline-none focus:ring-primary focus:border-primary">
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700">Grado / Curso</label>
            <input v-model="form.grade" required type="text" placeholder="Ej: 5A" class="mt-1 block w-full border border-gray-300 rounded p-2 outline-none">
          </div>
          
          <div>
            <label class="block text-sm font-medium text-gray-700">Padre / Acudiente</label>
            <select v-model="form.parent_id" required class="mt-1 block w-full border border-gray-300 rounded p-2 outline-none bg-white">
                <option :value="null" disabled>Seleccione un padre...</option>
                <option v-for="user in parents" :key="user.id" :value="user.id">
                    {{ user.full_name }} ({{ user.email }})
                </option>
            </select>
            <p class="text-xs text-gray-500 mt-1">Solo aparecen usuarios con rol 'Padre'.</p>
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button type="button" @click="showCreate = false" class="px-4 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200">Cancelar</button>
            <button type="submit" class="px-4 py-2 bg-primary text-white rounded hover:bg-blue-700">Guardar</button>
          </div>
        </form>
      </div>
    </div>

    <!-- MODAL 2: Asignar Tarjeta (Enrollment) -->
    <div v-if="showCard" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-8 text-center">
        <div class="text-5xl mb-4">📡</div>
        <h3 class="text-xl font-bold mb-2">Asignar Tarjeta</h3>
        <p class="text-gray-600 mb-4">Estudiante: <span class="font-bold">{{ selectedStudent?.full_name }}</span></p>
        
        <p class="text-sm text-gray-500 mb-4">Pase la tarjeta por el lector ahora...</p>

        <input 
          ref="cardInput"
          v-model="cardUid" 
          @keyup.enter="assignCard"
          type="text" 
          class="w-full border-2 border-primary rounded p-2 text-center font-mono font-bold text-lg outline-none"
          placeholder="Esperando lectura..."
          autofocus
        >
        
        <div v-if="cardError" class="text-red-500 text-sm mt-2 font-bold">{{ cardError }}</div>

        <button @click="showCard = false" class="mt-6 text-gray-500 underline text-sm">Cancelar</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue';
import api from '../api/axios';

const students = ref([]);
const parents = ref([]); // Lista de usuarios rol PADRE
const loading = ref(true);

// Modales
const showCreate = ref(false);
const showCard = ref(false);

// Forms
const form = ref({ full_name: '', grade: '', parent_id: null });
const selectedStudent = ref(null);
const cardUid = ref('');
const cardInput = ref(null);
const cardError = ref('');

// Cargar Datos Iniciales
const loadData = async () => {
  loading.value = true;
  try {
    // 1. Cargar Estudiantes
    const resStudents = await api.get('/students/');
    students.value = resStudents.data;
    
    // 2. Cargar Usuarios para filtrar Padres (Necesario para el select)
    // Nota: En un sistema gigante esto se haría con búsqueda en backend, 
    // pero para colegio mediano cargar todos los usuarios es aceptable.
    const resUsers = await api.get('/users/');
    parents.value = resUsers.data.filter(u => u.role === 'padre');
    
  } catch (error) {
    console.error(error);
  } finally {
    loading.value = false;
  }
};

// Helper para mostrar nombre del padre en la tabla
const getParentName = (parentId) => {
    const parent = parents.value.find(p => p.id === parentId);
    return parent ? parent.full_name : `ID: ${parentId}`;
};

// Crear Estudiante
const openCreateModal = () => {
    form.value = { full_name: '', grade: '', parent_id: null };
    showCreate.value = true;
};

const createStudent = async () => {
    try {
        await api.post('/students/', form.value);
        showCreate.value = false;
        loadData(); // Recargar tabla
    } catch (error) {
        alert("Error creando estudiante. Verifique datos.");
    }
};

// Asignar Tarjeta
const openCardModal = (student) => {
    selectedStudent.value = student;
    cardUid.value = '';
    cardError.value = '';
    showCard.value = true;
    
    // Auto-focus al input
    nextTick(() => {
        if(cardInput.value) cardInput.value.focus();
    });
};

const assignCard = async () => {
    if(!cardUid.value) return;
    
    try {
        await api.post('/cards/', {
            uid: cardUid.value,
            student_id: selectedStudent.value.id,
            daily_limit: 50000 // Limite por defecto
        });
        alert("¡Tarjeta vinculada exitosamente!");
        showCard.value = false;
        // Opcional: Marcar visualmente que ya tiene tarjeta
        selectedStudent.value.has_card = true; 
    } catch (error) {
        cardError.value = error.response?.data?.detail || "Error al asignar tarjeta";
        cardUid.value = ''; // Limpiar para reintentar
    }
};

onMounted(loadData);
</script>