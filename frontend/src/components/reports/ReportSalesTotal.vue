<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg">
      <div>
        <label class="block text-xs font-bold text-gray-500 uppercase">Desde / Hasta</label>
        <div class="flex gap-2">
            <input v-model="filters.start_date" type="date" class="w-full text-xs border p-2 rounded">
            <input v-model="filters.end_date" type="date" class="w-full text-xs border p-2 rounded">
        </div>
      </div>
      <div>
        <label class="block text-xs font-bold text-gray-500 uppercase">Categoría</label>
        <select v-model="filters.category_id" class="w-full text-xs border p-2 rounded">
            <option :value="null">Todas</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div class="flex items-end gap-2">
        <button @click="loadData" class="bg-primary text-white px-4 py-2 rounded text-xs font-bold flex-1">Filtrar</button>
        <button @click="exportData('excel')" class="bg-green-600 text-white px-3 py-2 rounded text-xs">Excel</button>
        <button @click="exportData('pdf')" class="bg-red-600 text-white px-3 py-2 rounded text-xs">PDF</button>
      </div>
    </div>

    <!-- TABLA -->
    <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
            <thead class="bg-gray-100 text-gray-600">
                <tr>
                    <th class="p-3">Fecha</th>
                    <th class="p-3">Comprador</th>
                    <th class="p-3">Monto</th>
                    <th class="p-3">Acción</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="item in data" :key="item.id" class="border-b hover:bg-gray-50">
                    <td class="p-3">{{ new Date(item.timestamp).toLocaleString() }}</td>
                    <td class="p-3 font-bold">{{ item.comprador }}</td>
                    <td class="p-3 text-blue-600 font-bold">{{ formatMoney(item.amount) }}</td>
                    <td class="p-3">
                        <button @click="viewDetail(item)" class="text-xs text-primary underline">Ver Detalle</button>
                    </td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- MODAL DETALLE -->
    <div v-if="selectedItem" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white p-6 rounded-xl max-w-md w-full">
            <h3 class="font-bold border-b pb-2 mb-4 text-lg">Detalle de la Venta</h3>
            <div class="space-y-2 mb-4">
                <div v-for="d in selectedItem.details" :key="d.id" class="flex justify-between text-sm">
                    <span>{{ d.product_name }} x{{ d.quantity }}</span>
                    <span class="font-mono font-bold">{{ formatMoney(d.subtotal) }}</span>
                </div>
            </div>
            <div class="border-t pt-2 flex justify-between font-bold text-lg">
                <span>TOTAL:</span>
                <span class="text-green-600">{{ formatMoney(selectedItem.amount) }}</span>
            </div>
            <button @click="selectedItem = null" class="w-full mt-6 bg-gray-100 py-2 rounded">Cerrar</button>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import api from '../../api/axios';
import { formatMoney, getLocalISODate } from '../../utils/formatters';


const data = ref([]);
const categories = ref([]);
const selectedItem = ref(null);
const filters = reactive({
    // ANTES: new Date().toISOString().split('T')[0] (Daba el error)
    // AHORA:
    start_date: getLocalISODate(), 
    end_date: getLocalISODate(),
    category_id: null,
    product_id: null
});

const loadData = async () => {
    const { data: res } = await api.get('/reports/sales-total', { params: filters });
    data.value = res.items;
};

const exportData = async (format) => {
    try {
        // Usamos Axios (api) que ya tiene el token inyectado
        const response = await api.get(`/reports/export/sales`, {
            params: {
                format: format,
                start_date: filters.start_date,
                end_date: filters.end_date,
                category_id: filters.category_id
            },
            responseType: 'blob' // Indispensable para archivos
        });

        // Crear un link virtual para descargar el archivo recibido
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Ventas_Totales.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (error) {
        console.error(error);
        if (error.response?.status === 404) {
            alert("No se encontraron datos para este reporte en las fechas seleccionadas.");
        } else {
            alert("Error al generar el archivo.");
        }
    }
};

const viewDetail = (item) => { selectedItem.value = item; };

onMounted(async () => {
    const resCat = await api.get('/categories/');
    categories.value = resCat.data;
    loadData();
});
</script>