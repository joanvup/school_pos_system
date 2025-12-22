import { useConfigStore } from '../stores/config';

export const formatMoney = (value) => {
    const configStore = useConfigStore();
    const symbol = configStore.settings.currency_symbol || '$';

    if (value === null || value === undefined || isNaN(value)) {
        return `${symbol}0`;
    }

    // Formateamos con separador de miles
    const formattedNumber = new Intl.NumberFormat('es-CO', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
    }).format(Math.abs(value));

    // Si el valor es negativo, ponemos el signo antes
    const sign = value < 0 ? '-' : '';

    return `${sign}${symbol}${formattedNumber}`;
};
/**
 * Obtiene la fecha actual en formato YYYY-MM-DD respetando la zona horaria local.
 * Evita el salto de día que produce .toISOString()
 */
export const getLocalISODate = (date = new Date()) => {
    const offset = date.getTimezoneOffset();
    const localDate = new Date(date.getTime() - (offset * 60 * 1000));
    return localDate.toISOString().split('T')[0];
};