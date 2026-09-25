<template>
  <div class="max-w-4xl mx-auto space-y-8 pb-20">
    <h1 class="text-3xl font-black text-gray-900 tracking-tighter">Configuración del Sistema</h1>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
      
      <!-- COLUMNA IZQUIERDA: LOGO Y NOMBRE -->
      <div class="space-y-6">
        <div class="bg-white p-6 rounded-[32px] shadow-sm border border-gray-100 text-center">
            <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-4">Logo Institucional</h3>
            
            <div class="relative group inline-block">
                <div class="w-32 h-32 rounded-[40px] overflow-hidden bg-gray-50 border-2 border-dashed border-gray-200 flex items-center justify-center mb-4 mx-auto">
                    <img v-if="settings.school_logo" :src="baseUrl + settings.school_logo" class="w-full h-full object-contain p-2">
                    <span v-else class="text-4xl">🏫</span>
                </div>
                <input type="file" @change="uploadLogo" accept="image/*" class="absolute inset-0 opacity-0 cursor-pointer">
                <div class="text-[10px] font-bold text-primary uppercase">Click para cambiar logo</div>
            </div>
            
            <div class="mt-6 text-left">
                <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Nombre del Colegio</label>
                <input v-model="settings.school_name" type="text" class="w-full border-2 border-gray-50 bg-gray-50 rounded-2xl p-3 focus:border-primary outline-none font-bold">
            </div>
        </div>
      </div>

      <!-- COLUMNA DERECHA: PARAMETROS TÉCNICOS -->
      <div class="md:col-span-2 space-y-6">
        
        <!-- SOPORTE Y MONEDA -->
        <div class="bg-white p-8 rounded-[32px] shadow-sm border border-gray-100">
            <h3 class="text-xs font-black text-gray-400 uppercase tracking-widest mb-6">Información General</h3>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Email de Soporte</label>
                    <input v-model="settings.school_support_email" type="email" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Símbolo de Moneda</label>
                    <input v-model="settings.currency_symbol" type="text" placeholder="$" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
            </div>
        </div>

        <div class="bg-white p-8 rounded-[32px] shadow-sm border border-blue-100">
            <div class="flex items-center gap-3 mb-5">
                <span class="text-2xl">⬇️</span>
                <div>
                    <h3 class="text-xs font-black text-primary uppercase tracking-widest">Descargas</h3>
                    <p class="text-xs text-gray-400 font-medium mt-1">Instala el lector NFC para los puntos de venta.</p>
                </div>
            </div>
            <button
                @click="downloadReader"
                :disabled="downloadingReader"
                class="w-full bg-primary text-white py-4 rounded-2xl font-black text-sm uppercase tracking-wider shadow-lg shadow-blue-100 hover:bg-blue-700 transition-all active:scale-95 disabled:opacity-50"
            >
                {{ downloadingReader ? 'Preparando descarga...' : '⬇️ Descargar lector NFC' }}
            </button>
            <p class="mt-3 text-[10px] text-gray-400 font-medium">Ejecutable para Windows. La descarga requiere un usuario autorizado.</p>
        </div>

        <!-- CONFIGURACIÓN SMTP (EMAIL) -->
        <div class="bg-white p-8 rounded-[32px] shadow-sm border border-orange-100 bg-orange-50/10">
            <div class="flex items-center gap-2 mb-6">
                <span class="text-xl">📧</span>
                <h3 class="text-xs font-black text-orange-600 uppercase tracking-widest">Parámetros de Correo (SMTP)</h3>
            </div>
            
            <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div class="md:col-span-2">
                    <label class="text-[10px] font-black text-gray-400 uppercase">Servidor SMTP (Host)</label>
                    <input v-model="settings.smtp_host" type="text" placeholder="smtp.gmail.com" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Puerto</label>
                    <input v-model="settings.smtp_port" type="text" placeholder="587" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Nombre Remitente</label>
                    <input v-model="settings.smtp_from_name" type="text" placeholder="Colegio POS" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Usuario Correo</label>
                    <input v-model="settings.smtp_user" type="text" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
                <div>
                    <label class="text-[10px] font-black text-gray-400 uppercase">Contraseña / Token</label>
                    <input v-model="settings.smtp_pass" type="password" class="w-full border-2 border-gray-50 bg-gray-50 rounded-xl p-3 outline-none focus:border-primary">
                </div>
            </div>
            <p class="mt-4 text-[10px] text-orange-400 font-medium">* Estos datos son necesarios para que funcione la recuperación de contraseña.</p>
        </div>

        <button 
            @click="saveSettings" 
            :disabled="loading"
            class="w-full bg-primary text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all active:scale-95 disabled:opacity-50"
        >
            {{ loading ? 'Guardando...' : '💾 GUARDAR CONFIGURACIÓN' }}
        </button>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import api, { downloadNfcReader } from '../api/axios';
import { useConfigStore } from '../stores/config';
const configStore = useConfigStore();

const baseUrl = configStore.baseUrl;
const loading = ref(false);
const downloadingReader = ref(false);
const settings = ref({
    school_name: '',
    school_logo: '',
    school_support_email: '',
    smtp_host: '',
    smtp_port: '',
    smtp_user: '',
    smtp_pass: '',
    smtp_from_name: '',
    currency_symbol: '$'
});

const loadSettings = async () => {
    try {
        const { data } = await api.get('/settings/');
        // Fusionar datos recibidos con el objeto inicial
        Object.assign(settings.value, data);
    } catch (e) { console.error(e); }
};

const saveSettings = async () => {
    loading.value = true;
    try {
        await api.put('/settings/', settings.value);
        alert("✅ Configuración guardada correctamente");
        // Recargar para asegurar consistencia
        location.reload(); 
    } catch (e) {
        alert("Error al guardar");
    } finally {
        loading.value = false;
    }
};

const downloadReader = async () => {
    downloadingReader.value = true;
    try {
        await downloadNfcReader();
    } catch (e) {
        alert("No se pudo descargar el lector NFC. Intenta nuevamente.");
    } finally {
        downloadingReader.value = false;
    }
};

const uploadLogo = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);

    try {
        const { data } = await api.post('/settings/logo', formData, {
            headers: { 'Content-Type': 'multipart/form-data' }
        });
        settings.value.school_logo = data.logo_url;
        alert("✅ Logo institucional actualizado");
    } catch (e) {
        alert("Error subiendo el logo");
    }
};

onMounted(loadSettings);
</script>