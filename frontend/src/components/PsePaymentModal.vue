<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
    <div class="bg-white rounded-[40px] shadow-2xl max-w-lg w-full overflow-hidden border-4 border-blue-50">
      
      <!-- CABECERA -->
      <div class="p-6 bg-blue-600 text-white text-center">
          <h3 class="text-xl font-black uppercase italic tracking-tighter">Recarga Saldo PSE</h3>
          <!-- SALDO ACTUAL VISIBLE -->
          <div class="mt-2 inline-block bg-white/20 px-4 py-1 rounded-full text-xs font-bold">
            Saldo Actual: {{ formatMoney(currentBalance) }}
          </div>
      </div>

      <div class="p-8 space-y-4">
        <!-- BENEFICIARIO -->
        <div class="text-center">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Titular de Tarjeta</p>
            <p class="text-lg font-black text-gray-800">{{ title }}</p>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- MONTO -->
            <div class="md:col-span-2">
                <label class="text-[10px] font-black text-gray-400 uppercase">Monto a Recargar</label>
                <input v-model.number="form.amount" type="number" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-black text-xl text-primary outline-none focus:border-primary">
            </div>

            <!-- DATOS CONTACTO OPCIONALES -->
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase">Teléfono (Opcional)</label>
                <input v-model="form.phone" type="text" placeholder="Ej: 300123..." class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl text-sm">
            </div>
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase">Dirección (Opcional)</label>
                <input v-model="form.address" type="text" placeholder="Ej: Calle 10 #2..." class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl text-sm">
            </div>

            <!-- BANCO -->
            <div class="md:col-span-2">
                <label class="text-[10px] font-black text-gray-400 uppercase">Banco</label>
                <select v-model="form.bank_code" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold text-sm">
                    <option v-for="bank in banks" :key="bank.pseCode" :value="bank.pseCode">{{ bank.description }}</option>
                </select>
            </div>

            <!-- DNI -->
            <div class="flex gap-2 md:col-span-2">
                <select v-model="form.buyer_dni_type" class="w-24 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold text-xs uppercase">
                    <option value="CC">CC</option><option value="CE">CE</option><option value="NIT">NIT</option>
                </select>
                <input v-model="form.buyer_dni" type="text" placeholder="Número de Documento" class="flex-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold outline-none focus:border-primary">
            </div>
        </div>

        <button @click="handlePayment" :disabled="loading || !form.bank_code || !form.buyer_dni"
                class="w-full bg-primary text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-100 active:scale-95 transition-all">
            {{ loading ? 'Conectando...' : '🚀 CONTINUAR AL BANCO' }}
        </button>

        <button @click="$emit('close')" class="w-full text-gray-400 text-[10px] font-black uppercase tracking-widest">Cancelar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue';
import api from '../api/axios';
import { formatMoney, getLocalISODate } from '../utils/formatters';

const props = defineProps({
    isOpen: Boolean,
    title: String,
    cardUid: String,
    currentBalance: { type: Number, default: 0 } 
});

const emit = defineEmits(['close']);
const loading = ref(false);
const banks = ref([]);

const form = reactive({
    amount: 50000,
    bank_code: null,
    user_type: "0",
    buyer_dni_type: "CC",
    buyer_dni: "",
    card_uid: "",
    phone: "",  
    address: "" 
});

watch(() => props.isOpen, async (val) => {
    if (val) {
        form.card_uid = props.cardUid;
        if (banks.value.length === 0) {
            const { data } = await api.get('/recharges/banks');
            banks.value = data;
            if(data.length > 0) form.bank_code = data[0].pseCode;
        }
    }
});

const handlePayment = async () => {
    loading.value = true;
    try {
        const { data } = await api.post('/recharges/init-payu-pse', form);
        if (data.redirect_url) window.location.href = data.redirect_url;
    } catch (error) {
        alert(error.response?.data?.detail || "Error");
    } finally { loading.value = false; }
};
</script>