<template>
  <div>
    <div class="mb-6">
      <h1 class="text-2xl font-black text-gray-800">Pasarela de pago</h1>
      <p class="text-sm text-gray-500 mt-1">
        La plataforma opera únicamente con PayU PSE. Las recargas solo se acreditan cuando PayU
        envía una notificación firmada y válida.
      </p>
    </div>

    <div v-if="loading" class="py-16 text-center text-gray-400">Cargando…</div>

    <div v-else class="space-y-3 max-w-xl">
      <div
        v-for="p in providers"
        :key="p.gateway"
        class="rounded-2xl border border-gray-200 p-5 bg-white"
      >
        <div class="flex items-center gap-3">
          <span class="text-2xl">{{ p.icon }}</span>
          <div>
            <p class="font-black text-gray-800">{{ p.label }}</p>
            <div class="flex items-center gap-2 mt-0.5">
              <span class="text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                {{ p.is_active ? 'Activa' : 'Configurada' }}
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

        <p class="text-xs mt-3 flex items-center gap-2" :class="p.has_credentials ? 'text-green-600' : 'text-amber-600'">
          <span class="inline-block w-2 h-2 rounded-full" :class="p.has_credentials ? 'bg-green-500' : 'bg-amber-500'"></span>
          {{ p.has_credentials ? 'Credenciales configuradas' : 'Faltan credenciales de PayU en el servidor' }}
        </p>
      </div>

      <p v-if="providers.length === 0" class="text-sm text-gray-500">
        No hay pasarela configurada. Ejecuta el seed de la base de datos.
      </p>

      <p v-if="error" class="text-sm text-red-600 mt-3">{{ error }}</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api from '../api/axios';

const providers = ref([]);
const loading = ref(true);
const error = ref('');

const ICONS = { payu: '📡' };

async function load() {
  loading.value = true;
  error.value = '';
  try {
    const { data } = await api.get('/payments/providers');
    providers.value = data.map((p) => ({ ...p, icon: ICONS[p.gateway] || '💳' }));
  } catch (e) {
    error.value = e?.response?.data?.detail || 'No se pudo cargar la pasarela';
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
