<template>
  <div class="bg-blue-50 border-l-4 border-blue-400 p-4 mb-6">
    <div class="flex">
        <div class="ml-3">
            <p class="text-sm text-blue-700">
                <span class="font-bold">Nota:</span> Use esta pantalla para cargar el inventario inicial o corregir descuadres físicos. 
                Para compras a proveedores, use la pestaña <span class="font-bold">"Entradas / Pedidos"</span>.
            </p>
        </div>
    </div>
  </div>
  <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
    
    <!-- FORMULARIO DE AJUSTE (IZQUIERDA) -->
    <div class="lg:col-span-2 bg-white p-6 rounded-2xl shadow-sm border border-orange-100">
      <h2 class="text-lg font-black text-orange-600 uppercase mb-4 italic">🔧 Nuevo Ajuste Manual</h2>
      
      <div class="space-y-4">
        <div>
          <label class="text-xs font-bold text-gray-400 uppercase">Motivo del Ajuste</label>
          <input v-model="reason" type="text" placeholder="Ej: Rotura de empaque, error en conteo, regalo..." 
                 class="w-full border-2 border-gray-100 p-3 rounded-xl outline-none focus:border-orange-400">
        </div>

        <div class="flex gap-2">
          <select v-model="selectedId" class="flex-1 border-2 border-gray-100 p-3 rounded-xl bg-gray-50">
            <option :value="null">Seleccionar producto para ajustar...</option>
            <option v-for="p in products" :key="p.id" :value="p.id">{{ p.name }} (Actual: {{ p.stock }})</option>
          </select>
          <input v-model.number="tempQty" type="number" placeholder="Cant (+/-)" class="w-24 border-2 border-gray-100 p-3 rounded-xl text-center font-bold">
          <button @click="addItem" class="bg-orange-500 text-white px-6 rounded-xl font-bold hover:bg-orange-600 transition">Añadir</button>
        </div>

        <table class="w-full text-sm mt-6">
          <thead class="bg-gray-50 text-gray-500 font-bold uppercase text-[10px]">
            <tr>
              <th class="p-3 text-left">Producto</th>
              <th class="p-3 text-center">Ajuste</th>
              <th class="p-3 text-right">Acción</th>
            </tr>
          </thead>
          <tbody class="divide-y">
            <tr v-for="(item, idx) in adjustmentItems" :key="idx">
              <td class="p-3 font-bold">{{ getProductName(item.product_id) }}</td>
              <td class="p-3 text-center">
                <span :class="item.quantity > 0 ? 'text-green-600' : 'text-red-600'" class="font-black px-2 py-1 bg-gray-100 rounded">
                  {{ item.quantity > 0 ? '+' : '' }}{{ item.quantity }}
                </span>
              </td>
              <td class="p-3 text-right">
                <button @click="adjustmentItems.splice(idx, 1)" class="text-red-400 hover:text-red-600">✕</button>
              </td>
            </tr>
          </tbody>
        </table>

        <button 
          @click="saveAdjustment" :disabled="adjustmentItems.length === 0 || !reason"
          class="w-full mt-6 bg-gray-900 text-white py-4 rounded-2xl font-black shadow-lg disabled:opacity-30 transition-all active:scale-95"
        >
          APLICAR AJUSTE AL INVENTARIO
        </button>
      </div>
    </div>

    <!-- HISTORIAL (DERECHA) -->
    <div class="bg-gray-50 p-6 rounded-2xl border border-gray-200 h-full max-h-[70vh] overflow-y-auto">
      <h3 class="text-xs font-black text-gray-400 uppercase mb-4">Ajustes Recientes</h3>
      <div v-for="adj in history" :key="adj.id" class="bg-white p-4 rounded-xl shadow-sm mb-3 border border-gray-100">
        <div class="flex justify-between text-[10px] font-black uppercase text-blue-600 mb-1">
          <span>{{ adj.code }}</span>
          <span class="text-gray-400">{{ new Date(adj.timestamp).toLocaleDateString() }}</span>
        </div>
        <p class="text-xs text-gray-700 font-medium italic mb-2">"{{ adj.reason }}"</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const products = ref([]);
const history = ref([]);
const adjustmentItems = ref([]);
const reason = ref('');
const selectedId = ref(null);
const tempQty = ref(1);

const loadData = async () => {
  // Cargar productos por separado para que sea más seguro
  try {
    const resP = await api.get('/products/');
    products.value = resP.data;
    console.log("Productos para ajuste cargados:", products.value.length);
  } catch (e) {
    console.error("Error cargando productos en ajustes:", e);
    alert("No se pudieron cargar los productos.");
  }

  // Cargar historial por separado (solo si eres admin)
  try {
    const resH = await api.get('/stock-adjustments/');
    history.value = resH.data;
  } catch (e) {
    console.warn("No se pudo cargar el historial de ajustes (posible falta de permisos).");
  }
};

const getProductName = (id) => products.value.find(p => p.id === id)?.name;

const addItem = () => {
  if (!selectedId.value || tempQty.value === 0) return;
  adjustmentItems.value.push({ product_id: selectedId.value, quantity: tempQty.value });
  selectedId.value = null; tempQty.value = 1;
};

const saveAdjustment = async () => {
  if(!confirm("Esta acción modificará el stock real. ¿Continuar?")) return;
  try {
    await api.post('/stock-adjustments/', { reason: reason.value, items: adjustmentItems.value });
    alert("Inventario ajustado correctamente");
    adjustmentItems.value = []; reason.value = '';
    loadData();
  } catch (e) { alert(e.response?.data?.detail); }
};

onMounted(loadData);
</script>