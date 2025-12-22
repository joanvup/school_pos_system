<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">Entradas de Almacén (Pedidos)</h1>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        <!-- FORMULARIO DE NUEVA ORDEN (IZQUIERDA) -->
        <div class="lg:col-span-2 bg-white p-6 rounded-xl shadow">
            <h2 class="text-lg font-bold mb-4 text-blue-600">Nueva Orden de Entrada</h2>
            
            <!-- Buscador de Producto -->
            <div class="flex gap-2 mb-4">
                <select v-model="selectedProductId" class="flex-1 border p-2 rounded">
                    <option :value="null">Seleccione un producto...</option>
                    <option v-for="p in products" :key="p.id" :value="p.id">
                        {{ p.name }} (Stock: {{ p.stock }})
                    </option>
                </select>
            </div>

            <div class="grid grid-cols-3 gap-4 mb-4" v-if="selectedProductId">
                <div>
                    <label class="text-xs text-gray-500">Cantidad (+)</label>
                    <input v-model.number="tempQty" type="number" min="1" class="w-full border p-2 rounded">
                </div>
                <div>
                    <label class="text-xs text-gray-500">Costo Unitario</label>
                    <input v-model.number="tempCost" type="number" step="50" class="w-full border p-2 rounded">
                </div>
                <div class="flex items-end">
                    <button @click="addToOrder" class="w-full bg-green-100 text-green-700 font-bold py-2 rounded hover:bg-green-200">
                        Agregar Item
                    </button>
                </div>
            </div>

            <!-- Tabla de Items de la Orden Actual -->
            <table class="w-full text-sm border-t mt-4">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="p-2 text-left">Producto</th>
                        <th class="p-2 text-right">Cant.</th>
                        <th class="p-2 text-right">Costo</th>
                        <th class="p-2 text-right">Total</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="(item, index) in newOrderItems" :key="index" class="border-b">
                        <td class="p-2">{{ getProductName(item.product_id) }}</td>
                        <td class="p-2 text-right">{{ item.quantity }}</td>
                        <td class="p-2 text-right">${{ item.unit_cost }}</td>
                        <td class="p-2 text-right">${{ item.quantity * item.unit_cost }}</td>
                        <td class="p-2 text-right">
                            <button @click="removeFromOrder(index)" class="text-red-500">✕</button>
                        </td>
                    </tr>
                    <tr v-if="newOrderItems.length === 0">
                        <td colspan="5" class="p-4 text-center text-gray-400">Agregue productos a la orden</td>
                    </tr>
                </tbody>
            </table>

            <div class="mt-6 flex justify-end">
                <button 
                    @click="saveOrder" 
                    :disabled="newOrderItems.length === 0"
                    class="bg-primary text-white px-6 py-2 rounded shadow hover:bg-blue-700 disabled:opacity-50"
                >
                    Guardar Orden e Incrementar Stock
                </button>
            </div>
        </div>

        <!-- HISTORIAL DE ORDENES (DERECHA) -->
        <div class="bg-white p-6 rounded-xl shadow h-full overflow-y-auto max-h-[80vh]">
            <h2 class="text-lg font-bold mb-4 text-gray-700">Historial Reciente</h2>
            <div class="space-y-4">
                <div v-for="order in orderHistory" :key="order.id" class="border p-3 rounded hover:bg-gray-50 relative">
                    <div class="flex justify-between items-center mb-1">
                        <span class="font-bold text-gray-800">{{ order.code }}</span>
                        <span 
                            class="text-xs px-2 py-0.5 rounded uppercase font-bold"
                            :class="order.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
                        >
                            {{ order.status === 'completed' ? 'Aplicada' : 'Anulada' }}
                        </span>
                    </div>
                    <div class="text-xs text-gray-500">{{ new Date(order.timestamp).toLocaleString() }}</div>
                    <div class="text-sm font-bold mt-1">Total: ${{ order.total_cost.toLocaleString() }}</div>
                    
                    <!-- Botón Anular -->
                    <button 
                        v-if="order.status === 'completed'"
                        @click="cancelOrder(order)"
                        class="mt-2 text-xs text-red-500 underline hover:text-red-700 w-full text-right"
                    >
                        Anular Orden (Restar Stock)
                    </button>
                </div>
            </div>
        </div>

    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const products = ref([]);
const orderHistory = ref([]);
const newOrderItems = ref([]);

// Form inputs
const selectedProductId = ref(null);
const tempQty = ref(1);
const tempCost = ref(0);

const loadData = async () => {
    // Cargar productos
    const resProd = await api.get('/products/');
    products.value = resProd.data;
    
    // Cargar historial
    const resOrders = await api.get('/purchases/');
    orderHistory.value = resOrders.data;
};

const getProductName = (id) => {
    return products.value.find(p => p.id === id)?.name || 'Unknown';
};

const addToOrder = () => {
    if (!selectedProductId.value || tempQty.value <= 0) return;
    
    // Buscar producto para obtener costo sugerido si no puso uno
    const prod = products.value.find(p => p.id === selectedProductId.value);
    
    newOrderItems.value.push({
        product_id: selectedProductId.value,
        quantity: tempQty.value,
        unit_cost: tempCost.value > 0 ? tempCost.value : prod.cost
    });

    // Reset inputs
    selectedProductId.value = null;
    tempQty.value = 1;
    tempCost.value = 0;
};

const removeFromOrder = (index) => {
    newOrderItems.value.splice(index, 1);
};

const saveOrder = async () => {
    if(!confirm("¿Confirmar entrada de mercancía? El stock aumentará inmediatamente.")) return;
    
    try {
        await api.post('/purchases/', { items: newOrderItems.value });
        alert("Orden guardada exitosamente");
        newOrderItems.value = [];
        loadData(); // Refrescar todo
    } catch (error) {
        alert("Error: " + error.response?.data?.detail);
    }
};

const cancelOrder = async (order) => {
    if(!confirm(`¿Desea anular la orden ${order.code}? Se intentará descontar el stock si está disponible.`)) return;

    try {
        await api.delete(`/purchases/${order.id}`);
        alert("Orden anulada correctamente");
        loadData();
    } catch (error) {
        alert("No se pudo anular: " + error.response?.data?.detail);
    }
};

onMounted(loadData);
</script>