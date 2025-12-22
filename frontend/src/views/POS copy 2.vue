<template>
  <div class="flex flex-col h-full gap-6 lg:flex-row p-2">
    
    <!-- COLUMNA IZQUIERDA: PRODUCTOS -->
    <!-- COLUMNA IZQUIERDA: PRODUCTOS -->
<div class="flex-1 space-y-8 overflow-y-auto max-h-[75vh] pr-2 pb-10">
  
  <!-- BUSCADOR SUPERIOR -->
  <div class="sticky top-0 bg-gray-100 py-2 z-10 flex justify-between items-center">
    <h2 class="text-2xl font-black text-gray-800 uppercase tracking-tight">Menú Cafetería</h2>
    <input v-model="search" type="text" placeholder="🔍 Buscar..." class="w-64 p-3 border-2 border-gray-200 rounded-2xl shadow-sm outline-none focus:border-primary transition-all">
  </div>

  <!-- REPETIMOS POR CADA CATEGORÍA -->
  <div v-for="(items, categoryName) in groupedProducts" :key="categoryName" class="space-y-4">
    
    <!-- ENCABEZADO DE CATEGORÍA -->
    <div class="flex items-center gap-4">
        <h3 class="text-sm font-black text-gray-400 uppercase tracking-[0.2em] whitespace-nowrap">
            {{ categoryName }}
        </h3>
        <div class="h-[1px] bg-gray-200 w-full"></div>
    </div>

    <!-- GRILLA DE PRODUCTOS DE ESTA CATEGORÍA -->
    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
        <div 
          v-for="product in items" :key="product.id" 
          @click="addToCart(product)"
          class="bg-white p-4 rounded-[2rem] shadow-sm border-2 border-transparent hover:border-primary hover:shadow-xl cursor-pointer transition-all group active:scale-95"
        >
          <!-- Imagen / Icono -->
          <div class="h-20 w-20 rounded-2xl mx-auto mb-3 flex items-center justify-center text-4xl group-hover:scale-110 transition overflow-hidden bg-gray-50">
            <img v-if="product.image_url" :src="'http://127.0.0.1:8000' + product.image_url" class="h-full w-full object-cover">
            <span v-else>{{ getCategoryIcon(categoryName) }}</span>
          </div>

          <h3 class="font-bold text-gray-800 text-sm text-center leading-tight h-10 overflow-hidden">
            {{ product.name }}
          </h3>
          
          <div class="mt-2 text-center">
            <span class="text-primary font-black text-lg block">{{ formatMoney(product.price) }}</span>
            <span class="text-[10px] bg-blue-50 text-blue-500 px-2 py-0.5 rounded-full font-bold uppercase">
                Stock: {{ product.stock }}
            </span>
          </div>
        </div>
    </div>
  </div>

  <!-- Muestra esto si no hay resultados en ninguna categoría -->
  <div v-if="Object.keys(groupedProducts).length === 0" class="text-center py-20 text-gray-400">
    <div class="text-5xl mb-4">🙊</div>
    <p class="font-bold uppercase text-xs tracking-widest">No se encontraron productos</p>
  </div>
