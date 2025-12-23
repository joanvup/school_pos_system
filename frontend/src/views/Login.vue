<template>
  <div class="min-h-screen w-full flex flex-col md:flex-row font-sans">
    
    <!-- LADO IZQUIERDO: ILUSTRACIÓN Y MENSAJE (Oculto en móvil pequeño) -->
    <div class="hidden md:flex md:w-1/2 bg-primary relative overflow-hidden items-center justify-center p-12">
        <!-- Decoración de fondo (Círculos abstractos) -->
        <div class="absolute top-0 left-0 w-96 h-96 bg-blue-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob"></div>
        <div class="absolute bottom-0 right-0 w-96 h-96 bg-indigo-400 rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-blob animation-delay-2000"></div>
        
        <div class="relative z-10 text-center space-y-8 max-w-lg">
            <div class="bg-white/10 backdrop-blur-lg border border-white/20 p-8 rounded-[40px] shadow-2xl">
                <div class="text-7xl mb-6">🥗</div>
                <h2 class="text-4xl font-black text-white leading-tight uppercase italic tracking-tighter">
                    Nutriendo el <br> <span class="text-blue-200">Futuro Escolar</span>
                </h2>
                <p class="text-blue-100 text-lg font-medium mt-4 opacity-80">
                    Sistema centralizado de gestión para cafeterías inteligentes. Rápido, seguro y sin efectivo.
                </p>
            </div>
            
            <div class="flex justify-center gap-4">
                <div class="bg-white/5 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/10 text-white text-xs font-bold uppercase tracking-widest">
                    RFID Ready 💳
                </div>
                <div class="bg-white/5 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/10 text-white text-xs font-bold uppercase tracking-widest">
                    PSE Integrated 💸
                </div>
            </div>
        </div>
    </div>

    <!-- LADO DERECHO: FORMULARIO -->
    <div class="w-full md:w-1/2 bg-white flex items-center justify-center p-8 lg:p-24 relative">
        <!-- Logo Móvil (Solo visible en pantallas pequeñas) -->
        <div class="md:hidden absolute top-12 left-0 w-full text-center">
             <h1 class="text-3xl font-black text-primary italic tracking-tighter uppercase">School POS</h1>
        </div>

        <div class="w-full max-w-md space-y-10 animate-fade-in">
            <!-- Encabezado Formulario -->
            <div class="space-y-2">
                <h3 class="text-4xl font-black text-gray-900 tracking-tighter">Bienvenido</h3>
                <p class="text-gray-400 font-bold text-sm uppercase tracking-widest">Inicia sesión para continuar</p>
            </div>

            <!-- Formulario -->
            <form @submit.prevent="handleLogin" class="space-y-6">
                <div class="space-y-4">
                    <!-- Email -->
                    <div class="relative group">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-4 transition-colors group-focus-within:text-primary">Correo Electrónico</label>
                        <div class="flex items-center mt-1">
                            <span class="absolute left-4 text-gray-400 group-focus-within:text-primary transition-colors">📧</span>
                            <input 
                                v-model="email" 
                                type="email" 
                                required 
                                placeholder="tu@colegio.com"
                                class="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-gray-50 rounded-2xl outline-none focus:border-primary focus:bg-white transition-all font-medium text-gray-700 shadow-sm"
                            >
                        </div>
                    </div>

                    <!-- Password -->
                    <div class="relative group">
                        <label class="text-[10px] font-black text-gray-400 uppercase tracking-widest ml-4 transition-colors group-focus-within:text-primary">Contraseña</label>
                        <div class="flex items-center mt-1">
                            <span class="absolute left-4 text-gray-400 group-focus-within:text-primary transition-colors">🔒</span>
                            <input 
                                v-model="password" 
                                type="password" 
                                required 
                                placeholder="••••••••"
                                class="w-full pl-12 pr-4 py-4 bg-gray-50 border-2 border-gray-50 rounded-2xl outline-none focus:border-primary focus:bg-white transition-all font-medium text-gray-700 shadow-sm"
                            >
                        </div>
                    </div>
                    <div class="text-right">
                        <button type="button" @click="showRecoverModal = true" class="text-xs font-bold text-primary hover:underline uppercase tracking-widest">
                            ¿Olvidaste tu contraseña?
                        </button>
                    </div>
                    <!-- MODAL DE RECUPERACIÓN -->
                    <div v-if="showRecoverModal" class="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                        <div class="bg-white rounded-[32px] p-8 max-w-sm w-full shadow-2xl animate-fade-in">
                            <h3 class="text-2xl font-black mb-2">Recuperar Acceso</h3>
                            <p class="text-gray-500 text-sm mb-6">Ingresa tu correo y te enviaremos un enlace de recuperación.</p>
                            
                            <input v-model="recoverEmail" type="email" placeholder="email@colegio.com" 
                                class="w-full p-4 bg-gray-50 border-2 border-gray-100 rounded-2xl mb-4 outline-none focus:border-primary">
        
                            <button @click="handleRecover" :disabled="loadingRecover"
                                class="w-full bg-gray-900 text-white py-4 rounded-2xl font-bold mb-3 disabled:opacity-50">
                                {{ loadingRecover ? 'Enviando...' : 'Enviar Enlace' }}
                            </button>
                            <button @click="showRecoverModal = false" class="w-full text-gray-400 text-xs font-bold uppercase">Cerrar</button>
                        </div>
                    </div>
                </div>

                <!-- Mensaje de Error -->
                <div v-if="errorMessage" class="bg-red-50 text-red-600 p-4 rounded-2xl text-xs font-black border border-red-100 flex items-center gap-3 animate-shake">
                    <span>⚠️</span> {{ errorMessage }}
                </div>

                <!-- Botón de Acción -->
                <button 
                    type="submit" 
                    :disabled="loading"
                    class="w-full bg-primary hover:bg-indigo-700 text-white py-5 rounded-[24px] font-black text-lg shadow-xl shadow-blue-200 transition-all active:scale-95 disabled:opacity-50 disabled:grayscale flex justify-center items-center gap-3 uppercase tracking-tighter"
                >
                    <span v-if="!loading">Acceder al Sistema</span>
                    <div v-else class="w-6 h-6 border-4 border-white/30 border-t-white rounded-full animate-spin"></div>
                </button>
            </form>

            <!-- Footer Footer -->
            <div class="pt-12 text-center">
                <p class="text-xs text-gray-400 font-bold uppercase tracking-widest">
                    &copy; 2025 · Gestión Tecnológica Escolar
                </p>
            </div>
        </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '../stores/auth';
