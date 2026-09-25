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
