<template>
  <div class="max-w-4xl mx-auto space-y-8 pb-20">
    <div class="text-center space-y-2">
        <h1 class="text-3xl font-black text-gray-900 tracking-tighter uppercase italic">Confrontación de Saldos</h1>
        <p class="text-gray-500 font-medium">Auditoría profunda de movimientos y saldos por usuario</p>
    </div>

    <!-- SELECTOR DE USUARIO -->
    <div class="bg-white p-8 rounded-[40px] shadow-sm border-4 border-gray-50">
        <div class="flex flex-col md:flex-row gap-4 items-end">
            <div class="flex-1">
                <label class="block text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2 ml-2">Seleccionar Portador</label>
                <select v-model="selectedCardId" class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl font-bold outline-none focus:border-primary transition-all">
                    <option :value="null">-- Buscar Estudiante o Empleado --</option>
                    <option v-for="c in cardholders" :key="c.card_id" :value="c.card_id">
                        {{ c.display_name }} (UID: {{ c.uid }})
                    </option>
                </select>
            </div>
            <button 
                @click="startAudit" 
                :disabled="!selectedCardId || auditing"
                class="bg-gray-900 text-white px-8 py-4 rounded-2xl font-black uppercase tracking-widest shadow-xl hover:bg-black disabled:opacity-30 transition-all flex items-center gap-3"
            >
                <span v-if="!auditing">⚙️ Iniciar Auditoría</span>
                <span v-else>Procesando...</span>
            </button>
        </div>
    </div>

    <!-- BARRA DE PROGRESO Y PASOS -->
    <div v-if="auditing" class="bg-white p-10 rounded-[40px] shadow-2xl border-4 border-blue-50 animate-pulse">
        <div class="flex justify-between mb-4 font-black text-primary uppercase text-xs tracking-tighter">
            <span>{{ auditStatus }}</span>
            <span>{{ progress }}%</span>
        </div>
        <div class="w-full bg-gray-100 h-4 rounded-full overflow-hidden">
            <div class="bg-primary h-full transition-all duration-500" :style="{ width: progress + '%' }"></div>
        </div>
    </div>

    <!-- RESULTADO DE LA CONFRONTACIÓN -->
    <div v-if="auditResult && !auditing" class="bg-white rounded-[40px] shadow-2xl overflow-hidden border-4 border-gray-50 animate-scale-in">
        <div class="p-8 bg-gray-900 text-white flex justify-between items-center">
            <div>
                <h3 class="text-xl font-black uppercase italic">Resultado del Análisis</h3>
                <p class="text-xs text-gray-400 font-bold opacity-70">Referencia: {{ selectedCard?.display_name }}</p>
            </div>
            <div class="text-right">
                <span :class="auditResult.discrepancy === 0 ? 'bg-green-500' : 'bg-red-500'" class="px-4 py-1 rounded-full text-[10px] font-black uppercase tracking-widest">
                    {{ auditResult.discrepancy === 0 ? 'Sistema Íntegro' : 'Discrepancia Detectada' }}
                </span>
            </div>
        </div>

        <div class="p-10 grid grid-cols-1 md:grid-cols-2 gap-12">
            <!-- Saldos -->
            <div class="space-y-6">
                <div class="flex justify-between items-center border-b pb-4">
                    <span class="text-gray-500 font-bold uppercase text-[10px]">Saldo en Base de Datos:</span>
                    <span class="text-2xl font-black text-gray-800">{{ formatMoney(auditResult.stored_balance) }}</span>
                </div>
                <div class="flex justify-between items-center border-b pb-4">
                    <span class="text-gray-500 font-bold uppercase text-[10px]">Saldo Real Recalculado:</span>
                    <span class="text-2xl font-black text-blue-600">{{ formatMoney(auditResult.calculated_balance) }}</span>
                </div>
                <div class="flex justify-between items-center p-4 rounded-2xl" :class="auditResult.discrepancy === 0 ? 'bg-green-50' : 'bg-red-50'">
                    <span class="font-black uppercase text-[10px]" :class="auditResult.discrepancy === 0 ? 'text-green-600' : 'text-red-600'">Diferencia:</span>
                    <span class="text-2xl font-black" :class="auditResult.discrepancy === 0 ? 'text-green-600' : 'text-red-600'">
                        {{ formatMoney(auditResult.discrepancy) }}
                    </span>
                </div>
            </div>

            <!-- Resumen Transaccional -->
            <div class="bg-gray-50 p-6 rounded-3xl space-y-4">
                <h4 class="text-xs font-black text-gray-400 uppercase tracking-widest">Métricas Analizadas</h4>
                <div class="flex justify-between">
                    <span class="text-sm font-medium text-gray-600">Recargas Totales:</span>
                    <span class="font-black text-gray-800">{{ auditResult.recharges_count }}</span>
                </div>
                <div class="flex justify-between">
                    <span class="text-sm font-medium text-gray-600">Consumos Totales:</span>
                    <span class="font-black text-gray-800">{{ auditResult.purchases_count }}</span>
                </div>
                <p class="text-[10px] text-gray-400 italic pt-4">
                    * El saldo real se calcula sumando algebraicamente cada movimiento individual de recarga (aprobado) y compra (no reversada).
                </p>
            </div>
        </div>

        <!-- ACCIONES DE CORRECCIÓN -->
        <div class="p-8 bg-gray-50 border-t flex flex-col md:flex-row gap-4">
            <button 
                v-if="auditResult.discrepancy !== 0" 
                @click="applyFix"
                class="flex-1 bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-tighter shadow-lg hover:bg-blue-700 transition-all active:scale-95"
            >
                ✅ Corregir Saldo en el Sistema
            </button>
            <button @click="auditResult = null" class="flex-1 bg-white border border-gray-200 text-gray-400 py-4 rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-gray-100 transition-all">
                Cerrar Análisis
            </button>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';

