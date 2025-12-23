<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <h1 class="text-2xl font-bold text-gray-800">Gestión de Inventario</h1>
      
      <!-- PESTAÑAS DE NAVEGACIÓN -->
      <div class="bg-white p-1 rounded-lg shadow-sm border flex">
        <button 
          @click="currentTab = 'products'"
          :class="['px-4 py-2 rounded-md text-sm font-medium transition', currentTab === 'products' ? 'bg-blue-100 text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
        >
          📦 Productos
        </button>
        <button 
          @click="currentTab = 'categories'"
          :class="['px-4 py-2 rounded-md text-sm font-medium transition', currentTab === 'categories' ? 'bg-blue-100 text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
        >
          🏷️ Categorías
        </button>
        <button 
          @click="currentTab = 'orders'"
          :class="['px-4 py-2 rounded-md text-sm font-medium transition', currentTab === 'orders' ? 'bg-blue-100 text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
        >
          🚛 Entradas / Pedidos
        </button>
        <button 
          @click="currentTab = 'adjustments'"
          v-if="authStore.isAdmin"
          :class="['px-4 py-2 rounded-md text-sm font-medium transition', currentTab === 'adjustments' ? 'bg-orange-100 text-orange-700 shadow-sm' : 'text-gray-500 hover:text-gray-700']"
        >
          🔧 Ajuste Stocks
        </button>
      </div>
    </div>

    <!-- AREA DE CONTENIDO DINÁMICO -->
    <div class="mt-4">
      <!-- Usamos KeepAlive para no perder datos al cambiar de pestaña -->
      <KeepAlive>
        <component :is="activeComponent" />
      </KeepAlive>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

// Importamos los componentes que antes eran vistas separadas
import ProductList from './ProductList.vue';      // El archivo que renombraste en Paso 1
import Categories from './Categories.vue';        // La vista de la Etapa 22
import PurchaseOrders from './PurchaseOrders.vue'; // La vista de la Etapa 20
import StockAdjustments from './StockAdjustments.vue'; // Importar
import { useAuthStore } from '../stores/auth'; 
const authStore = useAuthStore();
const currentTab = ref('products');

// Mapeo de string a componente
const activeComponent = computed(() => {
  switch (currentTab.value) {
    case 'products': return ProductList;
    case 'categories': return Categories;
    case 'orders': return PurchaseOrders;
    case 'adjustments': return StockAdjustments;
    default: return ProductList;
  }
});
</script>