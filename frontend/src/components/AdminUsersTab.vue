<script setup>
import { onMounted, ref } from 'vue'

import { userApi } from '../services/api'
import CreateUserModal from './CreateUserModal.vue'

const users = ref([])
const loading = ref(true)
const error = ref('')
const modalOpen = ref(false)
const saving = ref(false)

async function loadUsers() {
  loading.value = true
  error.value = ''
  try {
    users.value = await userApi.list()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function handleCreate(formData) {
  saving.value = true
  error.value = ''
  try {
    await userApi.create(formData.email, formData.password)
    modalOpen.value = false
    await loadUsers()
  } catch (err) {
    error.value = err.message
  } finally {
    saving.value = false
  }
}

onMounted(loadUsers)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">User Accounts</h2>
        <p class="text-sm text-gray-500"></p>
      </div>
      <button
        class="flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-black"
        @click="modalOpen = true"
      >
        <span class="text-base leading-none">+</span> Create User
      </button>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-5 py-3 font-medium">Email</th>
            <th class="px-5 py-3 font-medium">Role</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="2" class="px-5 py-6 text-center text-gray-400">Loading users…</td>
          </tr>
          <tr v-else-if="users.length === 0">
            <td colspan="2" class="px-5 py-6 text-center text-gray-400">No users yet.</td>
          </tr>
          <tr v-for="u in users" :key="u.id" class="text-gray-900">
            <td class="px-5 py-3 font-medium">{{ u.email }}</td>
            <td class="px-5 py-3">
              <span
                class="inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold"
                :class="u.role === 'admin' ? 'bg-gray-900 text-white' : 'bg-gray-100 text-gray-600'"
              >
                {{ u.role === 'admin' ? 'Admin' : 'User' }}
              </span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <CreateUserModal v-model="modalOpen" @saved="handleCreate" />
  </div>
</template>
