import axios from 'axios';

const BASE_URL = import.meta.env.PROD
    ? window.location.origin  // Toma automáticamente https://pos.colegiobilingue.edu.co
    : import.meta.env.VITE_API_BASE_URL;

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CSRF_COOKIE = 'school_pos_csrf';
const CSRF_HEADER = 'X-CSRF-Token';

const api = axios.create({
    baseURL: `${BASE_URL}/api/v1`,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
    },
});

function readCookie(name) {
    const prefix = `${name}=`;
    const match = document.cookie
        .split('; ')
        .find((row) => row.startsWith(prefix));
    return match ? decodeURIComponent(match.slice(prefix.length)) : null;
}

// La sesión viaja en cookie HttpOnly; solo el token CSRF es legible por JS.
api.interceptors.request.use(
    (config) => {
        const method = (config.method || 'get').toUpperCase();
        if (UNSAFE_METHODS.has(method)) {
            const csrfToken = readCookie(CSRF_COOKIE);
            if (csrfToken) {
                config.headers[CSRF_HEADER] = csrfToken;
            }
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Endpoints donde un 401 es un error de credenciales, no una sesión vencida.
const AUTH_ENDPOINTS = [
    '/auth/login/access-token',
    '/auth/password-recovery',
    '/auth/reset-password',
];

// Interceptor: si la sesión venció, limpiar el store y volver al login.
api.interceptors.response.use(
    (response) => response,
    (error) => {
        const url = error.config?.url || '';
        const isAuthRequest = AUTH_ENDPOINTS.some((path) => url.includes(path));
        const skipRedirect = error.config?.skipAuthRedirect === true;

        if (error.response?.status === 401 && !isAuthRequest && !skipRedirect) {
            if (!window.location.pathname.startsWith('/login')) {
                // Imports dinámicos para evitar el ciclo router -> auth -> axios.
                Promise.all([
                    import('../stores/auth'),
                    import('../router'),
                ])
                    .then(([{ useAuthStore }, { default: router }]) => {
                        useAuthStore().clearSession();
                        router.push('/login');
                    })
                    .catch(() => {
                        window.location.href = '/login';
                    });
            }
        }
        return Promise.reject(error);
    }
);

const downloadNfcReader = async () => {
    const response = await api.get('/downloads/nfc-reader', {
        responseType: 'blob'
    });
    const disposition = response.headers['content-disposition'] || '';
    const filenameMatch = disposition.match(/filename\*?=(?:UTF-8''|")?([^";]+)"?/i);
    const filename = filenameMatch?.[1] || 'ACR122U_NFC.exe';
    const objectUrl = window.URL.createObjectURL(response.data);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 100);
};

export { BASE_URL, downloadNfcReader };
export default api;
