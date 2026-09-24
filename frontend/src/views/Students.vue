<template>
  <div class="space-y-6">
    <!-- CABECERA -->
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 tracking-tighter uppercase italic leading-none">Control de Estudiantes</h1>
        <p class="text-gray-400 font-bold text-xs uppercase tracking-widest mt-2">Gestión de identidad y finanzas escolares</p>
      </div>
      <button @click="openStudentModal()" class="bg-primary hover:bg-blue-600 text-white px-8 py-4 rounded-3xl shadow-xl shadow-blue-100 font-black transition-all active:scale-95 flex items-center gap-2 uppercase text-sm">
        <span>➕</span> Registrar Alumno
      </button>
    </div>

    <!-- BARRA DE HERRAMIENTAS (BÚSQUEDA Y PAGINACIÓN) -->
    <div class="bg-white p-5 rounded-[32px] shadow-sm border border-gray-100 flex flex-col lg:flex-row gap-4 items-center justify-between">
        <div class="relative w-full lg:w-1/3">
            <span class="absolute left-4 top-3.5 text-gray-400">🔍</span>
            <input 
                v-model="searchQuery" @input="handleSearch" type="text" 
                placeholder="Buscar por nombre del alumno..." 
                class="w-full pl-12 pr-4 py-3 bg-gray-50 border-2 border-gray-50 rounded-2xl focus:border-primary outline-none transition-all font-bold text-gray-700"
            >
        </div>

        <div class="flex items-center gap-4 bg-gray-50 p-2 rounded-2xl border border-gray-100">
            <button @click="prevPage" :disabled="page === 1" class="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center hover:text-primary disabled:opacity-30 transition-all">◀</button>
            <div class="px-4 text-center">
                <span class="block text-[10px] font-black text-gray-400 uppercase">Página</span>
                <span class="text-sm font-black text-primary">{{ page }}</span>
            </div>
            <button @click="nextPage" :disabled="students.length < limit" class="w-10 h-10 rounded-xl bg-white shadow-sm flex items-center justify-center hover:text-primary disabled:opacity-30 transition-all">▶</button>
        </div>
    </div>

    <!-- LISTADO DE ESTUDIANTES -->
    <div class="bg-white rounded-[40px] shadow-sm border border-gray-100 overflow-hidden">
      <div v-if="loading" class="p-20 text-center">
          <div class="w-12 h-12 border-4 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p class="text-gray-400 font-bold uppercase text-xs tracking-widest">Sincronizando datos...</p>
      </div>

      <table v-else class="min-w-full divide-y divide-gray-100">
        <thead class="bg-gray-50/50">
          <tr class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
            <th class="px-8 py-5 text-left">Información del Estudiante</th>
            <th class="px-8 py-5 text-left">Padre / Acudiente</th>
            <th class="px-8 py-5 text-left">Tarjeta NFC y Saldo</th>
            <th class="px-8 py-5 text-right">Gestión</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="st in students" :key="st.id" class="hover:bg-blue-50/30 transition-colors group">
            <td class="px-8 py-6">
              <div class="flex items-center gap-4">
                  <div class="w-12 h-12 rounded-2xl bg-blue-100 flex items-center justify-center text-xl font-black text-blue-600">
                      {{ st.full_name.charAt(0) }}
                  </div>
                  <div>
                      <div class="text-sm font-black text-gray-800 leading-tight">{{ st.full_name }}</div>
                      <div class="text-[10px] font-bold text-primary uppercase tracking-tighter mt-1 bg-blue-50 px-2 py-0.5 rounded-md inline-block">Curso: {{ st.grade }}</div>
                  </div>
              </div>
            </td>
            <td class="px-8 py-6">
              <div class="text-xs font-bold text-gray-600 italic">
                  ID: {{ st.parent_id }}
              </div>
              <div class="text-[10px] text-gray-400 font-medium">Asociado vía Excel/Manual</div>
            </td>
            <td class="px-8 py-6">
                <!-- COLUMNA DINÁMICA DE TARJETA -->
                <div v-if="st.card" class="flex items-center gap-4">
                    <div class="bg-gray-900 text-white p-3 rounded-2xl shadow-lg border-2 border-gray-800 flex items-center gap-3">
                        <div class="text-xl">💳</div>
                        <div>
                            <p class="text-[9px] font-black uppercase opacity-50 leading-none">UID Asignado</p>
                            <p class="text-xs font-black font-mono tracking-tighter">{{ st.card.uid }}</p>
                        </div>
                    </div>
                    <div class="text-right">
                        <p class="text-[9px] font-black text-gray-400 uppercase">Saldo Actual</p>
                        <p class="text-sm font-black text-green-600">{{ formatMoney(st.card.balance) }}</p>
                    </div>
                </div>
                <div v-else class="text-red-400 text-[10px] font-black uppercase tracking-widest flex items-center gap-2">
                    <span class="w-2 h-2 rounded-full bg-red-400 animate-pulse"></span>
                    Pendiente de Vinculación
                </div>
            </td>
            <td class="px-8 py-6 text-right space-x-3">
                <button v-if="st.card" @click="unlinkStudentCard(st)" class="p-3 rounded-2xl bg-gray-100 text-gray-600 hover:bg-red-500 hover:text-white transition-all shadow-sm" title="Desvincular Tarjeta">🚫</button>
                <button @click="openCardModal(st)" class="p-3 rounded-2xl bg-gray-100 text-gray-600 hover:bg-primary hover:text-white transition-all shadow-sm" title="Link/Replace Card">
                    {{ st.card ? '🔄' : '💳' }}
                </button>
                <button @click="openStudentModal(st)" class="text-xs font-black text-gray-400 hover:text-primary uppercase tracking-widest">Editar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- MODAL 1: REGISTRO/EDICIÓN ESTUDIANTE -->
    <div v-if="showStudentModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-[40px] shadow-2xl max-w-md w-full p-8 border-4 border-gray-50">
        <h3 class="text-2xl font-black mb-6 tracking-tighter uppercase italic">{{ isEditing ? 'Actualizar Alumno' : 'Nuevo Alumno' }}</h3>
        <form @submit.prevent="saveStudent" class="space-y-4">
           <div>
             <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Nombre Completo</label>
             <input v-model="form.full_name" required type="text" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
           </div>
           <div class="grid grid-cols-2 gap-4">
               <div>
                 <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Grado / Curso</label>
                 <input v-model="form.grade" required type="text" placeholder="Ej: 11-A" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
               </div>
               <div>
                 <label class="text-[10px] font-black text-gray-400 uppercase ml-2">ID del Padre</label>
                 <input v-model.number="form.parent_id" required type="number" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
               </div>
           </div>
           
           <div class="flex gap-3 pt-6">
             <button type="button" @click="showStudentModal = false" class="flex-1 py-4 bg-gray-100 text-gray-500 rounded-2xl font-black uppercase text-xs tracking-widest">Cancelar</button>
             <button type="submit" class="flex-1 py-4 bg-primary text-white rounded-2xl font-black uppercase text-xs tracking-widest shadow-lg shadow-blue-100">Guardar Datos</button>
           </div>
        </form>
      </div>
    </div>

    <!-- MODAL 2: VINCULACIÓN / REEMPLAZO CON CONFIRMACIÓN -->
    <div v-if="showCardModal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-[50px] shadow-2xl p-10 max-w-sm w-full text-center border-8 border-gray-50 animate-scale-in">
        <div class="text-6xl mb-6">{{ isReplacement ? '🔄' : '💳' }}</div>
        <h3 class="text-2xl font-black uppercase tracking-tighter mb-2">
            {{ isReplacement ? 'Reemplazar Tarjeta' : 'Vincular Tarjeta' }}
        </h3>
        
        <div class="bg-blue-50 p-4 rounded-2xl mb-6">
            <p class="text-[10px] font-black text-blue-400 uppercase tracking-widest mb-1">Estudiante Destino</p>
            <p class="font-black text-blue-900">{{ selectedStudent?.full_name }}</p>
        </div>

        <!-- PASO 1: ESCANEO DE LA TARJETA -->
        <template v-if="!confirmStep">
            <p class="text-gray-500 text-sm font-medium mb-6 leading-tight">
                {{ isReplacement ? 'Acerque la NUEVA tarjeta NFC al lector ACR122U. El historial y el saldo se mantendrán intactos.' : 'Acerque la tarjeta NFC al lector ACR122U para leer su UID.' }}
            </p>

            <input 
              ref="cardInput" v-model="cardUid" @keyup.enter="handleCardAction"
              type="password" 
              class="w-full border-4 border-blue-100 bg-gray-50 rounded-3xl p-5 text-center text-3xl font-black text-primary outline-none focus:border-primary transition-all mb-4"
              placeholder="••••••"
            >
            
            <div v-if="cardError" class="text-red-500 text-xs font-black uppercase bg-red-50 p-3 rounded-xl mb-4 border border-red-100 animate-shake">
                ⚠️ {{ cardError }}
            </div>

            <div class="space-y-3">
                <button @click="handleCardAction" class="w-full bg-primary text-white py-5 rounded-3xl font-black uppercase tracking-widest shadow-xl shadow-blue-100 active:scale-95 transition-all">
                    Leer Tarjeta ➜
                </button>
                <button @click="showCardModal = false" class="w-full py-2 text-gray-400 font-bold uppercase text-[10px] tracking-widest hover:text-gray-600 transition-colors">Volver</button>
            </div>
        </template>

        <!-- PASO 2: CONFIRMACIÓN DEL UID LEÍDO -->
        <template v-else>
            <p class="text-gray-500 text-sm font-medium mb-4 leading-tight">
                Se leyó la siguiente tarjeta NFC. Verifique que sea la correcta antes de continuar.
            </p>

            <div class="bg-gray-900 text-white p-6 rounded-3xl shadow-lg border-2 border-gray-800 mb-6">
                <p class="text-[9px] font-black uppercase opacity-50 tracking-widest mb-1">UID Detectado</p>
                <p class="text-xl font-black font-mono tracking-tight break-all">{{ pendingUid }}</p>
            </div>

            <div class="space-y-3">
                <button @click="confirmCardLinking" :disabled="cardProcessing" class="w-full bg-green-500 hover:bg-green-600 text-white py-5 rounded-3xl font-black uppercase tracking-widest shadow-xl shadow-green-100 active:scale-95 transition-all">
                    ✓ SÍ, {{ isReplacement ? 'REEMPLAZAR' : 'VINCULAR' }}
                </button>
                <button @click="resetCardScan" class="w-full bg-gray-100 text-gray-600 py-3 rounded-2xl font-black uppercase text-xs tracking-widest hover:bg-gray-200 transition-colors">
                    ⟳ Leer Otra Tarjeta
                </button>
                <button @click="showCardModal = false" class="w-full py-2 text-gray-400 font-bold uppercase text-[10px] tracking-widest hover:text-gray-600 transition-colors">Cancelar</button>
            </div>
        </template>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';

