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
import ChangePassword from '../views/ChangePassword.vue';
import PaymentResult from '../views/PaymentResult.vue';
import BalanceAudit from '../views/BalanceAudit.vue';
import PaymentGateways from '../views/PaymentGateways.vue';

const ADMIN = ['admin'];
const ADMIN_SUPERVISOR = ['admin', 'supervisor'];
const STAFF = ['admin', 'supervisor', 'vendedor'];

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
            { path: '', redirect: '/dashboard' }, // La guarda redirige según el rol
            { path: 'dashboard', component: Dashboard, meta: { roles: ADMIN_SUPERVISOR } },
            { path: 'pos', component: POS, meta: { roles: STAFF } },
            { path: 'inventory', component: Inventory, meta: { roles: ADMIN_SUPERVISOR } },
            { path: 'students', component: Students, meta: { roles: ADMIN } },
            { path: 'users', component: Users, meta: { roles: ADMIN } },
            { path: 'bulk-import', component: BulkImport, meta: { roles: ADMIN } },
            { path: 'my-family', component: MyFamily, meta: { roles: ['padre'] } },
            { path: 'profile', component: Profile },
            { path: 'change-password', component: ChangePassword },
            { path: 'my-card', component: MyCard, meta: { roles: ['empleado'] } },
            { path: 'reports', component: Reports, meta: { roles: ADMIN_SUPERVISOR } },
            { path: 'settings', component: Settings, meta: { roles: ADMIN } },
            { path: 'payment-result', component: PaymentResult },
            { path: 'balance-audit', component: BalanceAudit, meta: { roles: ADMIN } },
            { path: 'admin/payments', component: PaymentGateways, meta: { roles: ADMIN } },
        ]
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to) => {
    const authStore = useAuthStore();

    // Revalida la sesión (cookie HttpOnly) antes de decidir.
    await authStore.initialize();

    if (authStore.isAuthenticated && authStore.mustChangePassword) {
        if (to.path === '/change-password') return true;
        return '/change-password';
    }

    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        return { path: '/login', query: { redirect: to.fullPath } };
    }

    if (to.meta.guest && authStore.isAuthenticated) {
        return authStore.homePath;
    }

    const roles = to.meta.roles;
    if (roles && !roles.includes(authStore.user?.role)) {
        return authStore.homePath;
    }

    return true;
});

export default router;
