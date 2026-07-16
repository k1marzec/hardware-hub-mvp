<script setup>
import { onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { deviceApi } from '../services/api'
import { useAuth } from '../stores/auth'

const { user } = useAuth()

const devices = ref([])
const loading = ref(true)
const error = ref('')
const returningId = ref(null)

async function loadRentals() {
  if (!user.value) return
  loading.value = true
  error.value = ''
  try {
    devices.value = await deviceApi.myRentals(user.value.email)
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function handleReturn(device) {
  returningId.value = device.id
  error.value = ''
  try {
    await deviceApi.return(device.id)
    await loadRentals()
  } catch (err) {
    error.value = err.message
  } finally {
    returningId.value = null
  }
}

onMounted(loadRentals)
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-semibold text-gray-900">My Rentals</h1>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-5 py-3 font-medium">Device Name</th>
            <th class="px-5 py-3 font-medium">Brand</th>
            <th class="px-5 py-3 font-medium">Serial Number</th>
            <th class="px-5 py-3 font-medium">Status</th>
            <th class="px-5 py-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="5" class="px-5 py-10 text-center text-gray-400">Loading rentals…</td>
          </tr>
          <tr v-else-if="devices.length === 0">
            <td colspan="5" class="px-5 py-10 text-center text-gray-400">You don't have any active rentals</td>
          </tr>
          <tr v-for="device in devices" :key="device.id" class="text-gray-900">
            <td class="px-5 py-3 font-medium">{{ device.name }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.brand || '—' }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.serialNumber || '—' }}</td>
            <td class="px-5 py-3"><StatusBadge :status="device.status" /></td>
            <td class="px-5 py-3 text-right">
              <button
                :disabled="returningId === device.id"
                class="rounded-lg bg-gray-100 px-4 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-200"
                @click="handleReturn(device)"
              >
                {{ returningId === device.id ? 'Returning…' : 'Return' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