const students = ref([]);
const loading = ref(false);
const showStudentModal = ref(false);
const isEditing = ref(false);
const form = reactive({ id: null, full_name: '', grade: '', parent_id: null });

// Lógica de Tarjetas
const showCardModal = ref(false);
const isReplacement = ref(false);
const selectedStudent = ref(null);
const cardUid = ref('');
const cardInput = ref(null);
const cardError = ref('');
const confirmStep = ref(false);
const pendingUid = ref('');

// Paginación y Búsqueda
const page = ref(1);
const limit = ref(10);
const searchQuery = ref('');
let searchTimer = null;

const loadData = async () => {
    loading.value = true;
    try {
        const skip = (page.value - 1) * limit.value;
        const { data } = await api.get('/students/', {
            params: { skip, limit: limit.value, search: searchQuery.value || undefined }
        });
        students.value = data;
    } catch (e) {
        console.error("Error cargando estudiantes:", e);
    } finally {
        loading.value = false;
    }
};

const handleSearch = () => {
    page.value = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
        // .trim() elimina espacios al inicio y final
        // .replace(/\s+/g, ' ') convierte múltiples espacios en uno solo
        const cleanQuery = searchQuery.value.trim().replace(/\s+/g, ' ');
        loadData(cleanQuery); 
    }, 500);
};

