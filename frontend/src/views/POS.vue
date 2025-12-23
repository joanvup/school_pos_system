<template>
  <div class="flex flex-col h-full gap-6 lg:flex-row p-2 overflow-hidden">
    
    <!-- COLUMNA IZQUIERDA: MENÚ DINÁMICO -->
    <div class="flex-1 flex flex-col min-h-0 space-y-4">
      
      <!-- CABECERA Y BUSCADOR -->
      <div class="flex flex-col md:flex-row justify-between items-center gap-4">
        <h2 class="text-2xl font-black text-gray-800 uppercase tracking-tighter italic">Venta Directa</h2>
        <div class="relative w-full md:w-72">
            <span class="absolute left-4 top-3 text-gray-400">🔍</span>
            <input 
                v-model="search" 
                type="text" 
                placeholder="Buscar por nombre..." 
                class="w-full pl-10 pr-4 py-3 bg-white border-2 border-gray-100 rounded-2xl shadow-sm outline-none focus:border-primary transition-all font-medium"
            >
        </div>
      </div>

      <!-- BARRA DE CATEGORÍAS (TABS) -->
      <div class="flex gap-2 overflow-x-auto pb-2 no-scrollbar scroll-smooth">
        <button 
          v-for="cat in categoryTabs" 
          :key="cat"
          @click="activeCategory = cat"
          :class="[
            'px-6 py-3 rounded-2xl font-black text-xs uppercase tracking-widest transition-all whitespace-nowrap border-2',
            activeCategory === cat 
              ? 'bg-primary border-primary text-white shadow-lg shadow-blue-100' 
              : 'bg-white border-gray-100 text-gray-400 hover:border-gray-200'
          ]"
        >
          {{ cat }}
        </button>
      </div>
      
      <!-- GRILLA DE PRODUCTOS (ÁREA DINÁMICA) -->
      <div class="flex-1 overflow-y-auto min-h-0 pr-2 custom-scrollbar">
        <div v-if="filteredProducts.length > 0" class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4 pb-6">
            <div 
                v-for="product in filteredProducts" :key="product.id" 
                @click="addToCart(product)"
                class="bg-white p-4 rounded-[32px] shadow-sm border-2 border-transparent hover:border-primary hover:shadow-xl cursor-pointer transition-all group active:scale-95 flex flex-col items-center justify-between h-56"
            >
                <!-- Foto o Icono -->
                <div class="h-24 w-24 rounded-3xl mb-2 flex items-center justify-center text-5xl group-hover:scale-110 transition-transform overflow-hidden bg-gray-50 border border-gray-50">
                    <img v-if="product.image_url" :src="baseUrl + product.image_url" class="h-full w-full object-cover">
                    <span v-else>{{ getCategoryIcon(product.category_rel?.name) }}</span>
                </div>

                <div class="text-center">
                    <h3 class="font-bold text-gray-800 text-sm leading-tight line-clamp-2 px-1 mb-1">{{ product.name }}</h3>
                    <p class="text-primary font-black text-lg">{{ formatMoney(product.price) }}</p>
                </div>
                
                <div class="w-full px-4">
                    <div class="text-[9px] bg-blue-50 text-blue-500 rounded-full font-black uppercase text-center py-1">
                        Stock: {{ product.stock }}
                    </div>
                </div>
            </div>
        </div>
        <div v-else class="h-full flex flex-col items-center justify-center text-gray-300">
            <div class="text-6xl mb-4">🏜️</div>
            <p class="font-black uppercase tracking-widest text-sm">No hay productos en esta sección</p>
        </div>
      </div>

      <!-- PANEL DE VENTAS RECIENTES (SIEMPRE VISIBLE ABAJO) -->
      <div class="bg-gray-50 rounded-[32px] p-6 border-2 border-gray-100 h-48 flex flex-col">
        <div class="flex justify-between items-center mb-3">
            <h3 class="text-[10px] font-black text-gray-400 uppercase tracking-widest">Últimas 5 Ventas</h3>
            <span class="w-2 h-2 rounded-full bg-green-500 animate-ping"></span>
        </div>
        <div class="flex-1 overflow-y-auto space-y-2 pr-2">
            <div v-for="sale in recentSales" :key="sale.id" class="flex justify-between items-center bg-white p-3 rounded-2xl shadow-sm border border-gray-100 text-xs">
                <div class="flex items-center gap-3">
                    <div class="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center font-bold text-blue-600">
                        {{ sale.comprador.charAt(0) }}
                    </div>
                    <div>
                        <p class="font-black text-gray-700">{{ sale.comprador }}</p>
                        <p class="text-[9px] text-gray-400">{{ new Date(sale.timestamp).toLocaleTimeString() }}</p>
                    </div>
                </div>
                <div class="flex items-center gap-4">
                    <span :class="sale.status === 'reversed' ? 'line-through text-red-300' : 'text-primary font-black'">
                        {{ formatMoney(sale.amount) }}
                    </span>
                    <button v-if="authStore.isAdmin && sale.status !== 'reversed'" @click="handleReverse(sale.id)" class="bg-red-50 text-red-600 px-3 py-1 rounded-xl font-bold hover:bg-red-600 hover:text-white transition-colors">
                        ANULAR
                    </button>
                    <span v-if="sale.status === 'reversed'" class="text-[9px] font-black text-red-500 uppercase italic">Anulada</span>
                </div>
            </div>
        </div>
      </div>
    </div>

    <!-- COLUMNA DERECHA: TICKET DE VENTA -->
    <div class="w-full lg:w-[400px] flex flex-col min-h-0">
        <div class="bg-gray-900 text-white rounded-[40px] shadow-2xl flex flex-col h-full border-4 border-gray-800 overflow-hidden">
            <div class="p-8 border-b border-white/5">
                <h2 class="text-2xl font-black uppercase italic tracking-tighter">Mi Carrito</h2>
                <p class="text-xs text-gray-500 font-bold mt-1 uppercase">{{ cart.length }} Items seleccionados</p>
            </div>

            <div class="flex-1 overflow-y-auto p-8 space-y-6 custom-scrollbar-dark">
                <div v-if="cart.length === 0" class="h-full flex flex-col items-center justify-center opacity-20">
                    <div class="text-8xl mb-4">🛒</div>
                    <p class="font-black uppercase tracking-widest text-sm">Venta Vacía</p>
                </div>
                <div v-for="(item, index) in cart" :key="item.product.id" class="flex justify-between items-center group">
                    <div class="flex-1">
                        <div class="font-black text-sm text-gray-200 group-hover:text-primary transition-colors">{{ item.product.name }}</div>
                        <div class="text-[10px] text-gray-500 font-bold uppercase">{{ formatMoney(item.product.price) }} x {{ item.quantity }}</div>
                    </div>
                    <div class="text-right flex flex-col items-end">
                        <div class="font-black text-lg text-white">{{ formatMoney(item.product.price * item.quantity) }}</div>
                        <button @click="removeFromCart(index)" class="text-[9px] text-red-500 font-black uppercase hover:bg-red-500/10 px-2 py-1 rounded-lg mt-1">Borrar</button>
                    </div>
                </div>
            </div>

            <div class="p-8 bg-white/5 rounded-b-[40px] border-t border-white/10 space-y-6">
                <div class="flex justify-between items-end">
                    <span class="text-gray-500 text-xs font-black uppercase tracking-widest">Total Orden</span>
                    <span class="text-5xl font-black text-primary leading-none">{{ formatMoney(total) }}</span>
                </div>
                <button 
                    @click="startCheckout" :disabled="cart.length === 0"
                    class="w-full bg-primary hover:bg-blue-600 text-white py-6 rounded-[28px] font-black text-2xl shadow-2xl shadow-blue-900/40 transition-all active:scale-95 disabled:opacity-20 disabled:grayscale"
                >
                    PAGAR (F2)
                </button>
            </div>
        </div>
    </div>

    <!-- MODAL DE COBRO (Ya optimizado para Touch) -->
    <div v-if="showModal" class="fixed inset-0 bg-black/90 backdrop-blur-md flex items-center justify-center z-[9999] p-4">
      <div class="bg-white rounded-[50px] shadow-2xl p-10 max-w-md w-full text-center relative border-8 border-gray-100">
        
        <div v-if="!stepIdentified" class="space-y-8 py-10">
            <div class="text-8xl animate-pulse">💳</div>
            <div>
                <h3 class="text-4xl font-black text-gray-900 tracking-tighter uppercase italic">Esperando Pago</h3>
                <p class="text-gray-400 font-bold mt-2 uppercase text-xs tracking-widest">Pase la tarjeta por el lector</p>
            </div>
            
            <input 
                ref="rfidInput" v-model="rfidCode" @keyup.enter="identifyCard" type="password" 
                class="w-full border-4 border-blue-100 bg-gray-50 rounded-3xl p-6 text-center text-4xl font-black text-primary outline-none focus:border-primary transition-all"
                placeholder="••••••"
            >

            <button @click="closeModal" class="w-full py-5 bg-red-50 text-red-600 rounded-3xl font-black text-sm uppercase tracking-widest hover:bg-red-100 transition-colors">
                ❌ Cancelar Orden
            </button>
        </div>

        <div v-else class="space-y-6">
            <div class="bg-primary text-white p-8 rounded-[40px] shadow-xl">
                <p class="text-[10px] font-black uppercase tracking-widest opacity-60 mb-2">Comprador Confirmado</p>
                <h4 class="text-3xl font-black leading-tight">{{ cardHolder.name }}</h4>
                <p class="text-xs font-bold opacity-80 mt-2 uppercase tracking-wider">{{ cardHolder.type }}</p>
            </div>

            <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 p-5 rounded-3xl border-2 border-gray-100">
                    <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">Tu Saldo</p>
                    <p class="text-xl font-black" :class="cardHolder.balance < total ? 'text-red-500' : 'text-green-600'">
                        {{ formatMoney(cardHolder.balance) }}
                    </p>
                </div>
                <div class="bg-gray-50 p-5 rounded-3xl border-2 border-gray-100">
                    <p class="text-[10px] font-black text-gray-400 uppercase tracking-widest mb-1">A Pagar</p>
                    <p class="text-xl font-black text-gray-900">{{ formatMoney(total) }}</p>
                </div>
            </div>

            <div v-if="errorMessage || cardHolder.balance < total" class="bg-red-600 text-white p-5 rounded-[28px] text-sm font-black shadow-xl animate-bounce">
                ⚠️ {{ errorMessage || 'SALDO INSUFICIENTE' }}
            </div>

            <div class="flex flex-col gap-3 pt-4">
                <button 
                    @click="confirmPayment" :disabled="processing || cardHolder.balance < total"
                    class="w-full bg-green-500 text-white py-8 rounded-[35px] font-black text-3xl hover:bg-green-600 shadow-2xl transition-all active:scale-95 disabled:opacity-20 disabled:grayscale"
                >
                    {{ processing ? '...' : 'PAGAR AHORA' }}
                </button>
                <div class="grid grid-cols-2 gap-3">
                    <button @click="resetModal" class="bg-amber-100 text-amber-700 py-4 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-amber-200">🔄 Otra Tarjeta</button>
                    <button @click="closeModal" class="bg-gray-100 text-gray-500 py-4 rounded-2xl font-black text-[10px] uppercase tracking-widest hover:bg-gray-200">🚫 Salir</button>
                </div>
            </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue';
