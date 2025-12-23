<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-6">
    <div class="bg-white p-12 rounded-[50px] shadow-2xl max-w-md w-full text-center space-y-8 border-8 border-white relative overflow-hidden">
        
        <!-- DECORACIÓN DE FONDO -->
        <div class="absolute -top-10 -right-10 w-32 h-32 bg-blue-50 rounded-full opacity-50"></div>

        <!-- ESTADO: CARGANDO -->
        <div v-if="loading" class="space-y-4">
            <div class="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
            <p class="font-black text-gray-400 uppercase text-xs tracking-widest">Verificando transacción...</p>
        </div>

        <!-- ESTADO: APROBADO -->
        <div v-else-if="status === 'approved'" class="animate-fade-in space-y-6">
            <div class="text-7xl">✅</div>
            <h2 class="text-4xl font-black tracking-tighter text-gray-900 leading-none">¡Recarga Exitosa!</h2>
            <p class="text-gray-500 font-medium">El saldo ha sido abonado a la tarjeta correctamente.</p>
            <div class="bg-green-50 p-4 rounded-3xl border border-green-100">
                <span class="block text-[10px] font-black text-green-600 uppercase">Monto Cargado</span>
                <span class="text-2xl font-black text-green-700">{{ formatMoney(amount) }}</span>
            </div>
        </div>

        <!-- ESTADO: PENDIENTE -->
        <div v-else-if="status === 'pending'" class="animate-fade-in space-y-6">
            <div class="text-7xl">⏳</div>
            <h2 class="text-4xl font-black tracking-tighter text-gray-900 leading-none">Pago en Proceso</h2>
            <p class="text-gray-500 font-medium">
                Tu banco está procesando la solicitud. Esto puede tardar unos minutos. Te avisaremos por correo.
            </p>
        </div>

        <!-- ESTADO: RECHAZADO / ERROR -->
        <div v-else class="animate-fade-in space-y-6">
            <div class="text-7xl">❌</div>
            <h2 class="text-4xl font-black tracking-tighter text-gray-900 leading-none">Pago No Exitoso</h2>
            <p class="text-gray-500 font-medium">La transacción fue rechazada por la entidad financiera o cancelada.</p>
            <p class="text-xs text-red-500 font-bold bg-red-50 p-3 rounded-2xl">Ref: {{ reference }}</p>
        </div>

        <!-- BOTÓN REGRESAR -->
        <div class="pt-6">
            <router-link to="/" class="w-full bg-gray-900 text-white py-5 rounded-[24px] font-black uppercase tracking-widest shadow-xl hover:bg-black transition-all block">
                Regresar al Inicio
            </router-link>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';

const route = useRoute();
const loading = ref(true);
const status = ref('pending');
const amount = ref(0);
const reference = ref('');

const checkStatus = async () => {
    // 1. Obtener la referencia de la URL (PayU la envía como referenceCode o reference_sale)
    reference.value = route.query.referenceCode || route.query.reference_sale;
    
    if (!reference.value) {
        status.value = 'error';
        loading.value = false;
        return;
    }

    try {
        // 2. Preguntar a nuestra API
        const { data } = await api.get(`/recharges/status/${reference.value}`);
        status.value = data.status;
        amount.value = data.amount;
    } catch (e) {
        // Si no está en nuestra DB todavía, mostramos el estado que envíe PayU por URL
        // transactionState 4 = Aprobado, 6 = Rechazado, 7 = Pendiente
        const payuState = route.query.transactionState;
        if (payuState === '4') status.value = 'approved';
        else if (payuState === '6') status.value = 'declined';
        else status.value = 'pending';
    } finally {
        loading.value = false;
    }
};

onMounted(checkStatus);
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
</style>