const nextPage = () => { page.value++; loadData(); };
const prevPage = () => { if(page.value > 1) { page.value--; loadData(); } };

// CRUD ESTUDIANTE
const openStudentModal = (student = null) => {
    if (student) {
        isEditing.value = true;
        Object.assign(form, { ...student });
    } else {
        isEditing.value = false;
        Object.assign(form, { id: null, full_name: '', grade: '', parent_id: null });
    }
    showStudentModal.value = true;
};

const saveStudent = async () => {
    try {
        if (isEditing.value) {
            await api.put(`/students/${form.id}`, form);
        } else {
            await api.post('/students/', form);
        }
        showStudentModal.value = false;
        loadData();
    } catch (e) {
        alert("Error al procesar la solicitud del estudiante");
    }
};

// LÓGICA DE TARJETA (LINK / REPLACE)
const openCardModal = (student) => {
    selectedStudent.value = student;
    cardUid.value = '';
    cardError.value = '';
    confirmStep.value = false;
    pendingUid.value = '';
    isReplacement.value = !!student.card; // Es reemplazo si ya tiene objeto tarjeta
    showCardModal.value = true;
    
    setTimeout(() => {
        if(cardInput.value) cardInput.value.focus();
    }, 200);
};

const cardProcessing = ref(false);