import api from '../api/axios';
import { useAuthStore } from '../stores/auth';
import { formatMoney } from '../utils/formatters';
const configStore = useConfigStore();

const baseUrl = configStore.baseUrl;

const authStore = useAuthStore();
const products = ref([]);
const recentSales = ref([]);
const cart = ref([]);
const search = ref('');
const loading = ref(true);

const activeCategory = ref('Todas');

// Modal States
const showModal = ref(false);
const stepIdentified = ref(false);
const rfidCode = ref('');
const rfidInput = ref(null);
const cardHolder = ref(null);
const processing = ref(false);
const errorMessage = ref('');

const loadPOSData = async () => {
    loading.value = true;
    try {
        const [resP, resS] = await Promise.all([
            api.get('/products/'),
            api.get('/sales/recent')
        ]);
        products.value = resP.data;
        recentSales.value = resS.data;
    } catch (e) { console.error(e); } 
    finally { loading.value = false; }
};

// --- LÓGICA DE PESTAÑAS Y FILTRADO ---
const categoryTabs = computed(() => {
    const cats = new Set(products.value.map(p => p.category_rel?.name || 'General'));
    return ['Todas', ...Array.from(cats).sort()];
});

const filteredProducts = computed(() => {
    if (!products.value) return [];
    
    return products.value.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(search.value.toLowerCase());
        const matchesCategory = activeCategory.value === 'Todas' || p.category_rel?.name === activeCategory.value;
        return matchesSearch && matchesCategory && p.is_active && p.stock > 0;
    });
});

