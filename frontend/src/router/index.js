import { createRouter, createWebHistory } from 'vue-router';
import { useAuthStore } from '../stores/auth';

// Importación de Vistas
import Login from '../views/Login.vue';
import MainLayout from '../layouts/MainLayout.vue';

// Vistas del Dashboard
import Dashboard from '../views/Dashboard.vue';
import POS from '../views/POS.vue';
import Inventory from '../views/Inventory.vue';
import Students from '../views/Students.vue';
import Users from '../views/Users.vue';
import BulkImport from '../views/BulkImport.vue';
import MyFamily from '../views/MyFamily.vue';
import Profile from '../views/Profile.vue';
import MyCard from '../views/MyCard.vue';
import Reports from '../views/Reports.vue';
import Settings from '../views/Settings.vue';
import ResetPassword from '../views/ResetPassword.vue';
import PaymentResult from '../views/PaymentResult.vue';
import BalanceAudit from '../views/BalanceAudit.vue';


const routes = [
    {
        path: '/login',
        component: Login,
        meta: { guest: true }
    },
    {
        path: '/reset-password',
        component: ResetPassword,
        meta: { guest: true }
    },
    {
        path: '/',
        component: MainLayout,
        meta: { requiresAuth: true },
        children: [
            { path: '', redirect: '/dashboard' }, // Redirección por defecto
            { path: 'dashboard', component: Dashboard },
            { path: 'pos', component: POS },
            { path: 'inventory', component: Inventory },
            { path: 'students', component: Students },
            { path: 'users', component: Users },
            { path: 'bulk-import', component: BulkImport },
            { path: 'my-family', component: MyFamily },
            { path: 'profile', component: Profile },
            { path: 'my-card', component: MyCard },
            { path: 'reports', component: Reports },
            { path: 'settings', component: Settings },
            { path: 'payment-result', component: PaymentResult },
            { path: 'balance-audit', component: BalanceAudit },
        ]
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore();

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        return next('/login');
    }

    // SI EL USUARIO VA A LA RAÍZ "/", REDIRIGIR SEGÚN ROL
    if (to.path === '/' && authStore.isAuthenticated) {
        const role = authStore.user?.role;
        if (role === 'padre') return next('/my-family');
        if (role === 'empleado') return next('/my-card');
        if (role === 'vendedor') return next('/pos');
        return next('/dashboard'); // Admin y Supervisor
    }

    next();
});

export default router;