<template>
  <div class="min-h-full space-y-8 pb-12">
    <!-- CABECERA DE BIENVENIDA -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tight">Panel de Control</h1>
        <p class="text-gray-500 font-medium">Estado de la cafetería al {{ currentDate }}</p>
      </div>
      <div class="flex gap-2">
        <button 
          @click="loadData" 
          class="flex items-center gap-2 bg-white border border-gray-200 px-4 py-2 rounded-xl text-sm font-bold text-gray-600 hover:bg-gray-50 transition shadow-sm"
        >
          <span>🔄</span> Actualizar Datos
        </button>
      </div>
    </div>

    <!-- SECCIÓN 1: KPIs DE ALTO IMPACTO -->
    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
      <!-- Venta Diaria -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition">
        <div class="flex justify-between items-start">
          <div class="p-3 bg-green-50 rounded-xl text-2xl">💰</div>
          <span class="text-[10px] font-black text-green-600 bg-green-100 px-2 py-1 rounded-full uppercase">Hoy</span>
        </div>
        <div class="mt-4">
          <div class="text-gray-500 text-xs font-bold uppercase tracking-wider">Ingresos Totales</div>
          <div class="text-3xl font-black text-gray-900">{{ formatMoney(stats.sales_today) }}</div>
        </div>
      </div>

      <!-- Volumen de Ventas -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition">
        <div class="flex justify-between items-start">
          <div class="p-3 bg-blue-50 rounded-xl text-2xl">🛒</div>
          <span class="text-[10px] font-black text-blue-600 bg-blue-100 px-2 py-1 rounded-full uppercase">Actividad</span>
        </div>
        <div class="mt-4">
          <div class="text-gray-500 text-xs font-bold uppercase tracking-wider">Transacciones Realizadas</div>
          <div class="text-3xl font-black text-gray-900">{{ stats.transactions_today }}</div>
        </div>
      </div>

      <!-- Alerta de Abastecimiento -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition" :class="{'ring-2 ring-red-500 bg-red-50/30': stats.low_stock_alert > 0}">
        <div class="flex justify-between items-start">
          <div class="p-3 bg-red-50 rounded-xl text-2xl">📦</div>
          <span v-if="stats.low_stock_alert > 0" class="text-[10px] font-black text-red-600 bg-red-100 px-2 py-1 rounded-full animate-pulse uppercase">Crítico</span>
        </div>
        <div class="mt-4">
          <div class="text-gray-500 text-xs font-bold uppercase tracking-wider">Productos Stock Bajo</div>
          <div class="text-3xl font-black text-gray-900">{{ stats.low_stock_alert }}</div>
        </div>
      </div>

      <!-- Comunidad -->
      <div class="bg-white p-6 rounded-2xl shadow-sm border border-gray-100 flex flex-col justify-between hover:shadow-md transition">
        <div class="flex justify-between items-start">
          <div class="p-3 bg-purple-50 rounded-xl text-2xl">🎓</div>
        </div>
        <div class="mt-4">
          <div class="text-gray-500 text-xs font-bold uppercase tracking-wider">Usuarios en el Sistema</div>
          <div class="text-3xl font-black text-gray-900">{{ stats.total_users }}</div>
        </div>
      </div>
    </div>

    <!-- SECCIÓN 2: GRÁFICOS Y DETALLES -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
      
      <!-- TOP PRODUCTOS (VISUALIZACIÓN DE BARRAS) -->
      <div class="lg:col-span-2 bg-white rounded-3xl shadow-sm border border-gray-100 overflow-hidden">
        <div class="p-6 border-b border-gray-50 flex justify-between items-center">
          <h3 class="font-black text-gray-800 text-lg uppercase tracking-tight">Rendimiento por Producto</h3>
          <span class="text-xs text-gray-400">Histórico de Ventas</span>
        </div>
        <div class="p-8 space-y-6">
          <div v-for="(prod, index) in topProducts" :key="index" class="space-y-2">
            <div class="flex justify-between items-end">
              <span class="text-sm font-bold text-gray-700">{{ prod.name }}</span>
              <span class="text-xs font-black text-blue-600">{{ prod.sold }} unidades</span>
            </div>
            <div class="w-full bg-gray-100 h-3 rounded-full overflow-hidden">
              <!-- La barra se calcula proporcional al primero (el más vendido) -->
              <div 
                class="bg-blue-500 h-full rounded-full transition-all duration-1000 ease-out"
                :style="{ width: getPercentage(prod.sold) + '%' }"
              ></div>
            </div>
          </div>
          <div v-if="topProducts.length === 0" class="text-center py-12 text-gray-400">
            Aún no hay datos de ventas registrados.
          </div>
        </div>
      </div>

      <!-- ESTADO DEL SISTEMA -->
      <div class="flex flex-col gap-6">
        <!-- Tarjeta de Alerta Rápida -->
        <div class="bg-gray-900 text-white p-6 rounded-3xl shadow-xl flex flex-col justify-between h-full relative overflow-hidden">
            <div class="z-10">
                <h3 class="font-bold opacity-70 text-xs uppercase tracking-widest mb-4">Aviso de Operación</h3>
                <p v-if="stats.low_stock_alert > 0" class="text-xl font-medium leading-relaxed">
                    Hay <span class="text-red-400 font-black">{{ stats.low_stock_alert }} productos</span> que requieren reposición inmediata para evitar pérdida de ventas.
                </p>
                <p v-else class="text-xl font-medium leading-relaxed">
                    El inventario se encuentra en <span class="text-green-400 font-black">estado óptimo</span>. No hay alertas de stock para hoy.
                </p>
            </div>
            <!-- Decoración visual -->
            <div class="absolute -right-8 -bottom-8 text-9xl opacity-10">📊</div>
        </div>

        <!-- Resumen de Valoración -->
        <div class="bg-indigo-600 text-white p-6 rounded-3xl shadow-xl">
            <h3 class="font-bold opacity-70 text-[10px] uppercase tracking-widest mb-2">Valoración del Día</h3>
            <div class="text-xs opacity-80 mb-4">Promedio por Transacción:</div>
            <div class="text-3xl font-black">
                {{ formatMoney(stats.sales_today / (stats.transactions_today || 1)) }}
            </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters'; 

const stats = ref({
    sales_today: 0,
    transactions_today: 0,
    low_stock_alert: 0,
    total_users: 0
});
const topProducts = ref([]);
const loading = ref(true);

const currentDate = computed(() => {
    return new Date().toLocaleDateString('es-ES', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
    });
});

const loadData = async () => {
  loading.value = true;
  try {
    const { data } = await api.get('/reports/dashboard');
    console.log("Datos recibidos del server:", data); // <--- AGREGA ESTO PARA DEBUG
    stats.value = data.stats;
    topProducts.value = data.top_products;
  } catch (error) {
    console.error("Error cargando dashboard:", error);
  } finally {
    loading.value = false;
  }
};

// Calcula el ancho de la barra comparando con el producto más vendido
const getPercentage = (sold) => {
    if (topProducts.value.length === 0) return 0;
    const maxSold = topProducts.value[0].sold;
    return (sold / maxSold) * 100;
};

onMounted(loadData);
</script>

<style scoped>
/* Transición suave para las barras de progreso */
.transition-all {
  transition-property: all;
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
  transition-duration: 1000ms;
}
</style>