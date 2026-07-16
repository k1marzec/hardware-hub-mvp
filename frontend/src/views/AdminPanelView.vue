<script setup>
import { ref } from 'vue'

import AdminHardwareTab from '../components/AdminHardwareTab.vue'
import AdminUsersTab from '../components/AdminUsersTab.vue'

const TABS = [
  { id: 'hardware', label: 'Hardware' },
  { id: 'users', label: 'Users' },
]

const activeTab = ref('hardware')
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-semibold text-gray-900">Admin Panel</h1>

    <div class="mb-6 flex gap-2 border-b border-gray-200">
      <button
        v-for="tab in TABS"
        :key="tab.id"
        class="border-b-2 px-4 py-2.5 text-sm font-medium transition"
        :class="
          activeTab === tab.id
            ? 'border-gray-900 text-gray-900'
            : 'border-transparent text-gray-500 hover:text-gray-900'
        "
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <AdminHardwareTab v-if="activeTab === 'hardware'" />
    <AdminUsersTab v-else />
  </div>
</template>
