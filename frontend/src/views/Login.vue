<template>
  <div class="min-h-screen w-full flex bg-slate-50 overflow-hidden font-sans">
    
    <!-- LADO IZQUIERDO: PANEL VISUAL (Visible en Desktop >= md) -->
    <div class="hidden lg:flex lg:w-3/5 bg-slate-900 relative items-center justify-center p-12 overflow-hidden">
        <!-- Fondo Animado de Gradientes -->
        <div class="absolute inset-0 z-0">
            <div class="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-blue-600 rounded-full mix-blend-screen filter blur-[120px] opacity-40 animate-pulse"></div>
            <div class="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-indigo-600 rounded-full mix-blend-screen filter blur-[120px] opacity-40 animate-pulse animation-delay-2000"></div>
        </div>

        <div class="relative z-10 w-full max-w-xl">
            <div class="bg-white/5 backdrop-blur-2xl border border-white/10 p-12 rounded-[60px] shadow-2xl space-y-8">
                <!-- Logo PWA -->
                <div class="flex justify-center">
                    <img src="/pwa-192x192.png" alt="App Logo" class="w-32 h-32 rounded-[35px] shadow-2xl border-4 border-white/20 p-2 bg-white/10 hover:rotate-3 transition-transform duration-500">
                </div>
                
                <div class="text-center space-y-4">
                    <h2 class="text-5xl font-black text-white tracking-tighter leading-none italic uppercase">
                        {{ configStore.settings.school_name }}
                    </h2>
                    <div class="h-1.5 w-24 bg-primary mx-auto rounded-full"></div>
                    <p class="text-slate-400 text-lg font-medium leading-relaxed max-w-sm mx-auto">
                        Gestión inteligente de cafetería, finanzas escolares y nutrición en un solo lugar.
                    </p>
                </div>

                <div class="flex justify-center gap-3 pt-6">
                    <span class="px-5 py-2 rounded-full bg-white/5 border border-white/10 text-white/60 text-[10px] font-black uppercase tracking-widest">v1.0 Pro</span>
                    <span class="px-5 py-2 rounded-full bg-white/5 border border-white/10 text-white/60 text-[10px] font-black uppercase tracking-widest">NFC Security</span>
                </div>
            </div>
        </div>
    </div>

    <!-- LADO DERECHO: FORMULARIO DE ACCESO (Móvil y Desktop) -->
    <div class="w-full lg:w-2/5 flex flex-col items-center justify-center p-6 sm:p-12 md:p-20 bg-white relative">
        
        <!-- Logo Móvil (Solo visible en < lg) -->
        <div class="lg:hidden absolute top-10 flex flex-col items-center gap-3">
             <img src="/pwa-192x192.png" class="w-20 h-20 rounded-2xl shadow-xl">
             <h1 class="text-xl font-black text-slate-800 uppercase tracking-tighter italic">
                {{ configStore.settings.school_name }}
             </h1>
        </div>

        <div class="w-full max-w-sm space-y-12 animate-fade-in">
            <!-- Header Acceso -->
            <div class="space-y-3">
                <h3 class="text-4xl font-black text-slate-900 tracking-tighter">Acceso Personal</h3>
                <p class="text-slate-400 font-bold text-xs uppercase tracking-[0.2em]">Panel de Control Unificado</p>
            </div>

            <!-- Formulario Principal -->
            <form @submit.prevent="handleLogin" class="space-y-8">
                <div class="space-y-5">
                    <!-- Campo Email -->
                    <div class="space-y-2">
                        <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest ml-1">Identificación / Email</label>
                        <div class="relative flex items-center group">
                            <span class="absolute left-4 text-slate-300 group-focus-within:text-primary transition-colors">👤</span>
                            <input 
                                v-model="email" type="email" required placeholder="nombre@colegio.edu.co"
                                class="w-full pl-12 pr-4 py-4 bg-slate-50 border-2 border-slate-50 rounded-2xl outline-none focus:border-primary focus:bg-white transition-all font-bold text-slate-700 shadow-sm"
                            >
                        </div>
                    </div>

                    <!-- Campo Password -->
                    <div class="space-y-2">
                        <div class="flex justify-between items-center px-1">
                            <label class="text-[10px] font-black text-slate-400 uppercase tracking-widest">Contraseña Segura</label>
                            <button @click="showRecoverModal = true" type="button" class="text-[10px] font-black text-primary uppercase hover:underline">¿La olvidaste?</button>
                        </div>
                        <div class="relative flex items-center group">
                            <span class="absolute left-4 text-slate-300 group-focus-within:text-primary transition-colors">🔒</span>
                            <input 
                                v-model="password" type="password" required placeholder="••••••••"
                                class="w-full pl-12 pr-4 py-4 bg-slate-50 border-2 border-slate-50 rounded-2xl outline-none focus:border-primary focus:bg-white transition-all font-bold text-slate-700 shadow-sm"
                            >
                        </div>
                    </div>
                </div>

                <!-- Error -->
                <div v-if="errorMessage" class="bg-red-50 text-red-600 p-4 rounded-2xl text-[10px] font-black uppercase border border-red-100 flex items-center gap-3 animate-shake">
                    <span>⚠️</span> {{ errorMessage }}
                </div>

                <!-- Botón Login -->
                <button 
                    type="submit" :disabled="loading"
                    class="w-full bg-slate-900 hover:bg-primary text-white py-5 rounded-[28px] font-black text-lg shadow-2xl shadow-slate-200 transition-all active:scale-95 disabled:opacity-50 disabled:grayscale flex justify-center items-center gap-3 uppercase tracking-tighter"
                >
                    <span v-if="!loading">Ingresar al Portal</span>
                    <div v-else class="w-6 h-6 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
                </button>
            </form>

            <div class="pt-8 text-center border-t border-slate-100">
                <p class="text-[9px] text-slate-300 font-bold uppercase tracking-widest leading-loose">
                    Protegido por Cifrado de Grado Bancario <br>
                    &copy; 2025 · School POS v1.0.0
                </p>
            </div>
        </div>
    </div>

    <!-- MODAL DE RECUPERACIÓN (GLASSMORPHISM) -->
    <Transition name="fade">
        <div v-if="showRecoverModal" class="fixed inset-0 bg-slate-900/60 backdrop-blur-md flex items-center justify-center z-[100] p-4">
            <div class="bg-white rounded-[50px] p-10 max-w-md w-full shadow-2xl border-8 border-slate-50/50 animate-scale-in text-center">
                <div class="text-6xl mb-6">🔑</div>
                <h3 class="text-3xl font-black text-slate-900 tracking-tighter mb-2 italic">¿Problemas de Acceso?</h3>
                <p class="text-slate-500 text-sm font-medium mb-8">Ingresa tu correo y te enviaremos una llave temporal.</p>
                
                <input v-model="recoverEmail" type="email" placeholder="email@colegio.edu.co" 
                       class="w-full p-5 bg-slate-100 border-2 border-slate-100 rounded-3xl mb-4 outline-none focus:border-primary font-bold text-center">
                
                <div class="flex flex-col gap-3">
                    <button @click="handleRecover" :disabled="loadingRecover"
                            class="w-full bg-primary text-white py-5 rounded-[24px] font-black uppercase tracking-widest shadow-xl shadow-blue-100">
                        {{ loadingRecover ? 'Enviando...' : 'Enviar enlace' }}
                    </button>
                    <button @click="showRecoverModal = false" class="py-2 text-slate-400 text-[10px] font-black uppercase tracking-widest hover:text-slate-600">Cerrar ventana</button>
                </div>
            </div>
        </div>
    </Transition>

  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useConfigStore } from '../stores/config';
