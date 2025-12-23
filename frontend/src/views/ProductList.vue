<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-800">Inventario de Productos</h1>
      <button @click="openModal()" class="bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg shadow transition">
        + Nuevo Producto
      </button>
    </div>

    <!-- Tabla de Productos -->
    <div class="bg-white rounded-xl shadow overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Producto</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Categoría</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Precio / Costo</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Stock</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Acciones</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-for="product in products" :key="product.id">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">{{ product.name }}</div>
              <div class="text-xs text-gray-500">{{ product.description }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-blue-100 text-blue-800">
                {{ product.category_rel?.name || 'Sin Cat' }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              <div class="font-bold text-green-600">{{ formatMoney(product.price) }}</div>
              <div class="text-xs">Costo: {{ formatMoney(product.cost) }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <div :class="{'text-red-600 font-bold': product.stock <= product.low_stock_threshold, 'text-gray-900': product.stock > product.low_stock_threshold}">
                {{ product.stock }} und.
              </div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button @click="openModal(product)" class="text-indigo-600 hover:text-indigo-900 mr-4">Editar</button>
              <button @click="handleDelete(product)" class="text-red-500 hover:text-red-700 font-bold">Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal Crear/Editar -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <h3 class="text-lg font-bold mb-4">{{ isEditing ? 'Editar Producto' : 'Nuevo Producto' }}</h3>
        
        <form @submit.prevent="saveProduct" class="space-y-4">
          <div>
            <label class="block text-sm font-medium text-gray-700">Nombre</label>
            <input v-model="form.name" required type="text" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2 outline-none focus:ring-primary focus:border-primary">
          </div>
          <div class="mt-4">
            <label class="block text-sm font-medium text-gray-700">Foto del Producto</label>
            <div class="mt-1 flex items-center gap-4">
                <!-- Vista previa si ya tiene imagen -->
                <img v-if="form.image_url" :src="baseUrl + form.image_url" class="h-16 w-16 object-cover rounded-lg border">
                <div v-else class="h-16 w-16 bg-gray-100 rounded-lg flex items-center justify-center text-2xl">📸</div>
        
                <input type="file" @change="handleImageUpload" accept="image/*" class="text-xs text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100">
            </div>
        </div>
          
          <div class="grid grid-cols-2 gap-4">
             <div>
                <label class="block text-sm font-medium text-gray-700">Categoría</label>
                <select v-model="form.category_id" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
                    <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                        {{ cat.name }}
                    </option>
                </select>
             </div>
             <div>
                <label class="block text-sm font-medium text-gray-700">Stock Inicial</label>
                <input v-model.number="form.stock" required disabled type="number" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
             </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
             <div>
                <label class="block text-sm font-medium text-gray-700">Precio Venta</label>
                <input v-model.number="form.price" required type="number" step="50" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
             </div>
             <div>
                <label class="block text-sm font-medium text-gray-700">Costo Compra</label>
                <input v-model.number="form.cost" required type="number" step="50" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
             </div>
          </div>
          
           <div>
            <label class="block text-sm font-medium text-gray-700">Alerta Stock Bajo</label>
            <input v-model.number="form.low_stock_threshold" required type="number" class="mt-1 block w-full border border-gray-300 rounded-md shadow-sm p-2">
          </div>

          <div class="flex justify-end gap-3 mt-6">
            <button type="button" @click="showModal = false" class="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200">Cancelar</button>
            <button type="submit" class="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-700">Guardar</button>
          </div>
        </form>
      </div>
    </div>
    
    
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';
import { useConfigStore } from '../stores/config';
const configStore = useConfigStore();

const baseUrl = configStore.baseUrl;

const products = ref([]);
const showModal = ref(false);
const isEditing = ref(false);
// Variables nuevas

const categories = ref([]);

const form = ref({
  name: '',
  category: 'General',
  price: 0,
  cost: 0,
  stock: 0,
  low_stock_threshold: 5,
  description: ''
});

const loadProducts = async () => {
  const resCat = await api.get('/categories/');
  categories.value = resCat.data;
  const { data } = await api.get('/products/');
  products.value = data;
};

const openModal = (product = null) => {
  if (product) {
    isEditing.value = true;
    form.value = { ...product }; // Copia para editar
  } else {
    isEditing.value = false;
    form.value = { name: '', category: 'General', price: 0, cost: 0, stock: 0, low_stock_threshold: 5 };
  }
  showModal.value = true;
};
const selectedFile = ref(null);

const handleImageUpload = (event) => {
    selectedFile.value = event.target.files[0];
};

const saveProduct = async () => {
  try {
    let productId = form.value.id;
    
    // 1. Guardar o actualizar datos básicos
    if (isEditing.value) {
      await api.put(`/products/${productId}`, form.value);
    } else {
      const res = await api.post('/products/', form.value);
      productId = res.data.id; // Obtenemos el ID del nuevo producto
    }

    // 2. Si hay una imagen seleccionada, subirla
    if (selectedFile.value) {
      const formData = new FormData();
      formData.append('file', selectedFile.value);
      await api.post(`/products/${productId}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
    }

    showModal.value = false;
    selectedFile.value = null;
    loadProducts();
    alert("Producto guardado con éxito");
  } catch (error) {
    alert("Error al guardar producto");
  }
};

// Funciones nuevas
const openStockModal = (product) => {
    selectedProduct.value = product;
    stockToAdd.value = 0;
    showStockModal.value = true;
};

const addStock = async () => {
    if (stockToAdd.value <= 0) return;
    
    // Calculamos el nuevo total
    const newStock = selectedProduct.value.stock + stockToAdd.value;
    
    try {
        // Reusamos el endpoint de update (PUT)
        await api.put(`/products/${selectedProduct.value.id}`, {
            stock: newStock
        });
        showStockModal.value = false;
        loadProducts(); // Refrescar tabla
        alert("Stock actualizado correctamente");
    } catch (error) {
        alert("Error actualizando stock");
    }
};
const handleDelete = async (product) => {
    if (!confirm(`¿Está seguro de eliminar '${product.name}'? Esta acción no se puede deshacer.`)) return;

    try {
        await api.delete(`/products/${product.id}`);
        alert("Producto eliminado correctamente");
        loadProducts(); // Refrescar tabla
    } catch (error) {
        // Mostramos el mensaje detallado del backend (si tiene movimientos)
        alert(error.response?.data?.detail || "Error al intentar eliminar");
    }
};




onMounted(loadProducts);
</script>