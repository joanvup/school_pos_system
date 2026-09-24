<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-black text-gray-800">Pasarela de pago</h1>
      <p class="text-sm text-gray-500 mt-1">
        Selecciona con qué pasarela trabaja la plataforma. El cambio aplica al instante a todas las recargas.
      </p>
    </div>

    <div v-if="loading" class="py-16 text-center text-gray-400">Cargando…</div>

    <div v-else class="space-y-3 max-w-xl">
      <div
        v-for="p in providers"
        :key="p.gateway"
        class="rounded-2xl border p-5 bg-white transition-colors"
        :class="p.is_active ? 'border-primary ring-2 ring-primary/30' : 'border-gray-200'"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-3">
            <span class="text-2xl">{{ p.icon }}</span>
            <div>
              <p class="font-black text-gray-800">{{ p.label }}</p>
              <div class="flex items-center gap-2 mt-0.5">
                <span
                  class="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full"
                  :class="p.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'"
                >
                  {{ p.is_active ? 'Activa' : 'Inactiva' }}
                </span>
                <span
                  v-if="p.is_test"
                  class="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-amber-100 text-amber-700"
                >
                  Modo prueba
                </span>
              </div>
            </div>
          </div>

          <button
            v-if="!p.is_active"
            :disabled="activating === p.gateway"
            class="px-4 py-2 rounded-xl bg-primary text-white font-bold text-sm disabled:opacity-50"
            @click="activate(p.gateway)"
          >
            {{ activating === p.gateway ? 'Activando…' : 'Activar' }}
          </button>
        </div>

        <p class="text-xs mt-3 flex items-center gap-2" :class="p.has_credentials ? 'text-green-600' : 'text-amber-600'">
          <span class="inline-block w-2 h-2 rounded-full" :class="p.has_credentials ? 'bg-green-500' : 'bg-amber-500'"></span>
          {{ p.has_credentials ? 'Credenciales configuradas' : 'Faltan credenciales (usa el panel de PayU o crea tu cuenta Wompi/Mercado Pago)' }}
        </p>
      </div>

      <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
      <p v-if="updated" class="text-sm text-green-600 mt-3">{{ updated }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import axios from '../api/axios';

const providers = ref([]);
const loading = ref(true);
const activating = ref('');
const error = ref('');
const updated = ref('');

const ICONS = { payu: '📡', wompi: '🏦', mercadopago: '🅼' };

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await axios.get('/payments/providers');
    providers.value = data.map((p) => ({ ...p, icon: ICONS[p.gateway] || '💳' }));
  } catch (e) {
    error.value = e?.response?.data?.detail || 'No se pudieron cargar las pasarelas';
  } finally {
    loading.value = false;
  }
}

async function activate(gateway) {
  activating.value = gateway;
  error.value = '';
  updated.value = '';
  try {
    const { data } = await axios.post('/payments/providers/activate', { gateway });
    updated.value = data.detail;
    await load();
  } catch (e) {
    error.value = e?.response?.data?.detail || 'No se pudo cambiar la pasarela';
  } finally {
    activating.value = '';
  }
}

onMounted(load);
</script>