const cardholders = ref([]);
const selectedCardId = ref(null);
const auditResult = ref(null);
const auditing = ref(false);
const progress = ref(0);
const auditStatus = ref('');

const selectedCard = computed(() => cardholders.value.find(c => c.card_id === selectedCardId.value));

const loadCardholders = async () => {
    const { data } = await api.get('/reports/cardholders');
    cardholders.value = data;
};

const startAudit = async () => {
    auditing.value = true;
    auditResult.value = null;
    progress.value = 0;

    // --- SIMULACIÓN DE PASOS DE AUDITORÍA PARA LA BARRA DE PROGRESO ---
    const steps = [
        { p: 20, s: 'Iniciando conexión con base de datos...' },
        { p: 40, s: 'Verificando integridad de transacciones...' },
        { p: 60, s: 'Analizando historial de recargas PSE...' },
        { p: 80, s: 'Calculando consumos y reversiones...' },
        { p: 100, s: 'Finalizando confrontación...' }
    ];

    for (let step of steps) {
        auditStatus.value = step.s;
        progress.value = step.p;
        await new Promise(r => setTimeout(r, 400)); // Delay visual
    }

    try {
        const { data } = await api.get(`/audit/reconcile/${selectedCardId.value}`);
        auditResult.value = data;
    } catch (e) {
        alert("Error en la auditoría");
    } finally {
        auditing.value = false;
    }
};

const applyFix = async () => {
    if (!confirm(`Se va a ajustar el saldo de ${formatMoney(auditResult.value.stored_balance)} a ${formatMoney(auditResult.value.calculated_balance)}. ¿Desea continuar?`)) return;

    try {
        await api.post(`/audit/fix-balance/${selectedCardId.value}`, {
            new_balance: auditResult.value.calculated_balance
        });
        alert("✅ Saldo sincronizado correctamente.");
        auditResult.value = null;
        selectedCardId.value = null;
    } catch (e) {
        alert("Error al aplicar la corrección");
    }
};

onMounted(loadCardholders);
</script>

<style scoped>
.animate-scale-in { animation: scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.95) translateY(10px); } to { opacity: 1; transform: scale(1) translateY(0); } }
</style>