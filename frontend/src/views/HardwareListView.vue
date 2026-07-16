<script setup>
import { computed, onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { deviceApi } from '../services/api'
import { useAuth } from '../stores/auth'

const { user } = useAuth()

const devices = ref([])
const loading = ref(true)
const error = ref('')
const actionId = ref(null)

function isMine(device) {
  return !!user.value && (device.assignedTo || '').toLowerCase() === user.value.email.toLowerCase()
}

// Decides what the action button should look like/do for a given device,
// mirroring the backend's rent/return state guards so the UI never offers
// an action the API would reject.
function actionFor(device) {
  if (device.status === 'Available') {
    return { label: 'Rent', disabled: false, variant: 'primary', handler: handleRent }
  }
  if (device.status === 'In Use') {
    return isMine(device)
      ? { label: 'Return', disabled: false, variant: 'secondary', handler: handleReturn }
      : { label: 'Rented', disabled: true, variant: 'disabled', handler: null }
  }
  if (device.status === 'Repair') {
    return { label: 'In Repair', disabled: true, variant: 'disabled', handler: null }
  }
  return { label: 'Unavailable', disabled: true, variant: 'disabled', handler: null }
}

const rows = computed(() => devices.value.map((device) => ({ device, action: actionFor(device) })))

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
  if (!user.value) return
  actionId.value = device.id
  error.value = ''
  try {
    await deviceApi.rent(device.id, user.value.email)
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    actionId.value = null
  }
}

async function handleReturn(device) {
  actionId.value = device.id
  error.value = ''
  try {
    await deviceApi.return(device.id)
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    actionId.value = null
  }
}

function handleAction(device) {
  const action = actionFor(device)
  if (action.disabled || !action.handler || actionId.value === device.id) return
  action.handler(device)
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
          <tr v-else-if="rows.length === 0">
            <td colspan="5" class="px-5 py-6 text-center text-gray-400">No devices found.</td>
          </tr>
          <tr v-for="row in rows" :key="row.device.id" class="text-gray-900">
            <td class="px-5 py-3 font-medium">{{ row.device.name }}</td>
            <td class="px-5 py-3 text-gray-500">{{ row.device.brand || '—' }}</td>
            <td class="px-5 py-3 text-gray-500">{{ row.device.purchaseDate || '—' }}</td>
            <td class="px-5 py-3"><StatusBadge :status="row.device.status" /></td>
            <td class="px-5 py-3 text-right">
              <button
                :disabled="row.action.disabled || actionId === row.device.id"
                class="rounded-lg px-4 py-1.5 text-xs font-semibold transition"
                :class="
                  row.action.disabled
                    ? 'cursor-not-allowed bg-gray-200 text-gray-400'
                    : row.action.variant === 'secondary'
                      ? 'bg-gray-200 text-gray-700 hover:bg-gray-300'
                      : 'bg-gray-900 text-white hover:bg-black'
                "
                @click="handleAction(row.device)"
              >
                {{ actionId === row.device.id ? 'Please wait…' : row.action.label }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
