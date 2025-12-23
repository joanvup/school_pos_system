<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">Mi Familia</h1>

    <!-- Lista de Hijos -->
    <div v-if="loading" class="text-center">Cargando datos...</div>
    
    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div v-for="student in students" :key="student.id" class="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-100">
        <div class="p-6 bg-gradient-to-r from-blue-50 to-white">
            <h2 class="text-xl font-bold text-gray-800">{{ student.full_name }}</h2>
            <p class="text-sm text-gray-500">Curso: {{ student.grade }}</p>
        </div>
        
        <div class="p-6 border-t border-gray-100">
            <div class="flex justify-between items-end mb-4">
                <span class="text-gray-600 text-sm font-medium">Saldo en Tarjeta:</span>
                <span v-if="student.card" class="text-2xl font-bold text-green-600">
                    {{ formatMoney(student.card.balance) }}
                </span>
                <span v-else class="text-red-500 text-sm font-bold">Sin Tarjeta Activa</span>
            </div>
            <!-- Debajo del Saldo, dentro del card del estudiante -->
            <div v-if="student.card" class="flex justify-between items-center mt-2 p-2 bg-gray-50 rounded border border-gray-100">
                <div class="text-sm">
                    <span class="text-gray-500">Cupo Diario Máximo:</span>
                    <div class="font-bold text-gray-800">{{ formatMoney(student.card.daily_limit || 0) }}</div>
                </div>
                <button @click="openLimitModal(student)" class="text-blue-600 hover:bg-blue-100 p-2 rounded transition" title="Cambiar Cupo">
                    ✏️ Editar
                </button>
            </div>
            
            <div class="flex flex-col gap-2 mt-4" v-if="student.card">
            <!-- FILA SUPERIOR: ACCIONES PRINCIPALES -->
                <div class="flex gap-2">
                    <button @click="openRecharge(student)" class="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded font-bold transition text-sm shadow">
                        Recargar
                    </button>
                    <button @click="viewHistory(student)" class="flex-1 border border-gray-300 hover:bg-gray-50 text-gray-700 py-2 rounded font-medium transition text-sm">
                        Movimientos
                    </button>
                </div>

            <!-- FILA INFERIOR: ESTADO DE TARJETA -->
                <div class="flex items-center justify-between bg-gray-50 p-2 rounded border mt-2">
                    <div class="flex items-center gap-2">
                        <span class="w-3 h-3 rounded-full" :class="student.card.status === 'active' ? 'bg-green-500' : 'bg-red-500'"></span>
                        <span class="text-xs font-bold uppercase text-gray-600">
                            {{ student.card.status === 'active' ? 'Tarjeta Activa' : 'Tarjeta Bloqueada' }}
                        </span>
                    </div>
        
                    <button 
                        @click="toggleCardStatus(student)" 
                        class="text-xs px-3 py-1 rounded border transition font-bold"
                        :class="student.card.status === 'active' 
                            ? 'border-red-200 text-red-600 hover:bg-red-50' 
                            : 'border-green-200 text-green-600 hover:bg-green-50'"
                    >
                        {{ student.card.status === 'active' ? 'BLOQUEAR 🔒' : 'DESBLOQUEAR 🔓' }}
                    </button>
                </div>
            </div>
        </div>
      </div>
    </div>

    <!-- MODAL 1: PSE (Recarga) -->
    <div v-if="showRecharge" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 text-center">
            <h3 class="text-lg font-bold mb-4">Recargar Saldo</h3>
            <p class="mb-2">Estudiante: <b>{{ selectedStudent?.full_name }}</b></p>
            <div class="mb-4 text-left">
                <label class="text-sm font-bold text-gray-700">Monto</label>
                <input v-model.number="amount" type="number" step="5000" class="w-full border p-2 rounded mt-1">
            </div>
            <button @click="processRecharge" class="w-full bg-blue-600 text-white py-3 rounded font-bold">Pagar con PSE</button>
            <button @click="showRecharge = false" class="mt-4 text-sm text-gray-500 underline">Cancelar</button>
        </div>
    </div>

    <!-- MODAL 2: HISTORIAL DE MOVIMIENTOS (NUEVO) -->
    <div v-if="showHistoryModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
            <div class="flex justify-between items-center mb-4">
                <h3 class="text-lg font-bold">Movimientos: {{ selectedStudent?.full_name }}</h3>
                <button @click="showHistoryModal = false" class="text-gray-500 hover:text-gray-800 text-2xl">×</button>
            </div>
            
            <div class="max-h-[60vh] overflow-y-auto">
                <table class="w-full text-sm text-left">
                    <thead class="bg-gray-50 text-gray-500 sticky top-0">
                        <tr>
                            <th class="p-3">Fecha</th>
                            <th class="p-3">Tipo</th>
                            <th class="p-3">Descripción</th>
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
                <!-- BOTÓN CARGAR MÁS -->
                <div v-if="hasMoreHistory && history.length > 0" class="p-4 text-center border-t">
                    <button 
                        @click="fetchHistoryBatch" 
                        class="text-blue-600 font-bold hover:bg-blue-50 px-4 py-2 rounded transition text-sm"
                    >
                        ⬇ Cargar movimientos anteriores
                    </button>
                </div>
            </div>
            
            <div class="mt-4 text-right">
                <button @click="showHistoryModal = false" class="bg-gray-100 px-4 py-2 rounded text-gray-700 hover:bg-gray-200">Cerrar</button>
            </div>
        </div>
    </div>
    <!-- MODAL 3: CAMBIAR CUPO DIARIO -->
    <div v-if="showLimitModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-lg shadow-xl max-w-sm w-full p-6 text-center">
            <h3 class="text-lg font-bold mb-4">Límite de Gasto Diario</h3>
            <p class="mb-4 text-sm text-gray-600">
                Estudiante: <b>{{ selectedStudent?.full_name }}</b>
            </p>

            <div class="text-left mb-4">
                <label class="text-xs font-bold text-gray-500 uppercase">Nuevo Límite ($)</label>
                <input 
                    v-model.number="tempLimit" 
                    type="number" 
                    step="1000" 
                    min="0"
                    class="w-full border-2 border-blue-500 rounded p-2 text-lg font-bold outline-none"
                    autofocus
                >
                <p class="text-xs text-gray-400 mt-1">Coloca 0 para bloquear compras o un monto alto para liberar.</p>
            </div>

            <button @click="saveLimit" class="w-full bg-blue-600 text-white py-3 rounded font-bold hover:bg-blue-700">
                Guardar Cambio
            </button>
            <button @click="showLimitModal = false" class="mt-4 text-gray-500 underline text-sm">Cancelar</button>
        </div>
    </div>
    <!-- MODAL 4: PSE PAYMENT -->
    <PsePaymentModal 
        :is-open="isPseOpen" 
        :title="selectedTarget.name" 
        :card-uid="selectedTarget.uid"
        @close="isPseOpen = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';

