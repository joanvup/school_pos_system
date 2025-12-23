<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-6">
    <div class="bg-white p-12 rounded-[50px] shadow-2xl max-w-md w-full text-center space-y-8 border-8 border-white relative overflow-hidden">
        
        <!-- DECORACIÓN DE FONDO -->
        <div class="absolute -top-10 -right-10 w-32 h-32 bg-blue-50 rounded-full opacity-50"></div>

        <!-- ESTADO: PENDIENTE (Buscando confirmación) -->
        <div v-if="status === 'pending'" class="space-y-6">
            <div class="w-20 h-20 border-8 border-primary border-t-transparent rounded-full animate-spin mx-auto"></div>
            <h2 class="text-3xl font-black tracking-tighter text-gray-900 leading-none">Esperando Confirmación</h2>
            <p class="text-gray-500 font-medium">
                Estamos verificando tu pago con el banco. <br>
                <span class="text-primary font-bold">Esta página se actualizará sola...</span>
            </p>
            <div class="text-[10px] text-gray-400 font-bold uppercase tracking-widest bg-gray-50 py-2 rounded-xl">
                Ref: {{ reference }}
            </div>
        </div>

        <!-- ESTADO: APROBADO -->
        <div v-else-if="status === 'approved'" class="animate-scale-in space-y-6">
            <div class="text-7xl">✅</div>
            <h2 class="text-4xl font-black tracking-tighter text-gray-900 leading-none">¡Recarga Exitosa!</h2>
            <p class="text-gray-500 font-medium">El dinero ya está disponible en tu tarjeta.</p>
            <div class="bg-green-50 p-5 rounded-3xl border-2 border-green-100">
                <span class="block text-[10px] font-black text-green-600 uppercase mb-1">Nuevo Saldo Abonado</span>
                <span class="text-3xl font-black text-green-700">{{ formatMoney(amount) }}</span>
            </div>
        </div>

        <!-- ESTADO: RECHAZADO -->
        <div v-else class="animate-scale-in space-y-6">
            <div class="text-7xl">❌</div>
            <h2 class="text-4xl font-black tracking-tighter text-gray-900 leading-none">Pago No Exitoso</h2>
            <p class="text-gray-500 font-medium">La entidad financiera rechazó la transacción o fue cancelada por el usuario.</p>
        </div>

        <!-- BOTÓN REGRESAR INTELIGENTE -->
        <div class="pt-6">
            <button 
                @click="goHome"
                class="w-full bg-gray-900 text-white py-5 rounded-[24px] font-black uppercase tracking-widest shadow-xl hover:bg-black transition-all transform active:scale-95"
            >
                Regresar al Inicio
            </button>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const status = ref('pending');
const amount = ref(0);
const reference = ref('');
let pollInterval = null;

// 1. LÓGICA DE REDIRECCIÓN POR ROL
const goHome = () => {
    const role = authStore.user?.role;
    if (role === 'padre') router.push('/my-family');
    else if (role === 'empleado') router.push('/my-card');
    else if (role === 'vendedor') router.push('/pos');
    else router.push('/dashboard'); // Admin y Supervisor
};

// 2. CONSULTAR ESTADO AL BACKEND
const checkPaymentStatus = async () => {
    if (!reference.value) return;

    try {
        const { data } = await api.get(`/recharges/status/${reference.value}`);
        
        // Si el estado ya no es 'pending', detenemos el reloj
        if (data.status === 'approved' || data.status === 'declined' || data.status === 'expired') {
            status.value = data.status;
            amount.value = data.amount;
            clearInterval(pollInterval);
            console.log("¡Pago procesado!");
        }
    } catch (e) {
        console.warn("Esperando que el servidor registre la transacción...");
    }
};

onMounted(() => {
    // Tomar referencia de la URL de PayU
    reference.value = route.query.referenceCode || route.query.reference_sale;

    if (reference.value) {
        // Iniciar Polling: Preguntar cada 3 segundos
        checkPaymentStatus(); // Primera ejecución inmediata
        pollInterval = setInterval(checkPaymentStatus, 3000);
    } else {
        status.value = 'error';
    }
});

// Limpiar el proceso si el usuario se va de la página antes de que termine
onUnmounted(() => {
    if (pollInterval) clearInterval(pollInterval);
});
</script>

<style scoped>
.animate-scale-in {
    animation: scaleIn 0.5s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
}
</style>