</div>

    <!-- COLUMNA DERECHA: CARRITO -->
    <div class="w-full lg:w-96 flex flex-col gap-4">
      <div class="bg-gray-900 text-white rounded-3xl shadow-xl flex flex-col h-[550px] border border-white/5">
        <div class="p-6 border-b border-white/10">
          <h2 class="text-xl font-black uppercase tracking-widest italic">Resumen Compra</h2>
        </div>

        <div class="flex-1 overflow-y-auto p-6 space-y-4">
          <div v-if="cart.length === 0" class="text-center text-gray-500 mt-20">
            <div class="text-5xl mb-4">🛒</div>
            <p class="font-bold uppercase text-xs tracking-widest">Carrito Vacío</p>
          </div>
          <div v-for="(item, index) in cart" :key="item.product.id" class="flex justify-between items-center bg-white/5 p-3 rounded-xl border border-white/5">
            <div class="flex-1">
              <div class="font-bold text-sm">{{ item.product.name }}</div>
              <div class="text-[10px] text-gray-400">x{{ item.quantity }} Unid.</div>
            </div>
            <div class="text-right">
              <div class="font-black text-sm">{{ formatMoney(item.product.price * item.quantity) }}</div>
              <!-- BOTÓN QUITAR MEJORADO -->
              <button @click.stop="removeFromCart(index)" class="text-[10px] text-red-400 font-bold uppercase hover:text-red-300 bg-red-400/10 px-2 py-1 rounded mt-1">
                Quitar
              </button>
            </div>
          </div>
        </div>

        <div class="p-8 bg-white/5 rounded-b-3xl border-t border-white/10">
          <div class="flex justify-between items-end mb-6">
            <span class="text-gray-400 text-xs font-bold uppercase">Total a Pagar</span>
            <span class="text-4xl font-black text-primary">{{ formatMoney(total) }}</span>
          </div>
          <button 
            @click="startCheckout" :disabled="cart.length === 0"
            class="w-full bg-primary hover:bg-blue-600 text-white py-5 rounded-2xl font-black text-xl shadow-2xl transition-all"
          >
            COBRAR (F2)
          </button>
        </div>
      </div>
    </div>

    <!-- MODAL DE COBRO (Z-INDEX ALTO) -->
    <!-- MODAL DE COBRO PROFESIONAL (TOUCH FRIENDLY) -->
    <div v-if="showModal" class="fixed inset-0 bg-black/90 backdrop-blur-md flex items-center justify-center z-[9999] p-4">
      <div class="bg-white rounded-[40px] shadow-2xl p-8 max-w-md w-full text-center relative border-4 border-gray-100">
        
        <!-- ESTADO 1: ESPERANDO LECTURA -->
        <div v-if="!stepIdentified" class="space-y-8">
            <div class="text-7xl animate-pulse">📡</div>
            <div>
                <h3 class="text-3xl font-black text-gray-900 tracking-tighter">Acerque la Tarjeta</h3>
                <p class="text-gray-500 font-medium mt-2">Terminal de identificación automática</p>
            </div>
            
            <input 
                ref="rfidInput" 
                v-model="rfidCode" 
                @keyup.enter="identifyCard" 
                type="password" 
                class="w-full border-4 border-blue-50 rounded-3xl p-6 text-center text-3xl font-bold bg-gray-50 focus:border-primary outline-none transition-all"
                placeholder="••••••"
            >

            <button 
                @click="closeModal" 
                class="w-full py-5 bg-red-50 text-red-600 rounded-2xl font-black text-lg hover:bg-red-100 transition-colors border-2 border-red-100 shadow-sm"
            >
                ❌ CANCELAR OPERACIÓN
            </button>
        </div>

        <!-- ESTADO 2: CONFIRMACIÓN DE TITULAR Y PAGO -->
        <div v-else class="space-y-6">
            <!-- Info Titular -->
            <div class="bg-blue-600 text-white p-6 rounded-[32px] shadow-lg shadow-blue-200">
                <p class="text-[10px] font-black uppercase tracking-widest opacity-80 mb-1">Cliente Identificado</p>
                <h4 class="text-2xl font-black leading-tight">{{ cardHolder.name }}</h4>
                <p class="text-xs font-bold opacity-90 mt-1">{{ cardHolder.type }}</p>
            </div>

            <!-- Precios y Saldo -->
            <div class="grid grid-cols-2 gap-4">
                <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                    <p class="text-[10px] font-bold text-gray-400 uppercase">Tu Saldo</p>
                    <p class="text-lg font-black" :class="cardHolder.balance < total ? 'text-red-600' : 'text-green-600'">
                        {{ formatMoney(cardHolder.balance) }}
                    </p>
                </div>
                <div class="bg-gray-50 p-4 rounded-2xl border border-gray-100">
                    <p class="text-[10px] font-bold text-gray-400 uppercase">A Pagar</p>
                    <p class="text-xl font-black text-gray-900">-{{ formatMoney(total) }}</p>
                </div>
            </div>

            <!-- Mensaje de Error si no hay saldo -->
            <div v-if="errorMessage || cardHolder.balance < total" class="bg-red-600 text-white p-4 rounded-2xl text-sm font-bold shadow-lg animate-bounce">
                ⚠️ {{ errorMessage || 'SALDO INSUFICIENTE' }}
            </div>

            <!-- BOTONERA GIGANTE PARA TOUCH -->
            <div class="flex flex-col gap-3 pt-4">
                <!-- CONFIRMAR (SOLO SI HAY SALDO) -->
                <button 
                    @click="confirmPayment" 
                    :disabled="processing || cardHolder.balance < total"
                    class="w-full bg-green-500 text-white py-6 rounded-3xl font-black text-2xl hover:bg-green-600 shadow-xl shadow-green-100 transition-all active:scale-95 disabled:opacity-30 disabled:grayscale"
                >
                    {{ processing ? 'PROCESANDO...' : '✅ CONFIRMAR PAGO' }}
                </button>

                <div class="grid grid-cols-2 gap-3">
                    <!-- OTRA TARJETA -->
                    <button 
                        @click="resetModal" 
                        class="bg-amber-500 text-white py-4 rounded-2xl font-black text-xs uppercase tracking-wider hover:bg-amber-600 shadow-lg shadow-amber-100 transition-all active:scale-95"
                    >
                        🔄 OTRA TARJETA
                    </button>
                    <!-- CANCELAR -->
                    <button 
                        @click="closeModal" 
                        class="bg-gray-100 text-gray-500 py-4 rounded-2xl font-black text-xs uppercase tracking-wider hover:bg-gray-200 transition-all active:scale-95"
                    >
                        🚫 CANCELAR
                    </button>
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

