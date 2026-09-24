<template>
  <Transition name="fade">
    <div v-if="isOpen" class="fixed inset-0 bg-black/70 backdrop-blur-md flex items-center justify-center z-[100] p-4">
      <div class="bg-white rounded-[40px] shadow-2xl max-w-lg w-full overflow-hidden border-4 border-blue-50 animate-scale-in">

        <div class="p-6 bg-blue-600 text-white text-center relative">
          <button @click="$emit('close')" class="absolute top-4 right-6 text-2xl opacity-50 hover:opacity-100">×</button>
          <h3 class="text-xl font-black uppercase italic tracking-tighter">Recargar Saldo</h3>
          <div class="mt-2 inline-block bg-white/20 px-4 py-1 rounded-full text-xs font-bold">
            Saldo Actual: {{ formatMoney(currentBalance) }}
          </div>
        </div>

        <div class="p-8 space-y-4 max-h-[80vh] overflow-y-auto custom-scrollbar">
          <div class="text-center">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Titular de Tarjeta</p>
            <p class="text-lg font-black text-gray-800 leading-tight">{{ title }}</p>
          </div>

          <!-- Cargando -->
          <div v-if="loadingMethods" class="py-6 text-center text-gray-400 text-sm font-bold">
            Cargando medio de pago…
          </div>

          <template v-else>
            <!-- MONTO -->
            <div>
              <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Monto a Recargar</label>
              <input v-model.number="form.amount" type="number" step="1000"
                     class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-black text-xl text-primary outline-none focus:border-primary">
            </div>

            <!-- MÉTODO -->
            <div>
              <label class="text-[10px] font-black text-gray-400 uppercase ml-2">
                Método de pago ({{ providerLabel }})
              </label>
              <select v-model="form.method"
                      class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold text-sm outline-none focus:border-primary">
                <option v-for="m in methods" :key="m.id" :value="m.id">{{ m.label }}</option>
              </select>
            </div>

            <!-- BANCO (solo si el método lo pide) -->
            <div v-if="needsBank">
              <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Banco del Pagador</label>
              <select v-model="form.bank_code"
                      class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold text-sm outline-none focus:border-primary">
                <option v-for="bank in banks" :key="bank.pseCode" :value="bank.pseCode">{{ bank.description }}</option>
              </select>
            </div>

            <!-- EMAIL -->
            <div>
              <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Correo de Notificación</label>
              <input v-model="form.buyer_email" type="email" placeholder="ejemplo@correo.com"
                     class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl text-sm font-bold outline-none focus:border-primary">
            </div>

            <!-- DNI -->
            <div class="flex gap-2">
              <select v-model="form.buyer_dni_type" class="w-24 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold text-xs uppercase outline-none focus:border-primary">
                <option value="CC">CC</option><option value="CE">CE</option><option value="NIT">NIT</option>
              </select>
              <input v-model="form.buyer_dni" type="text" placeholder="Número de Documento"
                     class="flex-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-xl font-bold outline-none focus:border-primary">
            </div>

            <div v-if="error" class="text-red-500 text-sm font-bold text-center">{{ error }}</div>

            <div class="pt-4">
              <button @click="handlePayment" :disabled="loading || needsBank && !form.bank_code || !form.buyer_dni || !form.buyer_email"
                      class="w-full bg-primary text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-100 active:scale-95 transition-all disabled:opacity-30 disabled:grayscale">
                {{ loading ? 'CONECTANDO...' : '🚀 CONTINUAR PAGO' }}
              </button>
              <button @click="$emit('close')" class="w-full mt-4 text-gray-400 text-[10px] font-black uppercase tracking-widest hover:text-gray-600 transition-colors">Cancelar y Salir</button>
            </div>
          </template>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';
import { useAuthStore } from '../stores/auth';

const authStore = useAuthStore();
const props = defineProps({
  isOpen: Boolean,
  title: String,
  cardUid: String,
  currentBalance: { type: Number, default: 0 }
});
const emit = defineEmits(['close']);

const loading = ref(false);
const loadingMethods = ref(false);
const methods = ref([]);
const providerLabel = ref('');
const providerName = ref('');
const banks = ref([]);
const error = ref('');

const form = reactive({
  amount: 50000,
  method: '',
  bank_code: null,
  user_type: "0",
  buyer_dni_type: "CC",
  buyer_dni: "",
  buyer_email: "",
  phone: "",
  address: ""
});

const needsBank = computed(() => form.method === 'pse');

async function loadMethods() {
  loadingMethods.value = true;
  error.value = '';
  try {
    const { data } = await api.get('/payments/methods');
    providerName.value = data.gateway;
    providerLabel.value = data.label;
    methods.value = data.methods;
    if (data.methods.length > 0) form.method = data.methods[0].id;
    if (data.gateway === 'payu' && banks.value.length === 0) {
      const { data: bankData } = await api.get('/recharges/banks');
      banks.value = bankData;
      if (bankData.length > 0) form.bank_code = bankData[0].pseCode;
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || 'No se pudo cargar el medio de pago';
  } finally {
    loadingMethods.value = false;
  }
}

watch(() => props.isOpen, (val) => {
  if (val) {
    form.card_uid = props.cardUid;
    if (!form.buyer_email) form.buyer_email = authStore.user?.email || "";
    loadMethods();
  }
});

const handlePayment = async () => {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await api.post('/payments/init', form);
    if (data.redirect_url) {
      window.location.href = data.redirect_url;
    } else {
      emit('close');
    }
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Falla en conexión';
  } finally {
    loading.value = false;
  }
};
</script>