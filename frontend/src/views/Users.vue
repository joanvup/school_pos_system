<template>
  <div class="space-y-6">
    <!-- CABECERA -->
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <h1 class="text-2xl font-black text-gray-800 uppercase tracking-tighter italic">Gestión de Usuarios</h1>
      <button @click="openUserModal()" class="bg-primary hover:bg-blue-600 text-white px-6 py-3 rounded-2xl shadow-lg shadow-blue-100 font-bold transition-all active:scale-95">
        + Nuevo Usuario
      </button>
    </div>

    <!-- BARRA DE BÚSQUEDA Y PAGINACIÓN -->
    <div class="bg-white p-4 rounded-3xl shadow-sm border border-gray-100 flex flex-col md:flex-row gap-4 items-center justify-between">
        <div class="relative w-full md:w-96">
            <span class="absolute left-4 top-3 text-gray-400">🔍</span>
            <input 
                v-model="searchQuery" @input="handleSearch" type="text" 
                placeholder="Buscar por nombre o email..." 
                class="w-full pl-10 pr-4 py-2 bg-gray-50 border-2 border-gray-50 rounded-xl focus:border-primary outline-none transition-all"
            >
        </div>
        <div class="flex items-center gap-4 bg-gray-50 p-1 rounded-xl border">
            <button @click="prevPage" :disabled="page === 1" class="px-4 py-1 rounded-lg hover:bg-white disabled:opacity-30 font-bold text-gray-500">◀</button>
            <span class="text-xs font-black text-primary uppercase tracking-widest">Pág. {{ page }}</span>
            <button @click="nextPage" :disabled="users.length < limit" class="px-4 py-1 rounded-lg hover:bg-white disabled:opacity-30 font-bold text-gray-500">▶</button>
        </div>
    </div>

    <!-- TABLA DE USUARIOS -->
    <div class="bg-white rounded-[32px] shadow-sm border border-gray-100 overflow-hidden">
      <table class="min-w-full divide-y divide-gray-100">
        <thead class="bg-gray-50">
          <tr class="text-[10px] font-black text-gray-400 uppercase tracking-widest">
            <th class="px-6 py-4 text-left">Información Personal</th>
            <th class="px-6 py-4 text-left">Rol</th>
            <th class="px-6 py-4 text-left">Tarjeta RFID / Saldo</th>
            <th class="px-6 py-4 text-right">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50 transition-colors">
            <td class="px-6 py-4">
              <div class="text-sm font-black text-gray-800">{{ user.full_name }}</div>
              <div class="text-xs text-gray-400 font-medium">{{ user.email }}</div>
            </td>
            <td class="px-6 py-4">
               <span class="px-3 py-1 text-[10px] font-black rounded-full uppercase tracking-tighter"
                :class="{
                    'bg-purple-100 text-purple-600': user.role === 'admin',
                    'bg-blue-100 text-blue-600': user.role === 'padre',
                    'bg-green-100 text-green-600': user.role === 'vendedor',
                    'bg-yellow-100 text-yellow-600': user.role === 'supervisor',
                    'bg-gray-100 text-gray-600': user.role === 'empleado'
                }">
                {{ user.role }}
               </span>
            </td>
            <td class="px-6 py-4">
                <!-- COLUMNA DINÁMICA DE TARJETA -->
                <div v-if="user.role === 'padre'" class="text-gray-300 text-xs italic">N/A</div>
                <div v-else class="flex items-center gap-3">
                    <div v-if="user.card" class="group flex items-center gap-2">
                        <div class="flex flex-col">
                            <span class="text-xs font-black text-blue-600 font-mono">{{ user.card.uid }}</span>
                            <span class="text-[10px] font-bold text-green-600">{{ formatMoney(user.card.balance) }}</span>
                        </div>
                        <button @click="openCardModal(user)" class="p-1 bg-gray-100 rounded-lg hover:bg-orange-100 text-orange-500 transition-colors" title="Reemplazar Tarjeta">
                            🔄
                        </button>
                    </div>
                    <button v-else @click="openCardModal(user)" class="text-[10px] font-black text-primary border-2 border-primary/20 px-3 py-1 rounded-xl hover:bg-primary hover:text-white transition-all uppercase tracking-widest">
                        💳 Vincular
                    </button>
                </div>
            </td>
            <td class="px-6 py-4 text-right">
              <button @click="openUserModal(user)" class="text-xs font-black text-gray-400 hover:text-primary uppercase tracking-widest">Editar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- MODAL 1: USUARIO (PERFIL) -->
    <div v-if="showUserModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-[40px] shadow-2xl max-w-md w-full p-8 border-4 border-gray-50">
        <h3 class="text-2xl font-black mb-6 tracking-tighter uppercase italic">{{ isEditing ? 'Editar Perfil' : 'Nuevo Usuario' }}</h3>
        <form @submit.prevent="saveUser" class="space-y-4">
           <div>
             <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Nombre Completo</label>
             <input v-model="form.full_name" required type="text" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
           </div>
           <div>
             <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Correo Institucional</label>
             <input v-model="form.email" required type="email" :disabled="isEditing" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold disabled:opacity-50">
           </div>
           <div>
             <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Rol de Acceso</label>
             <select v-model="form.role" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl font-bold outline-none focus:border-primary">
                <option value="padre">Padre de Familia</option>
                <option value="empleado">Empleado / Staff</option>
                <option value="vendedor">Vendedor / Cajero</option>
                <option value="supervisor">Supervisor de Inventario</option>
                <option value="admin">Administrador Total</option>
             </select>
           </div>
           <div>
             <label class="text-[10px] font-black text-gray-400 uppercase ml-2">Contraseña</label>
             <input v-model="form.password" :required="!isEditing" type="password" :placeholder="isEditing ? '••••••••' : ''" class="w-full mt-1 p-3 bg-gray-50 border-2 border-gray-100 rounded-2xl outline-none focus:border-primary font-bold">
           </div>
           
           <div class="flex gap-3 pt-6">
             <button type="button" @click="showUserModal = false" class="flex-1 py-4 bg-gray-100 text-gray-500 rounded-2xl font-black uppercase text-xs tracking-widest">Cancelar</button>
             <button type="submit" class="flex-1 py-4 bg-primary text-white rounded-2xl font-black uppercase text-xs tracking-widest shadow-lg shadow-blue-100">Guardar</button>
           </div>
        </form>
      </div>
    </div>

    <!-- MODAL 2: VINCULACIÓN / REEMPLAZO DE TARJETA -->
    <div v-if="showCardModal" class="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-[50px] shadow-2xl p-10 max-w-sm w-full text-center border-8 border-gray-50 animate-scale-in">
        <div class="text-6xl mb-6">{{ isReplacement ? '🔄' : '💳' }}</div>
        <h3 class="text-2xl font-black uppercase tracking-tighter mb-2">
            {{ isReplacement ? 'Reemplazar Tarjeta' : 'Vincular Tarjeta' }}
        </h3>
        <p class="text-gray-500 text-sm font-medium mb-8">
            {{ isReplacement ? 'La tarjeta anterior será anulada y el saldo pasará a la nueva.' : 'Acerque la tarjeta física al lector ahora.' }}
        </p>
        
        <div class="mb-6">
            <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-2">Usuario Destino</p>
            <p class="font-black text-gray-800">{{ selectedUser?.full_name }}</p>
        </div>

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
            <button @click="handleCardAction" class="w-full bg-primary text-white py-4 rounded-2xl font-black uppercase tracking-widest shadow-lg active:scale-95 transition-all">
                {{ isReplacement ? 'Confirmar Reemplazo' : 'Vincular Tarjeta' }}
            </button>
            <button @click="showCardModal = false" class="w-full py-2 text-gray-400 font-bold uppercase text-[10px] tracking-widest">Cerrar</button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, reactive } from 'vue';
