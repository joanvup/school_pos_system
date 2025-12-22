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
        ]
    }
];

const router = createRouter({
    history: createWebHistory(),
    routes,
});

router.beforeEach(async (to, from, next) => {
    const authStore = useAuthStore();

    // Si la ruta requiere auth y no tenemos token
    if (to.meta.requiresAuth && !authStore.isAuthenticated) {
        next('/login');
    }
    // Si vamos al login pero ya estamos logueados
    else if (to.meta.guest && authStore.isAuthenticated) {
        next('/');
    }
    else {
        next();
    }
});

export default router;