// PASO 1: Solo captura el UID leído y pide confirmación antes de enlazar
const handleCardAction = () => {
    if(!cardUid.value || cardProcessing.value) return;
    cardError.value = '';
    pendingUid.value = cardUid.value.trim().replace(/[:\s-]/g, '').toUpperCase();
    cardUid.value = '';
    confirmStep.value = true;
};

// PASO 2: El usuario confirmó el UID detectado; se realiza la operación real
const confirmCardLinking = async () => {
    if(!pendingUid.value || cardProcessing.value) return;
    cardProcessing.value = true;
    cardError.value = '';

    try {
        if (isReplacement.value) {
            // Reemplazo: Mantiene el registro de tarjeta pero cambia el UID físico
            await api.post('/cards/replace', {
                old_uid: selectedStudent.value.card.uid,
                new_uid: pendingUid.value
            });
            alert("✅ Tarjeta NFC reemplazada exitosamente. El saldo se ha preservado.");
        } else {
            // Vinculación Nueva
            await api.post('/cards/', {
                uid: pendingUid.value,
                student_id: selectedStudent.value.id,
                daily_limit: 50000 // Valor por defecto
            });
            alert("✅ Tarjeta NFC vinculada al estudiante correctamente.");
        }
        showCardModal.value = false;
        loadData();
    } catch (error) {
        cardError.value = error.response?.data?.detail || "No se pudo procesar la tarjeta NFC";
        resetCardScan();
    } finally {
        cardProcessing.value = false;
    }
};

// Volver al paso de escaneo (p. ej. si se leyó una tarjeta equivocada)
const resetCardScan = () => {
    confirmStep.value = false;
    pendingUid.value = '';
    cardUid.value = '';
    cardError.value = '';
    setTimeout(() => {
        if(cardInput.value) cardInput.value.focus();
    }, 200);
};

// Desvincular la tarjeta del estudiante
const unlinkStudentCard = async (student) => {
    if(!student.card) return;
    if(!confirm(`¿Estás seguro de que deseas DESVINCULAR la tarjeta ${student.card.uid} de ${student.full_name}?\n\nEl saldo y el historial se conservan y la tarjeta quedará inactiva.`)) return;
    try {
        await api.post('/cards/unlink', { card_uid: student.card.uid });
        alert("✅ Tarjeta desvinculada del estudiante.");
        student.card = null;
    } catch (e) {
        alert(e.response?.data?.detail || "Error al desvincular la tarjeta");
    }
};

onMounted(loadData);
</script>

<style scoped>
.animate-scale-in { animation: scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
.animate-shake { animation: shake 0.2s ease-in-out 0s 2; }

/* Scrollbar personalizada para la tabla */
.custom-scrollbar::-webkit-scrollbar { height: 6px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }
</style>