const authStore = useAuthStore();
const products = ref([]);
const recentSales = ref([]);
const cart = ref([]);
const search = ref('');
const loading = ref(true);

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
    } catch (e) {
        console.error("Error POS:", e);
    } finally {
        loading.value = false;
    }
};

const filteredProducts = computed(() => {
    if (!products.value) return [];
    
    return products.value.filter(p => {
        const matchesSearch = p.name.toLowerCase().includes(search.value.toLowerCase());
        const isAvailable = p.is_active;
        // --- NUEVA CONDICIÓN: STOCK MAYOR A 0 ---
        const hasStock = p.stock > 0; 
        
        return matchesSearch && isAvailable && hasStock;
    });
});

const getCategoryIcon = (cat) => {
    const icons = { 'Bebidas': '🥤', 'Alimentos': '🍕', 'Paquetes': '🍟', 'Papelería': '✏️', 'Dulces': '🍭' };
    return icons[cat] || '🍔';
};

const addToCart = (product) => {
    if(product.stock <= 0) return alert("Sin stock");
    const existing = cart.value.find(i => i.product.id === product.id);
    if(existing) existing.quantity++;
    else cart.value.push({ product, quantity: 1 });
};

// --- ELIMINAR DEL CARRITO (REFUERZO) ---
const removeFromCart = (index) => {
    cart.value.splice(index, 1);
};

const total = computed(() => cart.value.reduce((s, i) => s + (i.product.price * i.quantity), 0));

// --- GESTIÓN DE MODAL Y FOCO ---
const startCheckout = () => {
    errorMessage.value = '';
    rfidCode.value = '';
    stepIdentified.value = false;
    showModal.value = true;
    
    // Forzar foco inmediatamente y después de un tick
    setTimeout(() => {
        if (rfidInput.value) rfidInput.value.focus();
    }, 100);
};

const closeModal = () => {
    showModal.value = false;
    stepIdentified.value = false;
    rfidCode.value = '';
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
        
        // Ahora leemos los campos planos que enviamos desde el backend
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
    }
};
const confirmPayment = async () => {
    processing.value = true;
    errorMessage.value = '';
    try {
        await api.post('/sales/', {
            card_uid: cardHolder.value.uid,
            items: cart.value.map(i => ({ product_id: i.product.id, quantity: i.quantity }))
        });
        cart.value = [];
        closeModal();
        loadPOSData();
        alert("✅ Venta exitosa");
    } catch (e) {
        errorMessage.value = e.response?.data?.detail || "Error";
    } finally {
        processing.value = false;
    }
};

const handleReverse = async (id) => {
    if(!confirm("¿Reversar venta?")) return;
    try {
        await api.post(`/sales/reverse/${id}`);
        loadPOSData();
    } catch (e) { alert(e.response?.data?.detail); }
};

// 1. Mantenemos la lógica de búsqueda
const filteredProductsFlat = computed(() => {
    if (!products.value) return [];
    return products.value.filter(p => 
        p.name.toLowerCase().includes(search.value.toLowerCase()) && 
        p.stock > 0
    );
});

// 2. NUEVA FUNCIÓN: Agrupa los productos filtrados por su categoría
const groupedProducts = computed(() => {
    const groups = {};
    
    filteredProductsFlat.value.forEach(product => {
        const categoryName = product.category_rel?.name || 'General';
        if (!groups[categoryName]) {
            groups[categoryName] = [];
        }
        groups[categoryName].push(product);
    });
    
    return groups;
});

onMounted(loadPOSData);
</script>