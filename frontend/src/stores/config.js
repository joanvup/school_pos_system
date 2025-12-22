import { defineStore } from 'pinia';
import api, { BASE_URL } from '../api/axios';

export const useConfigStore = defineStore('config', {
    state: () => ({
        settings: {
            school_name: 'School POS',
            school_logo: null,
            currency_symbol: '$',
            school_support_email: ''
        },
        baseUrl: BASE_URL
    }),
    actions: {
        async fetchSettings() {
            try {
                const { data } = await api.get('/settings/');
                // Combinar con los valores por defecto
                this.settings = { ...this.settings, ...data };

                // Cambiar el título de la pestaña del navegador dinámicamente
                if (this.settings.school_name) {
                    document.title = this.settings.school_name;
                }
            } catch (error) {
                console.error("Error cargando configuración visual:", error);
            }
        }
    },
    getters: {
        logoUrl: (state) => {
            return state.settings.school_logo
                ? `${state.baseUrl}${state.settings.school_logo}`
                : null;
        }
    }
});