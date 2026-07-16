<script setup>
import { onMounted, ref } from 'vue'

import { deviceApi } from '../services/api'
import DeviceModal from './DeviceModal.vue'
import StatusBadge from './StatusBadge.vue'

const devices = ref([])
const loading = ref(true)
const error = ref('')
const modalOpen = ref(false)
const editingDevice = ref(null)
const busyId = ref(null)

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

function openAddModal() {
  editingDevice.value = null
  modalOpen.value = true
}

function openEditModal(device) {
  editingDevice.value = device
  modalOpen.value = true
}

async function handleSaved(formData) {
  error.value = ''
  try {
    if (editingDevice.value) {
      await deviceApi.update(editingDevice.value.id, formData)
    } else {
      await deviceApi.create(formData)
    }
    modalOpen.value = false
    await loadDevices()
  } catch (err) {
    error.value = err.message
  }
}

async function handleRepairToggle(device) {
  busyId.value = device.id
  error.value = ''
  try {
    if (device.status === 'Repair') {
      await deviceApi.restoreFromRepair(device.id)
    } else {
      await deviceApi.sendToRepair(device.id)
    }
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    busyId.value = null
  }
}

async function handleDelete(device) {
  if (!window.confirm(`Delete "${device.name}"? This action cannot be undone.`)) return
  busyId.value = device.id
  error.value = ''
  try {
    await deviceApi.remove(device.id)
    await loadDevices()
  } catch (err) {
    error.value = err.message
  } finally {
    busyId.value = null
  }
}

onMounted(loadDevices)
</script>

<template>
  <div>
    <div class="mb-6 flex items-center justify-between">
      <div>
        <h2 class="text-lg font-semibold text-gray-900">Hardware Management</h2>
        <p class="text-sm text-gray-500"></p>
      </div>
      <button
        class="flex items-center gap-2 rounded-lg bg-gray-900 px-4 py-2.5 text-sm font-semibold text-white hover:bg-black"
        @click="openAddModal"
      >
        <span class="text-base leading-none">+</span> Add New Device
      </button>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-5 py-3 font-medium">Device Name</th>
            <th class="px-5 py-3 font-medium">Brand</th>
            <th class="px-5 py-3 font-medium">Serial Number</th>
            <th class="px-5 py-3 font-medium">Date Added</th>
            <th class="px-5 py-3 font-medium">Status</th>
            <th class="px-5 py-3 font-medium">Assigned To</th>
            <th class="px-5 py-3 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="7" class="px-5 py-6 text-center text-gray-400">Loading devices…</td>
          </tr>
          <tr v-else-if="devices.length === 0">
            <td colspan="7" class="px-5 py-6 text-center text-gray-400">No devices yet.</td>
          </tr>
          <tr v-for="device in devices" :key="device.id" class="text-gray-900">
            <td class="px-5 py-3 font-medium">{{ device.name }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.brand || '—' }}</td>
            <td class="px-5 py-3 text-gray-400">{{ device.serialNumber || '—' }}</td>
            <td class="px-5 py-3 text-gray-500">{{ device.purchaseDate || '—' }}</td>
            <td class="px-5 py-3"><StatusBadge :status="device.status" /></td>
            <td class="px-5 py-3" :class="device.assignedTo ? 'text-gray-500' : 'text-gray-400'">{{ device.assignedTo || '-' }}</td>
            <td class="px-5 py-3">
              <div class="flex items-center justify-end gap-3 text-gray-400">
                <button title="Edit" class="hover:text-gray-900" @click="openEditModal(device)">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 20h9" />
                    <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
                  </svg>
                </button>
                <button
                  v-if="device.status === 'Repair'"
                  title="Mark as Available"
                  :disabled="busyId === device.id"
                  class="hover:text-green-600 disabled:cursor-not-allowed disabled:opacity-40"
                  @click="handleRepairToggle(device)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 6 9 17l-5-5" />
                  </svg>
                </button>
                <button
                  v-else
                  title="Send to Repair"
                  :disabled="busyId === device.id"
                  class="hover:text-gray-900 disabled:cursor-not-allowed disabled:opacity-40"
                  @click="handleRepairToggle(device)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94Z" />
                  </svg>
                </button>
                <button
                  title="Delete"
                  :disabled="busyId === device.id"
                  class="hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                  @click="handleDelete(device)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M3 6h18" />
                    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0-1 14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2L4 6" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <DeviceModal v-model="modalOpen" :device="editingDevice" @saved="handleSaved" />
  </div>
</template>
