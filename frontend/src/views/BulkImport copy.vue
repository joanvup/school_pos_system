<template>
  <div class="space-y-6">
    <h1 class="text-2xl font-bold text-gray-800">Carga Masiva de Datos</h1>

    <!-- SELECTOR DE TIPO -->
    <div class="flex justify-center gap-4 mb-6">
      <button 
        v-for="type in [{id:'students', label:'Estudiantes', icon:'🎓'}, {id:'employees', label:'Empleados', icon:'💼'}]"
        :key="type.id"
        @click="importType = type.id; result = null; progress = 0"
        :class="['px-6 py-2 rounded-full font-bold transition flex items-center gap-2', importType === type.id ? 'bg-primary text-white' : 'bg-gray-200 text-gray-600']"
      >
        <span>{{ type.icon }}</span> {{ type.label }}
      </button>
    </div>

    <div class="bg-white p-8 rounded-xl shadow-lg max-w-2xl mx-auto border border-gray-100">
      
      <!-- INPUT DE ARCHIVO -->
      <div class="flex flex-col items-center gap-6">
        <div class="w-full border-2 border-dashed border-gray-300 rounded-lg p-10 text-center hover:border-primary transition cursor-pointer" @click="$refs.fileInput.click()">
          <input type="file" ref="fileInput" accept=".xlsx" @change="handleFileChange" class="hidden" />
          <div class="text-4xl mb-2">📁</div>
          <p class="text-gray-600">{{ selectedFile ? selectedFile.name : 'Haz clic para seleccionar el archivo Excel' }}</p>
        </div>

        <!-- BARRA DE PROGRESO -->
        <div v-if="uploading || progress > 0" class="w-full space-y-2">
            <div class="flex justify-between text-xs font-bold uppercase text-gray-500">
                <span>{{ progress < 100 ? 'Subiendo Archivo...' : 'Procesando en Servidor...' }}</span>
                <span>{{ progress }}%</span>
            </div>
            <div class="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
                <div class="bg-primary h-full transition-all duration-300" :style="{ width: progress + '%' }"></div>
            </div>
        </div>

        <button 
            @click="uploadFile" 
            :disabled="!selectedFile || uploading"
            class="bg-primary text-white px-8 py-3 rounded-lg font-bold shadow-lg hover:bg-blue-700 disabled:opacity-50 transition w-full"
        >
            {{ uploading ? 'Espere por favor...' : 'Iniciar Carga' }}
        </button>
      </div>

      <!-- REPORTE DE RESULTADOS -->
      <div v-if="result" class="mt-10 space-y-4">
        <h3 class="font-bold text-lg border-b pb-2">Resumen de Operación</h3>
        
        <div class="grid grid-cols-3 gap-4">
            <div class="bg-gray-50 p-4 rounded-lg text-center">
                <div class="text-2xl font-bold">{{ result.total }}</div>
                <div class="text-xs text-gray-500 uppercase">Filas</div>
            </div>
            <div class="bg-green-50 p-4 rounded-lg text-center border border-green-100">
                <div class="text-2xl font-bold text-green-600">{{ result.created_students || result.created }}</div>
                <div class="text-xs text-gray-500 uppercase">Nuevos</div>
            </div>
            <div class="bg-blue-50 p-4 rounded-lg text-center border border-blue-100">
                <div class="text-2xl font-bold text-blue-600">{{ result.updated_students || result.updated }}</div>
                <div class="text-xs text-gray-500 uppercase">Actualizados</div>
            </div>
        </div>

        <!-- SECCIÓN DE ERRORES MEJORADA -->
        <div v-if="result.errors && result.errors.length > 0" class="mt-6">
            <div class="flex items-center gap-2 text-red-600 font-bold mb-2">
                <span>⚠️</span> Se encontraron {{ result.errors.length }} errores:
            </div>
            <div class="bg-red-50 rounded-lg border border-red-100 max-h-60 overflow-y-auto">
                <table class="w-full text-xs text-left">
                    <tbody class="divide-y divide-red-100">
                        <tr v-for="(err, i) in result.errors" :key="i">
                            <td class="p-3 text-red-700">{{ err }}</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <p class="text-[10px] text-gray-400 mt-2">* Las filas con error no fueron procesadas. Corrija el archivo y vuelva a subirlo.</p>
        </div>

        <div v-else-if="!uploading" class="p-4 bg-green-100 text-green-700 rounded-lg text-center font-bold">
            ✅ Carga completada sin errores.
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
const progress = ref(0);
const result = ref(null);

const handleFileChange = (event) => {
    selectedFile.value = event.target.files[0];
    result.value = null;
    progress.value = 0;
};

const uploadFile = async () => {
    if (!selectedFile.value) return;
    
    uploading.value = true;
    result.value = null;
    progress.value = 0;

    const formData = new FormData();
    formData.append('file', selectedFile.value);

    const endpoint = importType.value === 'students' ? '/import/students' : '/import/employees';

    try {
        const response = await api.post(endpoint, formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
            // RASTREO DE PROGRESO DE SUBIDA
            onUploadProgress: (progressEvent) => {
                const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                // Dejamos el progreso en 95% mientras el servidor procesa el Excel
                progress.value = percentCompleted > 95 ? 95 : percentCompleted;
            }
        });

        progress.value = 100; // Finalizado
        result.value = response.data;
        selectedFile.value = null;
        fileInput.value.value = '';
    } catch (error) {
        progress.value = 0;
        alert("Error crítico: " + (error.response?.data?.detail || "Fallo en el servidor"));
    } finally {
        uploading.value = false;
    }
};
</script>