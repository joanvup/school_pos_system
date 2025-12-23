<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">Carga Masiva e Inteligente</h1>

    <!-- SELECTOR -->
    <div class="flex justify-center gap-4">
        <button @click="importType = 'students'; result = null" :class="[importType === 'students' ? 'bg-primary text-white shadow-lg' : 'bg-gray-200 text-gray-600', 'px-6 py-2 rounded-full font-bold transition-all duration-300']">
            🎓 Estudiantes / Padres
        </button>
        <button @click="importType = 'employees'; result = null" :class="[importType === 'employees' ? 'bg-primary text-white shadow-lg' : 'bg-gray-200 text-gray-600', 'px-6 py-2 rounded-full font-bold transition-all duration-300']">
            💼 Empleados / Staff
        </button>
    </div>

    <div class="bg-white p-8 rounded-2xl shadow-xl max-w-2xl mx-auto border border-gray-100">
      <div class="text-center mb-8">
        <div class="text-5xl mb-4">{{ importType === 'students' ? '🏫' : '🏢' }}</div>
        <h2 class="text-xl font-bold text-gray-700">Importar y Actualizar Datos</h2>
        <p class="text-gray-400 text-sm mt-2">
            Si el registro ya existe (por email), el sistema actualizará los nombres y contraseñas automáticamente.
        </p>
      </div>

      <!-- ZONA DE CARGA -->
      <div class="space-y-4">
        <input 
          type="file" 
          ref="fileInput"
          accept=".xlsx"
          @change="handleFileChange"
          class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-6 file:rounded-full file:border-0 file:text-sm file:font-bold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 cursor-pointer"
        />

        <!-- BARRA DE PROGRESO -->
        <div v-if="uploading" class="space-y-2">
            <div class="flex justify-between text-xs font-bold text-gray-500">
                <span>Subiendo archivo...</span>
                <span>{{ uploadProgress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-2">
                <div class="bg-primary h-2 rounded-full transition-all duration-300" :style="{ width: uploadProgress + '%' }"></div>
            </div>
        </div>

        <button 
            @click="uploadFile" 
            :disabled="!selectedFile || uploading"
            class="w-full py-4 bg-primary text-white rounded-xl font-bold shadow-lg hover:bg-blue-700 disabled:opacity-50 transition-all flex justify-center items-center gap-2"
        >
            <span v-if="uploading">Procesando...</span>
            <span v-else>🚀 Iniciar Proceso Masivo</span>
        </button>
      </div>

      <!-- RESULTADOS DETALLADOS -->
      <div v-if="result" class="mt-8 animate-fade-in">
        <div class="grid grid-cols-3 gap-4 mb-6">
            <div class="bg-blue-50 p-4 rounded-xl text-center border border-blue-100">
                <div class="text-2xl font-black text-blue-700">{{ result.total }}</div>
                <div class="text-[10px] uppercase font-bold text-blue-500">Filas</div>
            </div>
            <div class="bg-green-50 p-4 rounded-xl text-center border border-green-100">
                <div class="text-2xl font-black text-green-700">{{ result.created }}</div>
                <div class="text-[10px] uppercase font-bold text-green-500">Creados</div>
            </div>
            <div class="bg-orange-50 p-4 rounded-xl text-center border border-orange-100">
                <div class="text-2xl font-black text-orange-700">{{ result.updated }}</div>
                <div class="text-[10px] uppercase font-bold text-orange-500">Actualizados</div>
            </div>
        </div>

        <!-- ERRORES -->
        <div v-if="result.errors && result.errors.length > 0" class="mt-4">
            <h4 class="text-sm font-bold text-red-600 mb-2 flex items-center gap-1">
                ⚠️ Errores en el archivo ({{ result.errors.length }})
            </h4>
            <div class="bg-red-50 p-3 rounded-lg border border-red-100 max-h-48 overflow-y-auto">
                <div v-for="(err, i) in result.errors" :key="i" class="text-xs text-red-700 py-1 border-b border-red-100 last:border-0">
                    {{ err }}
                </div>
            </div>
        </div>
        
        <div v-else class="p-4 bg-green-50 text-green-700 rounded-lg text-center font-bold text-sm">
            ✨ ¡Proceso completado sin errores!
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import api from '../api/axios';

const importType = ref('students');
const fileInput = ref(null);
const selectedFile = ref(null);
const uploading = ref(false);
const uploadProgress = ref(0);
const result = ref(null);

const handleFileChange = (e) => {
    selectedFile.value = e.target.files[0];
    result.value = null;
    uploadProgress.value = 0;
};

const uploadFile = async () => {
    if (!selectedFile.value) return;
    
    uploading.value = true;
    uploadProgress.value = 0;
    result.value = null;

    const formData = new FormData();
    // Asegúrate de que el nombre 'file' coincida con el backend
    formData.append('file', selectedFile.value); 

    const endpoint = importType.value === 'students' ? '/import/students' : '/import/employees';

    try {
        // 1. Enviar archivo y obtener ID de tarea
        const res = await api.post(endpoint, formData, {
            headers: {
                // IMPORTANTE: Al ponerlo en null o borrarlo, 
                // el navegador pone automáticamente 'multipart/form-data' con el boundary correcto
                'Content-Type': 'multipart/form-data' 
            }
        });
        
        const taskId = res.data.task_id;

        // 2. Iniciar Polling (preguntar cada 500ms)
        const pollInterval = setInterval(async () => {
            try {
                const statusRes = await api.get(`/import/status/${taskId}`);
                const data = statusRes.data;

                if (data.status === 'processing') {
                    uploadProgress.value = data.progress;
                } 
                else if (data.status === 'completed') {
                    clearInterval(pollInterval);
                    uploadProgress.value = 100;
                    result.value = data.result;
                    uploading.value = false;
                } 
                else if (data.status === 'failed') {
                    clearInterval(pollInterval);
                    uploading.value = false;
                    alert("Error en proceso: " + data.error);
                }
            } catch (e) {
                console.error("Error polling:", e);
            }
        }, 800);

    } catch (error) {
        console.error("Error upload:", error);
        alert("Error al subir archivo. Verifique el formato.");
        uploading.value = false;
    }
};
</script>

<style scoped>
.animate-fade-in { animation: fadeIn 0.5s ease-in; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>