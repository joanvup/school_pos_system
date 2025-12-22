<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg">
      <div>
        <label class="block text-xs font-bold text-gray-500 uppercase">Rango de Fechas</label>
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

    <!-- TABLA RESUMEN -->
    <div class="overflow-x-auto">
        <table class="w-full text-sm text-left">
            <thead class="bg-blue-50 text-blue-800">
                <tr>
                    <th class="p-3">Producto</th>
                    <th class="p-3">Categoría</th>
                    <th class="p-3 text-center">Cant. Vendida</th>
                    <th class="p-3 text-right">Total Recaudado</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="(item, idx) in data" :key="idx" class="border-b hover:bg-gray-50">
                    <td class="p-3 font-bold">{{ item.product }}</td>
                    <td class="p-3 text-gray-500">{{ item.category }}</td>
                    <td class="p-3 text-center">{{ item.qty }}</td>
                    <td class="p-3 text-right font-bold text-green-600">{{ formatMoney(item.total) }}</td>
                </tr>
                <tr v-if="data.length === 0" class="text-center text-gray-400">
                    <td colspan="4" class="p-10">No hay datos para mostrar</td>
                </tr>
            </tbody>
            <tfoot v-if="data.length > 0" class="bg-gray-100 font-bold">
                <tr>
                    <td colspan="2" class="p-3 text-right">GRAN TOTAL:</td>
                    <td class="p-3 text-center">{{ totalQty }}</td>
                    <td class="p-3 text-right text-blue-700">{{ formatMoney(totalRevenue) }}</td>
                </tr>
            </tfoot>
        </table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
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

const data = ref([]);
const categories = ref([]);

const totalQty = computed(() => data.value.reduce((s, i) => s + i.qty, 0));
const totalRevenue = computed(() => data.value.reduce((s, i) => s + i.total, 0));

const loadData = async () => {
    const { data: res } = await api.get('/reports/sales-by-product', { params: filters });
    data.value = res;
};

const exportData = async (format) => {
    try {
        const response = await api.get(`/reports/export/sales_product`, {
            params: { ...filters, format },
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Ventas_Producto.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    } catch (e) { alert("Error al exportar"); }
};

onMounted(async () => {
    const resCat = await api.get('/categories/');
    categories.value = resCat.data;
    loadData();
});
</script>