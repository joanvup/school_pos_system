<template>
  <div class="space-y-6">
    <div class="flex flex-col md:flex-row justify-between items-center gap-4">
      <h1 class="text-2xl font-bold text-gray-800">Centro de Reportes</h1>
      
      <!-- PESTAÑAS (TABS) -->
      <div class="bg-white p-1 rounded-lg shadow-sm border flex flex-wrap">
        <button v-for="tab in tabs" :key="tab.id" @click="currentTab = tab.id"
          :class="['px-4 py-2 rounded-md text-xs font-bold transition', currentTab === tab.id ? 'bg-primary text-white shadow-sm' : 'text-gray-500 hover:text-gray-700']">
          {{ tab.name }}
        </button>
      </div>
    </div>

    <!-- AREA DINÁMICA -->
    <div class="bg-white rounded-xl shadow-lg p-6 border border-gray-100">
        <ReportSalesTotal v-if="currentTab === 'sales_total'" />
        <ReportSalesProduct v-if="currentTab === 'sales_product'" /> 
        <ReportInventory v-if="currentTab === 'inventory'" />
        <ReportRecharges v-if="currentTab === 'recharges'" />
        <ReportBalance v-if="currentTab === 'balance'" />
        <ReportOrders v-if="currentTab === 'orders'" />
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import ReportSalesTotal from '../components/reports/ReportSalesTotal.vue';
import ReportSalesProduct from '../components/reports/ReportSalesProduct.vue';
import ReportInventory from '../components/reports/ReportInventory.vue';
import ReportRecharges from '../components/reports/ReportRecharges.vue';
import ReportBalance from '../components/reports/ReportBalance.vue';
import ReportOrders from '../components/reports/ReportOrders.vue';


const currentTab = ref('sales_total');

const tabs = [
    { id: 'sales_total', name: '💰 Ventas Totales' },
    { id: 'sales_product', name: '📦 Ventas x Producto' },
    { id: 'inventory', name: '📋 Inventario' },
    { id: 'recharges', name: '💳 Recargas PSE' },
    { id: 'balance', name: '⚖️ Recargas vs Consumo' },
    { id: 'orders', name: '🚛 Entradas' }
];
</script>