import { useRouter } from 'vue-router';
import api from '../api/axios';

const authStore = useAuthStore();
const configStore = useConfigStore();
const router = useRouter();

const email = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref('');

// Recuperación
const showRecoverModal = ref(false);
const recoverEmail = ref('');
const loadingRecover = ref(false);

const handleLogin = async () => {
  loading.value = true;
  errorMessage.value = '';
  try {
    await authStore.login(email.value, password.value);
    
    // Redirección inteligente por Rol
    const role = authStore.user?.role;
    if (role === 'padre') router.push('/my-family');
    else if (role === 'empleado') router.push('/my-card');
    else if (role === 'vendedor') router.push('/pos');
    else router.push('/dashboard');
    
  } catch (error) {
    errorMessage.value = 'Error de identificación. Verifique datos.';
  } finally {
    loading.value = false;
  }
};

const handleRecover = async () => {
    if(!recoverEmail.value) return;
    loadingRecover.value = true;
    try {
        await api.post(`/auth/password-recovery/${recoverEmail.value}`);
        alert("¡Listo! Revisa tu bandeja de entrada.");
        showRecoverModal.value = false;
    } catch (e) {
        alert("Error al procesar. Intenta más tarde.");
    } finally {
        loadingRecover.value = false;
    }
};
</script>

<style scoped>
@keyframes fadeIn {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in { animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes scaleIn {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
}
.animate-scale-in { animation: scaleIn 0.4s cubic-bezier(0.16, 1, 0.3, 1); }

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}
.animate-shake { animation: shake 0.2s ease-in-out 0s 2; }

/* Transiciones de Modal */
.fade-enter-active, .fade-leave-active { transition: opacity 0.4s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

.animation-delay-2000 { animation-delay: 2s; }
</style>