const getCategoryIcon = (cat) => {
    const icons = { 'Bebidas': '🥤', 'Comida Caliente': '🍕', 'Paquetes': '🍟', 'Papelería': '✏️', 'Dulcería': '🍭' };
    return icons[cat] || '🍔';
};

const addToCart = (product) => {
    const existing = cart.value.find(i => i.product.id === product.id);
    if(existing) {
        if(existing.quantity >= product.stock) return alert("Sin más stock");
        existing.quantity++;
    } else {
        cart.value.push({ product, quantity: 1 });
    }
};

const removeFromCart = (index) => cart.value.splice(index, 1);
const total = computed(() => cart.value.reduce((s, i) => s + (i.product.price * i.quantity), 0));

const startCheckout = () => {
    errorMessage.value = ''; rfidCode.value = ''; stepIdentified.value = false; showModal.value = true;
    setTimeout(() => rfidInput.value?.focus(), 150);
};

const closeModal = () => { showModal.value = false; stepIdentified.value = false; rfidCode.value = ''; };
const resetModal = () => { stepIdentified.value = false; rfidCode.value = ''; errorMessage.value = ''; setTimeout(() => rfidInput.value?.focus(), 100); };

const identifyCard = async () => {
    if (!rfidCode.value) return;
    try {
        const { data } = await api.get(`/cards/check/${rfidCode.value}`);
        cardHolder.value = {
            uid: data.uid,
            name: data.owner_name,
            type: data.owner_type,
            balance: data.balance
        };
        stepIdentified.value = true;
    } catch (e) {
        alert("Tarjeta no reconocida");
        rfidCode.value = '';
        setTimeout(() => rfidInput.value?.focus(), 100);
    }
};

const confirmPayment = async () => {
    processing.value = true; errorMessage.value = '';
    try {
        await api.post('/sales/', {
            card_uid: cardHolder.value.uid,
            items: cart.value.map(i => ({ product_id: i.product.id, quantity: i.quantity }))
        });
        cart.value = []; closeModal(); loadPOSData();
        alert("✅ Cobro completado");
    } catch (e) {
        errorMessage.value = e.response?.data?.detail || "Error";
    } finally { processing.value = false; }
};

const handleReverse = async (id) => {
    if(!confirm("¿Reversar venta?")) return;
    try {
        await api.post(`/sales/reverse/${id}`);
        loadPOSData();
    } catch (e) { alert(e.response?.data?.detail); }
};

onMounted(loadPOSData);
</script>

<style scoped>
.no-scrollbar::-webkit-scrollbar { display: none; }
.no-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }

.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
.custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

.custom-scrollbar-dark::-webkit-scrollbar { width: 4px; }
.custom-scrollbar-dark::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
.custom-scrollbar-dark::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
</style>