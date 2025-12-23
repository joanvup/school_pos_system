<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">Categorías de Productos</h1>
      <button @click="openModal()" class="bg-primary text-white px-4 py-2 rounded shadow">+ Nueva Categoría</button>
    </div>

    <div class="bg-white rounded-xl shadow p-4 max-w-2xl">
      <table class="w-full text-left">
        <thead>
          <tr class="border-b">
            <th class="p-3">Nombre</th>
            <th class="p-3 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="cat in categories" :key="cat.id" class="border-b hover:bg-gray-50">
            <td class="p-3 font-medium">{{ cat.name }}</td>
            <td class="p-3 text-right space-x-2">
              <button @click="openModal(cat)" class="text-blue-600 hover:underline">Editar</button>
              <button @click="deleteCategory(cat)" class="text-red-600 hover:underline">Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white p-6 rounded-lg shadow-xl w-96">
        <h3 class="font-bold mb-4">{{ isEditing ? 'Editar' : 'Nueva' }} Categoría</h3>
        <input v-model="form.name" class="w-full border p-2 rounded mb-4" placeholder="Nombre (Ej: Bebidas)">
        <div class="flex justify-end gap-2">
          <button @click="showModal = false" class="px-4 py-2 bg-gray-100 rounded">Cancelar</button>
          <button @click="save" class="px-4 py-2 bg-primary text-white rounded">Guardar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const categories = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
const form = ref({ id: null, name: '' });

const loadData = async () => {
    const { data } = await api.get('/categories/');
    categories.value = data;
};

const openModal = (cat = null) => {
    if (cat) {
        isEditing.value = true;
        form.value = { ...cat };
    } else {
        isEditing.value = false;
        form.value = { name: '' };
    }
    showModal.value = true;
};

const save = async () => {
    try {
        if (isEditing.value) {
            await api.put(`/categories/${form.value.id}`, { name: form.value.name });
        } else {
            await api.post('/categories/', { name: form.value.name });
        }
        showModal.value = false;
        loadData();
    } catch (e) {
        alert("Error guardando categoría");
    }
};

const deleteCategory = async (cat) => {
    if(!confirm(`¿Eliminar categoría '${cat.name}'?`)) return;
    try {
        await api.delete(`/categories/${cat.id}`);
        loadData();
    } catch (error) {
        alert(error.response?.data?.detail || "Error eliminando");
    }
};

onMounted(loadData);
</script>