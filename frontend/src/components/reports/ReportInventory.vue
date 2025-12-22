<template>
  <div class="space-y-4">
    <!-- FILTROS -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4 bg-gray-50 p-4 rounded-lg">
      <div>
        <label class="block text-xs font-bold text-gray-500 uppercase">Categoría</label>
        <select v-model="filters.category_id" class="w-full text-xs border p-2 rounded bg-white">
            <option :value="null">Todas las categorías</option>
            <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
        </select>
      </div>
      <div>
        <label class="block text-xs font-bold text-gray-500 uppercase">Producto Específico</label>
        <select v-model="filters.product_id" class="w-full text-xs border p-2 rounded bg-white">
            <option :value="null">Todos los productos</option>
            <option v-for="p in allProducts" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </div>
      <div class="flex items-end gap-2">
        <button @click="loadData" class="bg-primary text-white px-4 py-2 rounded text-xs font-bold flex-1">Actualizar Vista</button>
        <button @click="exportData('excel')" class="bg-green-600 text-white px-3 py-2 rounded text-xs">Excel</button>
        <button @click="exportData('pdf')" class="bg-red-600 text-white px-3 py-2 rounded text-xs">PDF</button>
      </div>
    </div>

    <!-- TABLA DE RESULTADOS -->
    <div class="overflow-x-auto border rounded-lg">
        <table class="min-w-full text-sm text-left">
            <thead class="bg-gray-800 text-white">
                <tr>
                    <th class="p-3">Producto</th>
                    <th class="p-3">Categoría</th>
                    <th class="p-3 text-center">Stock</th>
                    <th class="p-3 text-right">Costo Unit.</th>
                    <th class="p-3 text-right">P. Venta</th>
                    <th class="p-3 text-right">Valoración (Costo)</th>
                </tr>
            </thead>
            <tbody class="divide-y">
                <tr v-for="(item, idx) in inventory" :key="idx" class="hover:bg-blue-50 transition">
                    <td class="p-3 font-bold">{{ item.name }}</td>
                    <td class="p-3">
                        <span class="text-xs bg-gray-100 px-2 py-1 rounded">{{ item.category }}</span>
                    </td>
                    <td class="p-3 text-center">
                        <span :class="item.stock <= 5 ? 'text-red-600 font-bold' : 'text-gray-700'">
                            {{ item.stock }}
                        </span>
                    </td>
                    <td class="p-3 text-right text-gray-500 font-mono">{{ formatMoney(item.cost) }}</td>
                    <td class="p-3 text-right text-gray-500 font-mono">{{ formatMoney(item.price) }}</td>
                    <td class="p-3 text-right font-bold text-blue-700 font-mono">{{ formatMoney(item.valuation) }}</td>
                </tr>
            </tbody>
            <tfoot class="bg-gray-100 font-bold text-lg">
                <tr>
                    <td colspan="5" class="p-4 text-right">VALOR TOTAL DEL INVENTARIO:</td>
                    <td class="p-4 text-right text-green-700 font-mono">{{ formatMoney(totalValuation) }}</td>
                </tr>
            </tfoot>
        </table>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue';
import api from '../../api/axios';
import { formatMoney } from '../../utils/formatters';

const inventory = ref([]);
const categories = ref([]);
const allProducts = ref([]);
const filters = reactive({
    category_id: null,
    product_id: null
});

const totalValuation = computed(() => {
    return inventory.value.reduce((sum, item) => sum + item.valuation, 0);
});

const loadData = async () => {
    try {
        const { data } = await api.get('/reports/inventory-status', { params: filters });
        inventory.value = data;
    } catch (e) {
        alert("Error al cargar inventario");
    }
};

const exportData = async (format) => {
    try {
        const response = await api.get('/reports/export/inventory', {
            params: { ...filters, format },
            responseType: 'blob'
        });
        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement('a');
        link.href = url;
        link.setAttribute('download', `Inventario_Actual_${new Date().toISOString().slice(0,10)}.${format === 'pdf' ? 'pdf' : 'xlsx'}`);
        document.body.appendChild(link);
        link.click();
        link.remove();
    } catch (e) {
        alert("Error al exportar inventario");
    }
};

onMounted(async () => {
    // Cargar selectores
    const [resCat, resProd] = await Promise.all([
        api.get('/categories/'),
        api.get('/products/')
    ]);
    categories.value = resCat.data;
    allProducts.value = resProd.data;
    loadData();
});
</script>