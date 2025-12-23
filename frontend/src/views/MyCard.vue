<template>
  <div class="max-w-4xl mx-auto space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">Gestión de Mi Tarjeta</h1>

    <!-- TARJETA VISUAL -->
    <div v-if="loading" class="text-center p-10">Cargando información...</div>

    <div v-else-if="!myCard" class="bg-yellow-50 p-6 rounded-xl border border-yellow-200 text-center">
        <div class="text-4xl mb-2">⚠️</div>
        <h2 class="text-lg font-bold text-yellow-800">No tienes tarjeta asignada</h2>
        <p class="text-yellow-700">Por favor contacta al administrador para que te entregue tu tarjeta física.</p>
    </div>

    <div v-else class="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100">
        <!-- CABECERA TARJETA -->
        <div class="p-8 bg-gradient-to-r from-gray-800 to-gray-600 text-white">
            <div class="flex justify-between items-start">
                <div>
                    <h2 class="text-2xl font-bold">{{ authStore.user?.full_name }}</h2>
                    <p class="text-gray-300 opacity-80">Empleado / Staff</p>
                </div>
                <div class="text-right">
                    <div class="text-xs uppercase opacity-75 tracking-widest">Saldo Disponible</div>
                    <div class="text-4xl font-bold mt-1">{{ formatMoney(myCard.balance) }}</div>
                </div>
            </div>
            <!-- Dentro del div con gradiente (la tarjeta visual) -->
            <div class="mt-4 flex justify-between items-center bg-white/10 p-2 rounded">
                <div class="text-sm">
                    <span class="opacity-75 text-xs uppercase">Cupo Diario:</span>
                    <span class="font-bold ml-2">${{ (myCard.daily_limit || 0).toLocaleString() }}</span>
                </div>
                <button @click="openLimitModal" class="text-xs bg-white text-gray-800 px-2 py-1 rounded font-bold hover:bg-gray-200">
                    Cambiar
                </button>
            </div>
            <div class="mt-6 flex justify-between items-end">
                <div class="font-mono bg-white/20 px-3 py-1 rounded text-sm tracking-widest">
                    {{ myCard.uid }}
                </div>
                <div class="flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full" :class="myCard.status === 'active' ? 'bg-green-400' : 'bg-red-500'"></span>
                    <span class="text-sm uppercase font-bold">{{ myCard.status === 'active' ? 'Activa' : 'Bloqueada' }}</span>
                </div>
            </div>
            <div class="mt-4 pt-4 border-t border-white/20 flex justify-between items-center">
                <div class="flex items-center gap-2">
                    <div class="w-3 h-3 rounded-full" :class="myCard.status === 'active' ? 'bg-green-400' : 'bg-red-500'"></div>
                    <span class="text-sm font-bold">{{ myCard.status === 'active' ? 'OPERATIVA' : 'BLOQUEADA' }}</span>
                </div>

                <button 
                    @click="toggleMyCardStatus"
                    class="text-xs font-bold px-3 py-1 rounded transition bg-white/20 hover:bg-white/30 text-white"
                >
                    {{ myCard.status === 'active' ? 'BLOQUEAR' : 'DESBLOQUEAR' }}
                </button>
            </div>
        </div>
        
        <!-- ACCIONES -->
        <div class="p-6 flex gap-4">
            <button 
                @click="openRecharge"
                class="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-3 rounded-lg font-bold shadow transition flex items-center justify-center gap-2"
            >
                <span>💳</span> Recargar con PSE
            </button>
            <button 
                @click="openHistory"
                class="flex-1 bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 py-3 rounded-lg font-bold transition flex items-center justify-center gap-2"
            >
                <span>📄</span> Ver Movimientos
            </button>
        </div>
    </div>

    <!-- MODAL RECARGA -->
    <div v-if="showRechargeModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 text-center">
            <h3 class="text-lg font-bold mb-4">Recargar Mi Saldo</h3>
            <div class="mb-4 text-left">
                <label class="text-sm font-bold text-gray-700">Monto a Recargar</label>
                <input v-model.number="amount" type="number" step="5000" min="5000" class="w-full border p-2 rounded mt-1 font-bold text-lg">
            </div>
            <button @click="processRecharge" class="w-full bg-blue-600 text-white py-3 rounded font-bold hover:bg-blue-700">
                Pagar vía PSE
            </button>
            <button @click="showRechargeModal = false" class="mt-4 text-sm text-gray-500 underline">Cancelar</button>
        </div>
    </div>

    <!-- MODAL HISTORIAL (REUTILIZADO LÓGICA DE MYFAMILY) -->
    <div v-if="showHistoryModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6 flex flex-col max-h-[80vh]">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">Mis Movimientos</h3>
                <button @click="showHistoryModal = false" class="text-gray-500 text-2xl">×</button>
            </div>
            
            <div class="overflow-y-auto flex-1">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-500 sticky top-0">
                        <tr>
                            <th class="p-3">Fecha</th>
                            <th class="p-3">Tipo</th>
                            <th class="p-3">Detalle</th>
                            <th class="p-3 text-right">Monto</th>
                        </tr>
                    </thead>
                    <tbody class="divide-y">
                        <template v-for="tx in history" :key="tx.id">
                            <!-- FILA PRINCIPAL -->
                            <tr class="hover:bg-gray-50 cursor-pointer" @click="toggleDetails(tx.id)">
                                <td class="p-3">
                                    <div class="font-medium">{{ new Date(tx.timestamp).toLocaleDateString() }}</div>
                                    <div class="text-xs text-gray-400">{{ new Date(tx.timestamp).toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'}) }}</div>
                                </td>
                                <td class="p-3">
                                    <span v-if="tx.type === 'recharge'" class="text-green-600 font-bold bg-green-50 px-2 py-1 rounded text-xs">RECARGA</span>
                                    <span v-else class="text-blue-600 font-bold bg-blue-50 px-2 py-1 rounded text-xs">COMPRA</span>
                                </td>
                                <td class="p-3 text-gray-600">
                                    {{ tx.description }}
                                    <!-- Icono indicador de expansión si es compra -->
                                    <span v-if="tx.type === 'purchase'" class="text-xs text-gray-400 ml-2">
                                        {{ expandedRowId === tx.id ? '▼' : '▶' }}
                                    </span>
                                </td>
                                <td class="p-3 text-right font-mono font-bold" :class="tx.amount > 0 ? 'text-green-600' : 'text-red-600'">
                                    {{ tx.amount > 0 ? '+' : '' }}{{ formatMoney(tx.amount) }}
                                </td>
                            </tr>

                            <!-- FILA DE DETALLES (SOLO SI ESTÁ EXPANDIDA Y ES COMPRA) -->
                            <tr v-if="expandedRowId === tx.id && tx.type === 'purchase'" class="bg-gray-50 border-b-2 border-gray-100">
                                <td colspan="4" class="p-4 pl-12">
                                    <div class="text-xs font-bold text-gray-500 mb-2 uppercase tracking-wider">Detalle de Consumo:</div>
                                    
                                    <table class="w-full text-sm">
                                        <tr v-for="(item, idx) in tx.details" :key="idx" class="border-b border-gray-200 last:border-0">
                                            <td class="py-1 w-2/3">{{ item.product_name }}</td>
                                            <td class="py-1 text-center text-gray-500">x{{ item.quantity }}</td>
                                            <td class="py-1 text-right font-mono">{{ formatMoney(item.subtotal) }}</td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </template>

                        <tr v-if="history.length === 0">
                            <td colspan="4" class="p-6 text-center text-gray-400">Sin movimientos</td>
                        </tr>
                    </tbody>
                </table>
                
                <div v-if="hasMore" class="p-3 text-center border-t">
                    <button @click="loadHistory" class="text-blue-600 font-bold hover:underline">⬇ Ver más antiguos</button>
                </div>
            </div>
        </div>
    </div>
    <!-- MODAL CAMBIAR CUPO -->
    <div v-if="showLimitModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 text-center">
            <h3 class="text-lg font-bold mb-4">Mi Límite Diario</h3>
            <input 
                v-model.number="tempLimit" 
                type="number" 
                class="w-full border-2 border-blue-500 rounded p-2 text-lg font-bold mb-4"
            >
            <button @click="saveLimit" class="w-full bg-blue-600 text-white py-2 rounded font-bold">Guardar</button>
            <button @click="showLimitModal = false" class="mt-4 text-gray-500 underline text-sm">Cancelar</button>
        </div>
    </div>
    <!-- MODAL PSE PAYMENT -->
    <PsePaymentModal 
        v-if="myCard"
        :is-open="isPseOpen" 
        :title="authStore.user?.full_name" 
        :card-uid="myCard.uid"
        :current-balance="myCard.balance" 
        @close="isPseOpen = false"
    />

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';
import { useAuthStore } from '../stores/auth';
import { formatMoney } from '../utils/formatters';

// 1. IMPORTAR
import PsePaymentModal from '../components/PsePaymentModal.vue';

const isPseOpen = ref(false); // ¿Está abierto el modal?

// 2. FUNCIÓN SIMPLIFICADA
const openRecharge = () => {
    isPseOpen.value = true;
    
};

const authStore = useAuthStore();
const myCard = ref(null);
const loading = ref(true);

// Recarga
const showRechargeModal = ref(false);
const amount = ref(50000);

// Historial
const showHistoryModal = ref(false);
const history = ref([]);
const skip = ref(0);
const limit = 20;
const hasMore = ref(true);
// Variable para controlar qué fila muestra detalles
const expandedRowId = ref(null);
// Variables
const showLimitModal = ref(false);
const tempLimit = ref(0);

// Funciones
const openLimitModal = () => {
    tempLimit.value = myCard.value.daily_limit || 0;
    showLimitModal.value = true;
};

const saveLimit = async () => {
    try {
        await api.put(`/cards/${myCard.value.uid}`, {
            daily_limit: tempLimit.value
        });
        myCard.value.daily_limit = tempLimit.value;
        showLimitModal.value = false;
        alert("Tu cupo diario ha sido actualizado.");
    } catch (error) {
        alert("Error: " + error.response?.data?.detail);
    }
};
const toggleDetails = (txId) => {
    if (expandedRowId.value === txId) {
        expandedRowId.value = null; // Cerrar si ya estaba abierto
    } else {
        expandedRowId.value = txId; // Abrir
    }
};

const loadCard = async () => {
    loading.value = true;
    try {
        // Obtenemos los datos del usuario actual, que ya incluye 'card' si hicimos el cambio anterior
        // Ojo: Si el UserResponse backend trae 'card', lo usamos directo.
        const { data } = await api.get('/users/me');
        myCard.value = data.card;
    } catch (e) {
        console.error(e);
    } finally {
        loading.value = false;
    }
};

/*const openRecharge = () => {
    amount.value = 50000;
    showRechargeModal.value = true;
}; */

const processRecharge = async () => {
    try {
        await api.post('/recharges/simulate-pse', {
            card_uid: myCard.value.uid,
            amount: amount.value
        });
        alert("¡Recarga exitosa!");
        showRechargeModal.value = false;
        loadCard(); // Actualizar saldo visual
    } catch (error) {
        alert("Error: " + error.response?.data?.detail);
    }
};

const openHistory = () => {
    history.value = [];
    skip.value = 0;
    hasMore.value = true;
    showHistoryModal.value = true;
    loadHistory();
};

const loadHistory = async () => {
    try {
        const { data } = await api.get(`/cards/${myCard.value.uid}/history`, {
            params: { skip: skip.value, limit: limit }
        });
        
        if(data.length < limit) hasMore.value = false;
        history.value.push(...data);
        skip.value += limit;
    } catch (e) { alert("Error cargando historial"); }
};

const toggleMyCardStatus = async () => {
    const newStatus = myCard.value.status === 'active' ? 'blocked' : 'active';
    
    if(!confirm(`¿Deseas ${newStatus === 'blocked' ? 'BLOQUEAR' : 'ACTIVAR'} tu tarjeta?`)) return;

    try {
        await api.put(`/cards/${myCard.value.uid}`, { status: newStatus });
        myCard.value.status = newStatus; // Actualizar local
    } catch (error) {
        alert("Error: " + error.response?.data?.detail);
    }
};

onMounted(loadCard);
</script>