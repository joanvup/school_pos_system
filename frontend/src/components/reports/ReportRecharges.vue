<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg">
      <div class="md:col-span-2">
        <label class="block text-xs font-bold text-gray-500 uppercase">Rango de Fechas</label>
        <div class="flex gap-2">
            <input v-model="filters.start_date" type="date" class="flex-1 text-sm border p-2 rounded">
            <input v-model="filters.end_date" type="date" class="flex-1 text-sm border p-2 rounded">
        </div>
      </div>
      <div class="flex items-end gap-2">
        <button @click="loadData" class="bg-primary text-white px-4 py-2 rounded text-xs font-bold flex-1">Filtrar</button>
        <button @click="exportData('excel')" class="bg-green-600 text-white px-3 py-2 rounded text-xs">Excel</button>
        <button @click="exportData('pdf')" class="bg-red-600 text-white px-3 py-2 rounded text-xs">PDF</button>
      </div>
    </div>

    <!-- TABLA DE RESULTADOS -->
    <div class="overflow-x-auto">
        <table class="min-w-full text-sm text-left">
            <thead class="bg-blue-600 text-white">
                <tr>
                    <th class="p-3">Fecha / Hora</th>
                    <th class="p-3">Referencia PSE</th>
                    <th class="p-3">CUS (Banco)</th>
                    <th class="p-3">Tarjeta (UID)</th>
                    <th class="p-3">Beneficiario</th>
                    <th class="p-3 text-right">Monto Recargado</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                <tr v-for="item in data" :key="item.id" class="hover:bg-gray-50 border-b">
                    <td class="p-3 text-gray-500">{{ new Date(item.timestamp).toLocaleString() }}</td>
                    <td class="p-3 font-mono text-xs font-bold text-blue-600">{{ item.reference }}</td>
                    <td class="p-3 font-mono text-xs text-purple-600 font-bold">{{ item.cus }}</td> 
                    <td class="p-3 font-mono text-xs">{{ item.uid }}</td>
                    <td class="p-3 font-bold">{{ item.beneficiario }}</td>
                    <td class="p-3 text-right font-bold text-green-600">{{ formatMoney(item.amount) }}</td>
                </tr>
                <tr v-if="data.length === 0">
                    <td colspan="5" class="p-10 text-center text-gray-400">No hay recargas en este periodo</td>
                </tr>
            </tbody>
            <tfoot v-if="data.length > 0" class="bg-gray-100 font-bold text-lg">
                <tr>
                    <td colspan="4" class="p-4 text-right">INGRESOS TOTALES POR PSE:</td>
                    <td class="p-4 text-right text-green-700 font-mono">{{ formatMoney(totalRecharge) }}</td>
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

const totalRecharge = computed(() => {
    return data.value.reduce((sum, item) => sum + item.amount, 0);
});

const loadData = async () => {
    try {
        const { data: res } = await api.get('/reports/recharges-history', { params: filters });
        data.value = res;
    } catch (e) {
        alert("Error al cargar historial de recargas");
    }
};

const exportData = async (format) => {
    try {
        const response = await api.get('/reports/export/recharges', {
            params: { ...filters, format },
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Recargas_PSE_${filters.start_date}_${filters.end_date}.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    } catch (e) {
        alert("Error al exportar");
    }
};

onMounted(loadData);
</script>