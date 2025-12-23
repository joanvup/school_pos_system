<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[100] p-4">
    <div class="bg-white rounded-[40px] shadow-2xl max-w-lg w-full overflow-hidden animate-fade-in border-4 border-blue-50">
      
      <!-- CABECERA -->
      <div class="p-8 bg-blue-600 text-white text-center relative">
          <button @click="$emit('close')" class="absolute top-4 right-6 text-2xl opacity-50 hover:opacity-100">×</button>
          <div class="text-4xl mb-2">🏦</div>
          <h3 class="text-2xl font-black italic uppercase tracking-tighter">Recarga Segura PSE</h3>
          <p class="text-blue-100 text-xs font-bold uppercase tracking-widest mt-1">Procesado por PayU Colombia</p>
      </div>

      <div class="p-8 space-y-6">
        <!-- INFO DEL BENEFICIARIO -->
        <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100 flex justify-between items-center">
            <span class="text-xs font-black text-gray-400 uppercase">Beneficiario:</span>
            <span class="text-sm font-black text-gray-700">{{ title }}</span>
        </div>

        <!-- FORMULARIO -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <!-- MONTO -->
            <div class="md:col-span-2">
                <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Monto a Recargar</label>
                <div class="relative mt-1">
                    <span class="absolute left-4 top-3.5 font-black text-gray-400 text-xl">$</span>
                    <input v-model.number="form.amount" type="number" step="1000" min="5000" 
                           class="w-full pl-10 pr-4 py-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-black text-2xl text-primary">
                </div>
            </div>

            <!-- BANCO -->
            <div class="md:col-span-2">
                <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Selecciona tu Banco</label>
                <select v-model="form.bank_code" class="w-full mt-1 p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold text-gray-700">
                    <option :value="null" disabled>Cargando bancos...</option>
                    <option v-for="bank in banks" :key="bank.id" :value="bank.id">
                        {{ bank.description }}
                    </option>
                </select>
            </div>

            <!-- TIPO PERSONA -->
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Tipo de Persona</label>
                <select v-model="form.user_type" class="w-full mt-1 p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
                    <option value="0">Natural</option>
                    <option value="1">Jurídica (Empresa)</option>
                </select>
            </div>

            <!-- TIPO DOCUMENTO -->
            <div>
                <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Documento</label>
                <div class="flex gap-2 mt-1">
                    <select v-model="form.buyer_dni_type" class="w-20 p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold text-xs uppercase">
                        <option value="CC">CC</option>
                        <option value="CE">CE</option>
                        <option value="NIT">NIT</option>
                    </select>
                    <input v-model="form.buyer_dni" type="text" placeholder="Número" 
                           class="flex-1 p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
                </div>
            </div>
        </div>

        <!-- BOTÓN DE ACCIÓN -->
        <button 
            @click="handlePayment" 
            :disabled="loading || !form.bank_code || !form.buyer_dni || form.amount < 5000"
            class="w-full bg-green-500 hover:bg-green-600 text-white py-5 rounded-[28px] font-black text-xl shadow-xl shadow-green-100 transition-all active:scale-95 disabled:opacity-30 flex justify-center items-center gap-3"
        >
            <span v-if="!loading">🚀 IR AL BANCO</span>
            <div v-else class="w-6 h-6 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
        </button>
        
        <p class="text-[9px] text-center text-gray-400 font-bold uppercase tracking-widest">
            Al hacer clic serás redirigido a la plataforma segura de tu banco.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, watch } from 'vue';
import api from '../api/axios';

const props = defineProps({
    isOpen: Boolean,
    title: String,
    cardUid: String
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
    card_uid: ""
});

// Cargar bancos al abrir el modal
watch(() => props.isOpen, async (val) => {
    if (val && banks.value.length === 0) {
        try {
            const { data } = await api.get('/recharges/banks');
            banks.value = data;
            // Seleccionar el primer banco por defecto si existe
            if(data.length > 0) form.bank_code = data[0].id;
        } catch (e) {
            console.error("Error cargando bancos", e);
        }
    }
    if (val) {
        form.card_uid = props.cardUid;
    }
});

const handlePayment = async () => {
    loading.value = true;
    try {
        const { data } = await api.post('/recharges/init-payu-pse', form);
        
        // ¡REDIRECCIÓN AL BANCO!
        if (data.redirect_url) {
            window.location.href = data.redirect_url;
        } else {
            alert("No se pudo obtener la URL del banco.");
        }
    } catch (error) {
        alert("Error: " + (error.response?.data?.detail || "Falla en comunicación con PayU"));
    } finally {
        loading.value = false;
    }
};
</script>