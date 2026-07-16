<script setup>
import { onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { deviceApi } from '../services/api'
import { useAuth } from '../stores/auth'

const { user } = useAuth()

const devices = ref([])
const loading = ref(true)
const error = ref('')
const rentingId = ref(null)

async function loadDevices() {
  loading.value = true
  error.value = ''
  try {
    devices.value = await deviceApi.list()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function handleRent(device) {
  if (device.status !== 'Available' || !user.value) return
  rentingId.value = device.id
  error.value = ''
  try {
    await deviceApi.rent(device.id, user.value.email)
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    rentingId.value = null
  }
}

onMounted(loadDevices)
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-semibold text-gray-900">Hardware List</h1>

    <div class="mb-6 flex items-center gap-2 rounded-xl bg-gray-100 px-4 py-3">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        type="text"
        placeholder="Ask AI..."
        disabled
        class="flex-1 cursor-not-allowed bg-transparent text-sm text-gray-500 placeholder-gray-400 outline-none"
      />
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0 text-purple-400" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l1.6 4.8L18 8l-4.4 1.2L12 14l-1.6-4.8L6 8l4.4-1.2L12 2Z" />
      </svg>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-5 py-3 font-medium">Device Name</th>
            <th class="px-5 py-3 font-medium">Brand</th>
            <th class="px-5 py-3 font-medium">Date Added</th>
            <th class="px-5 py-3 font-medium">Status</th>
            <th class="px-5 py-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="5" class="px-5 py-6 text-center text-gray-400">Loading devices…</td>
          </tr>
          <tr v-else-if="devices.length === 0">
            <td colspan="5" class="px-5 py-6 text-center text-gray-400">No devices found.</td>
          </tr>
          <tr v-for="device in devices" :key="device.id" class="text-gray-900">
            <td class="px-5 py-3 font-medium">{{ device.name }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.brand || '—' }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.purchaseDate || '—' }}</td>
            <td class="px-5 py-3"><StatusBadge :status="device.status" /></td>
            <td class="px-5 py-3 text-right">
              <button
                :disabled="device.status !== 'Available' || rentingId === device.id"
                class="rounded-lg px-4 py-1.5 text-xs font-semibold transition"
                :class="
                  device.status === 'Available'
                    ? 'bg-gray-900 text-white hover:bg-black'
                    : 'cursor-not-allowed bg-gray-200 text-gray-400'
                "
                @click="handleRent(device)"
              >
                {{ rentingId === device.id ? 'Renting…' : 'Rent' }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
