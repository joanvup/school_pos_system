<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg border">
      <div class="md:col-span-2">
        <label class="block text-[10px] font-black text-gray-400 uppercase mb-1">Rango de Búsqueda (Fecha de OC)</label>
        <div class="flex gap-2">
            <input v-model="filters.start_date" type="date" class="flex-1 text-sm border p-2 rounded-lg shadow-sm">
            <input v-model="filters.end_date" type="date" class="flex-1 text-sm border p-2 rounded-lg shadow-sm">
        </div>
      </div>
      <div class="flex items-end gap-2">
        <button @click="loadData" class="bg-primary text-white px-4 py-2 rounded-lg font-bold flex-1 hover:bg-blue-700 transition shadow-md">
            Filtrar OC
        </button>
        <button @click="exportData('excel')" class="bg-green-600 text-white px-3 py-2 rounded-lg text-xs font-bold shadow-sm">Excel</button>
        <button @click="exportData('pdf')" class="bg-red-600 text-white px-3 py-2 rounded-lg text-xs font-bold shadow-sm">PDF</button>
      </div>
    </div>

    <!-- TABLA DE ÓRDENES -->
    <div class="bg-white rounded-xl border shadow-sm overflow-hidden">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-800 text-white text-[10px] uppercase tracking-wider">
                <tr>
                    <th class="p-4">Fecha OC</th>
                    <th class="p-4">Consecutivo</th>
                    <th class="p-4">Responsable</th>
                    <th class="p-4">Estado</th>
                    <th class="p-4 text-right">Inversión</th>
                    <th class="p-4 text-center">Acción</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
                <tr v-for="order in orders" :key="order.id" class="hover:bg-gray-50 transition">
                    <td class="p-4 text-gray-500 font-mono text-xs">
                        {{ new Date(order.timestamp).toLocaleString() }}
                    </td>
                    <td class="p-4 font-black text-blue-600">{{ order.code }}</td>
                    <td class="p-4 text-gray-700 font-medium">{{ order.user_name }}</td>
                    <td class="p-4">
                        <span :class="['px-2 py-1 rounded-full text-[10px] font-bold uppercase', 
                            order.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700']">
                            {{ order.status }}
                        </span>
                    </td>
                    <td class="p-4 text-right font-black text-gray-900">{{ formatMoney(order.total_cost) }}</td>
                    <td class="p-4 text-center">
                        <button @click="viewDetail(order)" class="text-xs bg-gray-100 hover:bg-primary hover:text-white px-3 py-1 rounded-md transition font-bold">
                            👁️ Ver Detalle
                        </button>
                    </td>
                </tr>
                <tr v-if="orders.length === 0">
                    <td colspan="6" class="p-12 text-center text-gray-400 italic">No se encontraron órdenes en este rango de fechas.</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- MODAL DE DETALLE OC -->
    <div v-if="selectedOrder" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-2xl shadow-2xl max-w-xl w-full overflow-hidden animate-fade-in">
            <div class="p-6 bg-gray-800 text-white flex justify-between items-center">
                <div>
                    <h3 class="text-xl font-black">Orden de Entrada: {{ selectedOrder.code }}</h3>
                    <p class="text-xs opacity-70">{{ new Date(selectedOrder.timestamp).toLocaleString() }}</p>
                </div>
                <button @click="selectedOrder = null" class="text-2xl hover:text-red-400 transition">×</button>
            </div>
            
            <div class="p-6">
                <table class="w-full text-sm">
                    <thead class="border-b-2">
                        <tr class="text-left text-gray-500 font-bold uppercase text-[10px]">
                            <th class="py-2">Producto</th>
                            <th class="py-2 text-center">Cant.</th>
                            <th class="py-2 text-right">Costo Unit.</th>
                            <th class="py-2 text-right">Subtotal</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y">
                        <tr v-for="(d, i) in selectedOrder.details" :key="i" class="text-gray-700">
                            <td class="py-3 font-bold">{{ d.product }}</td>
                            <td class="py-3 text-center">{{ d.qty }}</td>
                            <td class="py-3 text-right font-mono">{{ formatMoney(d.cost) }}</td>
                            <td class="py-3 text-right font-black">{{ formatMoney(d.subtotal) }}</td>
                        </tr>
                    </tbody>
                    <tfoot class="border-t-2">
                        <tr class="text-lg font-black text-blue-700">
                            <td colspan="3" class="py-4 text-right uppercase">Total de la Orden:</td>
                            <td class="py-4 text-right">{{ formatMoney(selectedOrder.total_cost) }}</td>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div class="p-4 bg-gray-50 text-right">
                <button @click="selectedOrder = null" class="px-6 py-2 bg-gray-200 text-gray-700 rounded-lg font-bold hover:bg-gray-300 transition">Cerrar</button>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '../../api/axios';
import { formatMoney, getLocalISODate } from '../../utils/formatters'; // Importar nueva función

const filters = reactive({
    // ANTES: new Date().toISOString().split('T')[0] (Daba el error)
    // AHORA:
    start_date: getLocalISODate(), 
    end_date: getLocalISODate(),
    category_id: null,
    product_id: null
});

const orders = ref([]);
const selectedOrder = ref(null);


const loadData = async () => {
    try {
        const { data } = await api.get('/reports/purchase-orders-history', { params: filters });
        orders.value = data;
    } catch (e) {
        alert("Error al cargar historial de pedidos");
    }
};

const viewDetail = (order) => { selectedOrder.value = order; };

const exportData = async (format) => {
    try {
        const response = await api.get(`/reports/export/orders`, {
            params: { format, ...filters },
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Ordenes_Entrada_${filters.start_date}_${filters.end_date}.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    } catch (e) { alert("Error al exportar"); }
};

onMounted(loadData);
</script>