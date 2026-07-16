<script setup>
import Sidebar from '../components/Sidebar.vue'
</script>

<template>
  <div class="flex h-screen bg-gray-50">
    <Sidebar />
    <main class="flex-1 overflow-y-auto p-8">
      <router-view />
    </main>
  </div>
</template>
