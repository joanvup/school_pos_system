import axios from 'axios';

const BASE_URL = import.meta.env.PROD
    ? window.location.origin  // Toma automáticamente https://pos.colegiobilingue.edu.co
    : import.meta.env.VITE_API_BASE_URL;

const api = axios.create({
    baseURL: `${BASE_URL}/api/v1`,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Interceptor: Antes de enviar la petición, pega el token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Interceptor: Si la respuesta es 401 (Token vencido), limpiar localstorage
api.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            localStorage.removeItem('token');
            window.location.href = '/login';
        }
        return Promise.reject(error);
    }
);
export { BASE_URL };
export default api;