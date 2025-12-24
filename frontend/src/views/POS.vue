<template>
  <!-- Contenedor Principal: Ajuste de altura dinámico para móviles -->
  <div class="flex flex-col h-[calc(100vh-80px)] md:h-full gap-4 lg:flex-row p-1 md:p-2 overflow-hidden relative">
    
    <!-- COLUMNA IZQUIERDA: MENÚ DE PRODUCTOS -->
    <div class="flex-1 flex flex-col min-h-0 space-y-3 md:space-y-4">
      
      <!-- CABECERA: Buscador compacto en móvil -->
      <div class="flex flex-col sm:flex-row justify-between items-center gap-2 px-2">
        <h2 class="hidden sm:block text-xl font-black text-gray-800 uppercase italic">Venta</h2>
        <div class="relative w-full sm:w-64">
            <span class="absolute left-3 top-2.5 text-gray-400 text-sm">🔍</span>
            <input 
                v-model="search" 
                type="text" 
                placeholder="Buscar..." 
                class="w-full pl-9 pr-4 py-2 bg-white border-2 border-gray-100 rounded-xl shadow-sm outline-none focus:border-primary transition-all text-sm"
            >
        </div>
      </div>

      <!-- TABS DE CATEGORÍAS: Scroll horizontal táctil -->
      <div class="flex gap-2 overflow-x-auto px-2 pb-1 no-scrollbar">
        <button 
          v-for="cat in categoryTabs" 
          :key="cat"
          @click="activeCategory = cat"
          :class="[
            'px-4 py-2 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all whitespace-nowrap border-2',
            activeCategory === cat 
              ? 'bg-primary border-primary text-white shadow-md' 
              : 'bg-white border-gray-100 text-gray-400'
          ]"
        >
          {{ cat }}
        </button>
      </div>
      
      <!-- GRILLA DE PRODUCTOS: Optimizada para pulgares -->
      <div class="flex-1 overflow-y-auto min-h-0 px-2 custom-scrollbar">
        <div v-if="filteredProducts.length > 0" class="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-4 gap-3 md:gap-4 pb-24 lg:pb-6">
            <div 
                v-for="product in filteredProducts" :key="product.id" 
                @click="addToCart(product)"
                class="bg-white p-3 md:p-4 rounded-[24px] md:rounded-[32px] shadow-sm border-2 border-transparent hover:border-primary active:scale-95 transition-all flex flex-col items-center justify-between h-48 md:h-56"
            >
                <div class="h-16 w-16 md:h-24 md:w-24 rounded-2xl md:rounded-3xl mb-1 flex items-center justify-center text-3xl md:text-5xl overflow-hidden bg-gray-50">
                    <img v-if="product.image_url" :src="configStore.baseUrl + product.image_url" class="h-full w-full object-cover">
                    <span v-else>{{ getCategoryIcon(product.category_rel?.name) }}</span>
                </div>

                <div class="text-center w-full">
                    <h3 class="font-bold text-gray-800 text-xs md:text-sm leading-tight line-clamp-2 px-1">{{ product.name }}</h3>
                    <p class="text-primary font-black text-sm md:text-lg">{{ formatMoney(product.price) }}</p>
                </div>
                
                <div class="w-full">
                    <div class="text-[8px] md:text-[9px] bg-blue-50 text-blue-500 rounded-full font-black uppercase text-center py-0.5">
                        Stock: {{ product.stock }}
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Estado Vacío -->
        <div v-else class="h-full flex flex-col items-center justify-center text-gray-300">
            <div class="text-4xl mb-2">🏜️</div>
            <p class="font-black uppercase tracking-widest text-[10px]">Sin productos</p>
        </div>
      </div>

      <!-- VENTAS RECIENTES: Ocultas en móvil para ganar espacio, visibles en PC -->
      <div class="hidden lg:flex bg-gray-50 rounded-[32px] p-4 border-2 border-gray-100 h-40 flex-col">
        <h3 class="text-[9px] font-black text-gray-400 uppercase tracking-widest mb-2">Ventas del momento</h3>
        <div class="flex-1 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
            <div v-for="sale in recentSales" :key="sale.id" class="flex justify-between items-center bg-white p-2 rounded-xl shadow-sm border border-gray-100 text-[10px]">
                <span class="font-black text-gray-700 truncate w-32">{{ sale.comprador }}</span>
                <span :class="sale.status === 'reversed' ? 'line-through text-red-300' : 'text-primary font-black'">
                    {{ formatMoney(sale.amount) }}
                </span>
            </div>
        </div>
      </div>
    </div>

    <!-- BOTÓN FLOTANTE MÓVIL (Muestra total y abre carrito) -->
    <div class="lg:hidden fixed bottom-6 left-1/2 -translate-x-1/2 z-30 w-[90%] max-w-sm">
        <button 
            @click="isMobileCartOpen = true"
            class="w-full bg-gray-900 text-white p-4 rounded-[24px] shadow-2xl flex justify-between items-center border-2 border-white/10"
        >
            <div class="flex items-center gap-3">
                <span class="bg-primary text-white w-8 h-8 rounded-full flex items-center justify-center font-black text-sm">{{ cart.length }}</span>
                <span class="font-black uppercase text-xs tracking-widest">Ver Pedido</span>
            </div>
            <span class="text-xl font-black text-primary">{{ formatMoney(total) }}</span>
        </button>
    </div>

    <!-- COLUMNA DERECHA / CARRITO: En móvil es un Modal/Overlay -->
    <div 
        :class="[
            'w-full lg:w-[380px] flex flex-col fixed inset-0 z-[100] lg:relative lg:inset-auto lg:z-auto transition-transform duration-300',
            isMobileCartOpen ? 'translate-y-0' : 'translate-y-full lg:translate-y-0'
        ]"
    >
        <div class="bg-gray-900 text-white rounded-t-[40px] lg:rounded-[40px] shadow-2xl flex flex-col h-full border-t-4 lg:border-4 border-gray-800">
            <!-- Header Carrito -->
            <div class="p-6 flex justify-between items-center border-b border-white/5">
                <div>
                    <h2 class="text-xl font-black uppercase italic tracking-tighter">Mi Carrito</h2>
                    <p class="text-[10px] text-gray-500 font-bold uppercase">{{ cart.length }} productos</p>
                </div>
                <button @click="isMobileCartOpen = false" class="lg:hidden text-gray-400 text-2xl">✕</button>
            </div>

            <!-- Items -->
            <div class="flex-1 overflow-y-auto p-6 space-y-4 custom-scrollbar-dark">
                <div v-for="(item, index) in cart" :key="item.product.id" class="flex justify-between items-center bg-white/5 p-3 rounded-2xl">
                    <div class="flex-1">
                        <div class="font-black text-xs text-gray-100">{{ item.product.name }}</div>
                        <div class="text-[10px] text-gray-500 font-bold uppercase">{{ formatMoney(item.product.price) }} x {{ item.quantity }}</div>
                    </div>
                    <div class="text-right flex items-center gap-3">
                        <div class="font-black text-sm text-primary">{{ formatMoney(item.product.price * item.quantity) }}</div>
                        <button @click="removeFromCart(index)" class="text-red-500 bg-red-500/10 w-8 h-8 rounded-full flex items-center justify-center font-bold">✕</button>
                    </div>
                </div>
            </div>

            <!-- Footer Carrito -->
            <div class="p-6 bg-white/5 rounded-b-[40px] border-t border-white/10 space-y-4">
                <div class="flex justify-between items-end">
                    <span class="text-gray-500 text-[10px] font-black uppercase tracking-widest">Total</span>
                    <span class="text-3xl md:text-4xl font-black text-primary">{{ formatMoney(total) }}</span>
                </div>
                <button 
                    @click="startCheckout" :disabled="cart.length === 0"
                    class="w-full bg-primary hover:bg-blue-600 text-white py-4 md:py-5 rounded-[24px] font-black text-lg md:text-xl shadow-xl transition-all active:scale-95 disabled:opacity-20"
                >
                    COBRAR (F2)
                </button>
            </div>
        </div>
    </div>

    <!-- MODAL DE COBRO (Igual que el anterior pero con z-index mayor) -->
    <div v-if="showModal" class="fixed inset-0 bg-black/95 backdrop-blur-md flex items-center justify-center z-[200] p-4">
        <!-- ... (Contenido del modal de la respuesta anterior, se mantiene intacto) ... -->
        <div class="bg-white rounded-[40px] shadow-2xl p-6 md:p-10 max-w-md w-full text-center relative border-4 md:border-8 border-gray-100">
            <div v-if="!stepIdentified" class="space-y-6">
                <div class="text-6xl animate-pulse">💳</div>
                <h3 class="text-2xl font-black text-gray-900 tracking-tighter uppercase italic">Esperando Tarjeta</h3>
                <input ref="rfidInput" v-model="rfidCode" @keyup.enter="identifyCard" type="password" class="w-full border-4 border-blue-100 bg-gray-50 rounded-2xl p-4 text-center text-2xl font-black text-primary outline-none" placeholder="••••••">
                <button @click="closeModal" class="w-full py-4 bg-red-50 text-red-600 rounded-2xl font-black text-xs uppercase tracking-widest">Cancelar</button>
            </div>
            <div v-else class="space-y-4">
                <div class="bg-primary text-white p-6 rounded-[30px]">
                    <p class="text-[8px] font-black uppercase tracking-widest opacity-60">Comprador</p>
                    <h4 class="text-xl font-black">{{ cardHolder.name }}</h4>
                    <p class="text-[10px] opacity-80 uppercase">{{ cardHolder.type }}</p>
                </div>
                <div class="grid grid-cols-2 gap-3 text-sm">
                    <div class="bg-gray-50 p-3 rounded-2xl border">
                        <p class="text-[8px] font-bold text-gray-400 uppercase">Saldo</p>
                        <p class="font-black" :class="cardHolder.balance < total ? 'text-red-500' : 'text-green-600'">{{ formatMoney(cardHolder.balance) }}</p>
                    </div>
                    <div class="bg-gray-50 p-3 rounded-2xl border">
                        <p class="text-[8px] font-bold text-gray-400 uppercase">A pagar</p>
                        <p class="font-black text-gray-900">{{ formatMoney(total) }}</p>
                    </div>
                </div>
                <button @click="confirmPayment" :disabled="processing || cardHolder.balance < total" class="w-full bg-green-500 text-white py-5 rounded-[24px] font-black text-xl shadow-lg">CONFIRMAR PAGO</button>
                <div class="grid grid-cols-2 gap-2">
                    <button @click="resetModal" class="bg-amber-100 text-amber-700 py-3 rounded-xl font-black text-[10px] uppercase">🔄 Otra Tarjeta</button>
                    <button @click="closeModal" class="bg-gray-100 text-gray-500 py-3 rounded-xl font-black text-[10px] uppercase">🚫 Salir</button>
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
import { useConfigStore } from '../stores/config'; // Importante para la URL del logo
import { formatMoney } from '../utils/formatters';

const authStore = useAuthStore();
const configStore = useConfigStore();
const products = ref([]);
const recentSales = ref([]);
const cart = ref([]);
const search = ref('');
const loading = ref(true);
const activeCategory = ref('Todas');
const isMobileCartOpen = ref(false); // <--- Control para móvil

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

const closeModal = () => { 
    showModal.value = false; 
    stepIdentified.value = false; 
    rfidCode.value = ''; 
    isMobileCartOpen.value = false; 
};

const resetModal = () => { 
    stepIdentified.value = false; 
    rfidCode.value = ''; 
    errorMessage.value = ''; 
    setTimeout(() => rfidInput.value?.focus(), 100); 
};

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
.custom-scrollbar::-webkit-scrollbar-thumb { background: #e2e8f0; border-radius: 10px; }

.custom-scrollbar-dark::-webkit-scrollbar { width: 4px; }
.custom-scrollbar-dark::-webkit-scrollbar-track { background: rgba(255,255,255,0.05); }
.custom-scrollbar-dark::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;  
  overflow: hidden;
}
</style>