import { useRouter } from 'vue-router';
import { useConfigStore } from '../stores/config';
import api from '../api/axios'; 
const configStore = useConfigStore();

const authStore = useAuthStore();
const router = useRouter();

const email = ref('');
const password = ref('');
const loading = ref(false);
const errorMessage = ref('');

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
    console.error("Login Error:", error);
    errorMessage.value = 'Credenciales no válidas o cuenta inactiva';
  } finally {
    loading.value = false;
  }
};

const showRecoverModal = ref(false);
const recoverEmail = ref('');
const loadingRecover = ref(false);

const handleRecover = async () => {
    if(!recoverEmail.value) return;
    loadingRecover.value = true;
    try {
        // Asegúrate de que la URL sea exactamente esta:
        const response = await api.post(`/auth/password-recovery/${recoverEmail.value}`);
        alert("Si el correo existe, recibirás un mensaje en breve.");
        showRecoverModal.value = false;
    } catch (e) {
        // ESTO TE DIRÁ EL ERROR REAL EN LA CONSOLA (F12)
        console.error("Error detallado:", e.response?.data || e.message);
        
        if (e.response?.status === 404) {
            alert("Error: Ruta no encontrada. Revisa el prefijo /auth en el Backend.");
        } else {
            alert("Error al procesar solicitud: " + (e.response?.data?.detail || "Problema de conexión"));
        }
    } finally {
        loadingRecover.value = false;
    }
};
</script>

<style scoped>
/* Animaciones Personalizadas */
@keyframes blob {
  0% { transform: translate(0px, 0px) scale(1); }
  33% { transform: translate(30px, -50px) scale(1.1); }
  66% { transform: translate(-20px, 20px) scale(0.9); }
  100% { transform: translate(0px, 0px) scale(1); }
}

.animate-blob {
  animation: blob 7s infinite;
}

.animation-delay-2000 {
  animation-delay: 2s;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
}

.animate-fade-in {
    animation: fadeIn 0.8s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-5px); }
  75% { transform: translateX(5px); }
}

.animate-shake {
  animation: shake 0.2s ease-in-out 0s 2;
}

/* Tipografía Adicional (Opcional si usas Google Fonts en tu index.html) */
/* @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap'); */
</style>