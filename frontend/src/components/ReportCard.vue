<template>
  <div class="bg-white p-6 rounded-xl shadow hover:shadow-md transition border border-gray-100 flex flex-col justify-between">
    <div>
        <div class="text-3xl mb-2">{{ icon }}</div>
        <h3 class="font-bold text-gray-800 text-lg">{{ title }}</h3>
        <p class="text-gray-500 text-sm mb-6">{{ desc }}</p>
    </div>
    <div class="flex gap-2">
        <button @click="$emit('excel')" class="flex-1 bg-green-50 text-green-700 py-2 rounded font-bold text-xs hover:bg-green-100 transition">
            EXCEL
        </button>
        <button @click="$emit('pdf')" class="flex-1 bg-red-50 text-red-700 py-2 rounded font-bold text-xs hover:bg-red-100 transition">
            PDF
        </button>
    </div>
  </div>
</template>

<script setup>
defineProps(['title', 'desc', 'icon']);
defineEmits(['excel', 'pdf']);
</script>