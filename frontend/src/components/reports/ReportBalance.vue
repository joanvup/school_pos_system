<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-50 p-4 rounded-lg border">
      <div class="md:col-span-2">
        <label class="block text-[10px] font-black text-gray-400 uppercase mb-1">Titular de Tarjeta (Con tarjeta activa)</label>
        <select v-model="selectedCardId" class="w-full text-sm border p-2 rounded-lg bg-white shadow-sm outline-none focus:ring-2 focus:ring-primary">
            <option :value="null">-- Seleccione Estudiante o Empleado --</option>
            <option v-for="c in cardholders" :key="c.card_id" :value="c.card_id">
                {{ c.display_name }} [{{ c.uid }}]
            </option>
        </select>
      </div>
      <div>
        <label class="block text-[10px] font-black text-gray-400 uppercase mb-1">Periodo</label>
        <div class="flex gap-1">
            <input v-model="filters.start_date" type="date" class="w-full text-xs border p-2 rounded">
            <input v-model="filters.end_date" type="date" class="w-full text-xs border p-2 rounded">
        </div>
      </div>
      <div class="flex items-end">
        <button @click="loadData" :disabled="!selectedCardId" class="w-full bg-primary text-white py-2 rounded-lg font-bold shadow-md disabled:opacity-50 transition">
            🔍 Ver Balance
        </button>
      </div>
    </div>

    <!-- VISTA DEL REPORTE -->
    <div v-if="reportData" class="space-y-6">
        <!-- CABECERA RESUMEN -->
        <div class="flex flex-col md:flex-row justify-between items-center bg-white p-6 rounded-xl border border-gray-100 shadow-sm gap-4">
            <div>
                <h2 class="text-xl font-black text-gray-800">{{ reportData.student_name }}</h2>
                <p class="text-sm text-gray-500 font-mono">Saldo disponible en sistema</p>
            </div>
            <div class="text-center md:text-right">
                <div class="text-3xl font-black text-blue-600">{{ formatMoney(reportData.current_balance) }}</div>
                <div class="flex gap-2 mt-2 justify-center md:justify-end">
                    <button @click="exportData('excel')" class="text-[10px] bg-green-100 text-green-700 px-2 py-1 rounded font-bold hover:bg-green-200">EXCEL</button>
                    <button @click="exportData('pdf')" class="text-[10px] bg-red-100 text-red-700 px-2 py-1 rounded font-bold hover:bg-red-200">PDF</button>
                </div>
            </div>
        </div>

        <!-- TABLA DE MOVIMIENTOS -->
        <div class="bg-white rounded-xl shadow-sm border overflow-hidden">
            <table class="w-full text-sm text-left">
                <thead class="bg-gray-50 border-b">
                    <tr class="text-[10px] text-gray-400 uppercase font-black">
                        <th class="p-4">Fecha / Hora</th>
                        <th class="p-4">Movimiento</th>
                        <th class="p-4 text-right">Valor</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-100">
                    <tr v-for="tx in reportData.transactions" :key="tx.id" class="hover:bg-blue-50/30 transition">
                        <td class="p-4 text-gray-500 whitespace-nowrap">
                            {{ new Date(tx.timestamp).toLocaleString() }}
                        </td>
                        <td class="p-4">
                            <div class="font-bold flex items-center gap-2">
                                <span v-if="tx.type === 'recharge'" class="text-green-600">➕ Recarga PSE</span>
                                <span v-else class="text-gray-800">➖ Consumo Cafetería</span>
                            </div>
                            <div class="text-[11px] text-gray-400 mt-1 italic">
                                {{ tx.description }}
                                <span v-if="tx.details.length > 0">
                                    ({{ tx.details.map(d => `{d.product} x${d.qty}`).join(', ') }})
                                </span>
                            </div>
                        </td>
                        <td class="p-4 text-right font-mono font-bold" :class="tx.amount > 0 ? 'text-green-600' : 'text-red-500'">
                            {{ tx.amount > 0 ? '+' : '' }}{{ formatMoney(tx.amount) }}
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <div v-else class="text-center py-24 bg-gray-50 rounded-2xl border border-dashed border-gray-200">
        <div class="text-4xl mb-2">🔎</div>
        <p class="text-gray-400 font-medium">Seleccione un usuario para auditar sus movimientos.</p>
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
const cardholders = ref([]);
const selectedCardId = ref(null);
const reportData = ref(null);

const loadCardholders = async () => {
    const { data } = await api.get('/reports/cardholders');
    cardholders.value = data;
};

const loadData = async () => {
    if (!selectedCardId.value) return;
    try {
        // Obtenemos el balance del "dueño" de esa tarjeta. 
        // Nota: Ajustaremos el endpoint para buscar por CARD ID directamente
        const { data } = await api.get(`/reports/student-balance/${selectedCardId.value}`, { params: filters });
        reportData.value = data;
    } catch (e) {
        alert("Error al obtener el balance");
    }
};

const exportData = async (format) => {
    if (!selectedCardId.value) return alert("Seleccione un usuario primero");

    try {
        const response = await api.get(`/reports/export/balance`, {
            params: { 
                format: format, 
                start_date: filters.start_date, 
                end_date: filters.end_date,
                user_id: selectedCardId.value // Este es el ID de la tarjeta que el backend recibirá
            },
            responseType: 'blob' // CRÍTICO para que el navegador entienda que es un archivo
        });

        // Crear nombre del archivo
        const nombreArchivo = reportData.value ? reportData.value.student_name.replace(/ /g, "_") : "Balance";
        const extension = format === 'pdf' ? 'pdf' : 'xlsx';
        
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Balance_${nombreArchivo}.${extension}`);
        document.body.appendChild(link);
        link.click();
        
        // Limpieza
        link.remove();
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error("Error exportando balance:", e);
        alert("No se pudo generar el archivo. Asegúrese de que haya datos en el rango seleccionado.");
    }
};

onMounted(loadCardholders);
</script>