import api from '../api/axios';
import { formatMoney } from '../utils/formatters';

const users = ref([]);
const loading = ref(false);
const showUserModal = ref(false);
const isEditing = ref(false);
const form = reactive({});

// Lógica de Tarjetas
const showCardModal = ref(false);
const isReplacement = ref(false);
const selectedUser = ref(null);
const cardUid = ref('');
const cardInput = ref(null);
const cardError = ref('');

// Paginación y Búsqueda
const page = ref(1);
const limit = ref(10);
const searchQuery = ref('');
let searchTimer = null;

const loadUsers = async () => {
    loading.value = true;
    try {
        const skip = (page.value - 1) * limit.value;
        const { data } = await api.get('/users/', {
            params: { skip, limit: limit.value, search: searchQuery.value || undefined }
        });
        users.value = data;
    } catch (e) { console.error(e); } 
    finally { loading.value = false; }
};

const handleSearch = () => {
    page.value = 1;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadUsers, 500);
};

const nextPage = () => { page.value++; loadUsers(); };
const prevPage = () => { if(page.value > 1) { page.value--; loadUsers(); } };

// CRUD USUARIO
const openUserModal = (user = null) => {
    if (user) {
        isEditing.value = true;
        Object.assign(form, { ...user, password: '' });
    } else {
        isEditing.value = false;
        Object.assign(form, { full_name: '', email: '', role: 'vendedor', password: '', is_active: true });
    }
    showUserModal.value = true;
};

const saveUser = async () => {
    try {
        if (isEditing.value) {
            const payload = { ...form };
            if (!payload.password) delete payload.password;
            await api.put(`/users/${form.id}`, payload);
        } else {
            await api.post('/users/', form);
        }
        showUserModal.value = false;
        loadUsers();
    } catch (e) { alert("Error al guardar usuario"); }
};

// LÓGICA DE ASIGNACIÓN/REEMPLAZO DE TARJETA
const openCardModal = (user) => {
    selectedUser.value = user;
    cardUid.value = '';
    cardError.value = '';
    // Detectamos si es reemplazo
    isReplacement.value = !!user.card;
    showCardModal.value = true;
    
    setTimeout(() => {
        if(cardInput.value) cardInput.value.focus();
    }, 200);
};

const handleCardAction = async () => {
    if(!cardUid.value) return;
    cardError.value = '';

    try {
        if (isReplacement.value) {
            // Caso 1: Reemplazo (POST /cards/replace)
            await api.post('/cards/replace', {
                old_uid: selectedUser.value.card.uid,
                new_uid: cardUid.value
            });
            alert("✅ Tarjeta reemplazada. El saldo se mantuvo en la nueva cuenta.");
        } else {
            // Caso 2: Vinculación Nueva (POST /cards/)
            await api.post('/cards/', {
                uid: cardUid.value,
                user_id: selectedUser.value.id,
                daily_limit: 100000
            });
            alert("✅ Nueva tarjeta vinculada exitosamente.");
        }
        showCardModal.value = false;
        loadUsers();
    } catch (error) {
        cardError.value = error.response?.data?.detail || "Error en la operación";
        cardUid.value = '';
        cardInput.value?.focus();
    }
};

onMounted(loadUsers);
</script>

<style scoped>
.animate-scale-in { animation: scaleIn 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
@keyframes scaleIn { from { opacity: 0; transform: scale(0.9); } to { opacity: 1; transform: scale(1); } }
@keyframes shake { 0%, 100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
.animate-shake { animation: shake 0.2s ease-in-out 0s 2; }
</style>