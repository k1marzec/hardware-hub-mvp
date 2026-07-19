<script setup>
import { onMounted, ref } from 'vue'

import { useDeviceFilters } from '../composables/useDeviceFilters'
import { useRowHighlight } from '../composables/useRowHighlight'
import { deviceApi } from '../services/api'
import DeviceModal from './DeviceModal.vue'
import StatusBadge from './StatusBadge.vue'

const devices = ref([])
const loading = ref(true)
const error = ref('')
const modalOpen = ref(false)
const editingDevice = ref(null)
const busyId = ref(null)

const emit = defineEmits(['devicesChanged'])

// --- Toolbar: search + status + brand/category filters ---------------------

const {
  STATUS_OPTIONS,
  searchQuery,
  statusFilter,
  brandFilter,
  categoryFilter,
  brandOptions,
  categoryOptions,
  filteredDevices,
  hasActiveFilters,
  clearFilters,
} = useDeviceFilters(devices)

// --- Locate + highlight a row (e.g. from the Inventory Auditor) ------------

const { highlightedId, scrollToDevice } = useRowHighlight()

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

// Updates the local `devices` array in place from the API response instead
// of reloading the page (or even re-fetching the whole list), so the table
// reflects the change instantly without a flicker. Also re-runs the AI
// Health Check so a newly reported `issue` shows up as a fresh tile right
// away.
async function handleSaved(formData) {
  error.value = ''
  try {
    if (editingDevice.value) {
      const updated = await deviceApi.update(editingDevice.value.id, formData)
      const idx = devices.value.findIndex((device) => device.id === updated.id)
      if (idx !== -1) devices.value[idx] = updated
    } else {
      const created = await deviceApi.create(formData)
      devices.value.push(created)
    }
    modalOpen.value = false
    emit('devicesChanged')
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

// Exposed so AdminPanelView can refresh this tab's data after the AI Health
// Check resolves a device issue (status/history/issue change server-side),
// and so it can jump/highlight a specific device row from the AI report.
defineExpose({ loadDevices, scrollToDevice })
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

    <!-- Toolbar: search + status + brand filters -->
    <div class="mb-6 flex flex-wrap items-center gap-3">
      <div class="relative">
        <svg xmlns="http://www.w3.org/2000/svg" class="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name or brand…"
          class="w-56 rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-700 outline-none placeholder-gray-400 focus:ring-2 focus:ring-gray-300"
        />
      </div>

      <select
        v-model="statusFilter"
        class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-gray-300"
      >
        <option v-for="option in STATUS_OPTIONS" :key="option" :value="option">
          {{ option === 'All' ? 'All Statuses' : option }}
        </option>
      </select>

      <select
        v-model="brandFilter"
        class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-gray-300"
      >
        <option v-for="option in brandOptions" :key="option" :value="option">
          {{ option === 'All' ? 'All Brands' : option }}
        </option>
      </select>

      <select
        v-model="categoryFilter"
        class="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700 outline-none focus:ring-2 focus:ring-gray-300"
      >
        <option v-for="option in categoryOptions" :key="option" :value="option">
          {{ option === 'All' ? 'All Categories' : option }}
        </option>
      </select>

      <button
        v-if="hasActiveFilters"
        type="button"
        title="Clear filters"
        class="flex items-center gap-1 rounded-lg px-2 py-2 text-sm text-gray-400 hover:bg-gray-100 hover:text-gray-600"
        @click="clearFilters"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
        Clear filters
      </button>
    </div>

    <p v-if="error" class="mb-4 text-sm text-red-600">{{ error }}</p>

    <div class="overflow-x-auto rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-3 py-2 font-medium">Device Name</th>
            <th class="px-3 py-2 font-medium">Brand</th>
            <th class="px-3 py-2 font-medium">Category</th>
            <th class="px-3 py-2 font-medium">Serial Number</th>
            <th class="px-3 py-2 font-medium">Date Added</th>
            <th class="px-3 py-2 font-medium">Status</th>
            <th class="px-3 py-2 font-medium">Assigned To</th>
            <th class="px-3 py-2 font-medium">Issue</th>
            <th class="px-3 py-2 font-medium">Notes</th>
            <th class="px-3 py-2 font-medium">History</th>
            <th class="w-24 whitespace-nowrap px-3 py-2 text-right font-medium">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="11" class="px-3 py-6 text-center text-gray-400">Loading devices…</td>
          </tr>
          <tr v-else-if="filteredDevices.length === 0">
            <td colspan="11" class="px-3 py-6 text-center text-gray-400">
              {{ devices.length === 0 ? 'No devices yet.' : 'No devices match the selected filters.' }}
            </td>
          </tr>
          <tr
            v-for="device in filteredDevices"
            :id="'device-' + device.id"
            :key="device.id"
            class="text-gray-900 align-top"
            :class="{ highlight: highlightedId === device.id }"
          >
            <td class="px-3 py-2 font-medium">{{ device.name }}</td>
            <td class="px-3 py-2 text-gray-500">{{ device.brand || '—' }}</td>
            <td class="px-3 py-2 text-gray-500">{{ device.category || '—' }}</td>
            <td class="px-3 py-2 text-gray-400">{{ device.serialNumber || '—' }}</td>
            <td class="px-3 py-2 text-gray-500">{{ device.purchaseDate || '—' }}</td>
            <td class="px-3 py-2"><StatusBadge :status="device.status" /></td>
            <td class="px-3 py-2" :class="device.assignedTo ? 'text-gray-500' : 'text-gray-400'">{{ device.assignedTo || '—' }}</td>
            <td class="w-44 px-3 py-2" :class="device.issue ? 'text-gray-500' : 'text-gray-400'">
              <div class="long-text-scroll max-h-[12.5rem] overflow-y-auto whitespace-pre-line break-words pr-1">
                {{ device.issue || '—' }}
              </div>
            </td>
            <td class="w-44 px-3 py-2" :class="device.notes ? 'text-gray-500' : 'text-gray-400'">
              <div class="long-text-scroll max-h-[12.5rem] overflow-y-auto whitespace-pre-line break-words pr-1">
                {{ device.notes || '—' }}
              </div>
            </td>
            <td class="w-44 px-3 py-2" :class="device.history ? 'text-gray-500' : 'text-gray-400'">
              <div class="long-text-scroll max-h-[12.5rem] overflow-y-auto whitespace-pre-line break-words pr-1">
                {{ device.history || '—' }}
              </div>
            </td>
            <td class="w-24 whitespace-nowrap px-3 py-2">
              <div class="flex items-center justify-end gap-2 text-gray-400">
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

<style scoped>
/* Long Issue/Notes/History text scrolls internally after ~10 lines instead
   of stretching the row (or the whole table) indefinitely. */
.long-text-scroll {
  scrollbar-width: thin;
}
.long-text-scroll::-webkit-scrollbar {
  width: 6px;
}
.long-text-scroll::-webkit-scrollbar-thumb {
  background-color: rgba(107, 114, 128, 0.4);
  border-radius: 999px;
}
.long-text-scroll::-webkit-scrollbar-track {
  background: transparent;
}

/* Briefly highlights a row after scrollToDevice() jumps to it, then fades
   back out on its own (no JS needed to remove the color, only the class). */
.highlight {
  animation: highlight-fade 2s ease-out;
}
@keyframes highlight-fade {
  0% {
    background-color: rgba(99, 102, 241, 0.35);
  }
  100% {
    background-color: transparent;
  }
}
</style>