// 1. IMPORTAR EL NUEVO COMPONENTE
import PsePaymentModal from '../components/PsePaymentModal.vue';

const students = ref([]);
const loading = ref(true);

// 2. VARIABLES PARA CONTROLAR EL MODAL
const isPseOpen = ref(false); // ¿Está abierto el modal?
const selectedTarget = ref({ name: '', uid: '' }); // Datos del hijo seleccionado

// 3. FUNCIÓN PARA ABRIR EL MODAL
const openRecharge = (student) => {
    // Guardamos los datos del hijo al que hicieron clic
    selectedTarget.value = { 
        name: student.full_name, 
        uid: student.card.uid 
    };
    // Abrimos el modal
    isPseOpen.value = true;
};

// Variables de Recarga
const showRecharge = ref(false);
const selectedStudent = ref(null);
const amount = ref(20000);

// Variables de Historial
const showHistoryModal = ref(false);
const history = ref([]);

const historySkip = ref(0);
const historyLimit = 20;
const hasMoreHistory = ref(true);

// Variable para controlar qué fila muestra detalles
const expandedRowId = ref(null);
const showLimitModal = ref(false);
const tempLimit = ref(0);

// Funciones
const openLimitModal = (student) => {
    selectedStudent.value = student;
    tempLimit.value = student.card.daily_limit || 0;
    showLimitModal.value = true;
};

const saveLimit = async () => {
    try {
        await api.put(`/cards/${selectedStudent.value.card.uid}`, {
            daily_limit: tempLimit.value
        });
        
        // Actualizar visualmente
        selectedStudent.value.card.daily_limit = tempLimit.value;
        alert("Cupo diario actualizado correctamente.");
        showLimitModal.value = false;
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

const loadFamily = async () => {
    loading.value = true;
    try {
        const { data } = await api.get('/students/me');
        students.value = data;
    } catch (error) { console.error(error); } 
    finally { loading.value = false; }
};

/* --- LOGICA RECARGA ---
const openRecharge = (student) => {
    selectedStudent.value = student;
    amount.value = 20000;
    showRecharge.value = true;
}; */

const processRecharge = async () => {
    if(!selectedStudent.value.card) return alert("Sin tarjeta");
    try {
        await api.post('/recharges/simulate-pse', {
            card_uid: selectedStudent.value.card.uid,
            amount: amount.value
        });
        alert("¡Recarga Exitosa!");
        showRecharge.value = false;
        loadFamily();
    } catch (error) { alert("Error: " + error.response?.data?.detail); }
};

// Abrir modal y cargar primeros 20
const viewHistory = async (student) => {
    if(!student.card) return alert("El estudiante no tiene tarjeta vinculada.");
    
    selectedStudent.value = student;
    history.value = []; // Limpiar lista visual
    historySkip.value = 0; // Reiniciar contador
    hasMoreHistory.value = true;
    showHistoryModal.value = true;

    await fetchHistoryBatch();
};

// Función auxiliar para llamar a la API
const fetchHistoryBatch = async () => {
    try {
        const { data } = await api.get(`/cards/${selectedStudent.value.card.uid}/history`, {
            params: {
                skip: historySkip.value,
                limit: historyLimit
            }
        });

        // Si llegaron menos datos del límite, significa que se acabaron
        if (data.length < historyLimit) {
            hasMoreHistory.value = false;
        }

        // AGREGAR al array existente (no reemplazar)
        history.value.push(...data);
        
        // Aumentar el salto para la próxima vez
        historySkip.value += historyLimit;
        
    } catch (error) {
        alert("Error cargando historial");
    }
};
const toggleCardStatus = async (student) => {
    const newStatus = student.card.status === 'active' ? 'blocked' : 'active';
    const action = newStatus === 'blocked' ? 'BLOQUEAR' : 'ACTIVAR';
    
    if(!confirm(`¿Estás seguro de que deseas ${action} la tarjeta de ${student.full_name}?`)) return;

    try {
        // Endpoint PUT /cards/{uid}
        await api.put(`/cards/${student.card.uid}`, {
            status: newStatus
        });
        
        // Actualizamos visualmente sin recargar todo
        student.card.status = newStatus;
        alert(`Tarjeta ${newStatus === 'active' ? 'activada' : 'bloqueada'} correctamente.`);
        
    } catch (error) {
        alert("Error cambiando estado: " + error.response?.data?.detail);
    }
};
onMounted(loadFamily);
</script>
