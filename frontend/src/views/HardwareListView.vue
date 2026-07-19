<script setup>
import { computed, onMounted, ref } from 'vue'

import StatusBadge from '../components/StatusBadge.vue'
import { useDeviceFilters } from '../composables/useDeviceFilters'
import { useRowHighlight } from '../composables/useRowHighlight'
import { deviceApi } from '../services/api'
import { useAuth } from '../stores/auth'

const { user } = useAuth()

const devices = ref([])
const loading = ref(true)
const error = ref('')
const actionId = ref(null)

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

// --- Sorting ---------------------------------------------------------------

const sortKey = ref(null) // 'name' | 'brand' | 'category' | 'purchaseDate' | null
const sortDir = ref('asc') // 'asc' | 'desc'

function toggleSort(key) {
  if (sortKey.value === key) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortKey.value = key
    sortDir.value = 'asc'
  }
}

function compareDevices(a, b) {
  const key = sortKey.value
  const dir = sortDir.value === 'asc' ? 1 : -1

  let va = a[key]
  let vb = b[key]

  if (key === 'purchaseDate') {
    // Missing dates sort last, regardless of direction.
    va = va ? new Date(va).getTime() : Number.POSITIVE_INFINITY
    vb = vb ? new Date(vb).getTime() : Number.POSITIVE_INFINITY
  } else {
    va = (va || '').toLowerCase()
    vb = (vb || '').toLowerCase()
  }

  if (va < vb) return -1 * dir
  if (va > vb) return 1 * dir
  return 0
}

const sortedDevices = computed(() => {
  if (!sortKey.value) return filteredDevices.value
  return [...filteredDevices.value].sort(compareDevices)
})

// --- Rental engine (Rent / Return) -----------------------------------------

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
      : { label: 'In Use', disabled: true, variant: 'disabled', handler: null }
  }
  if (device.status === 'Repair') {
    return { label: 'In Repair', disabled: true, variant: 'disabled', handler: null }
  }
  return { label: 'Unavailable', disabled: true, variant: 'disabled', handler: null }
}

const rows = computed(() => sortedDevices.value.map((device) => ({ device, action: actionFor(device) })))

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
    await deviceApi.rent(device.id)
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

defineExpose({ scrollToDevice })
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-semibold text-gray-900">Hardware List</h1>

    <!-- Smart Dashboard toolbar: search + status + brand filters -->
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

    <div class="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table class="w-full text-left text-sm">
        <thead class="bg-gray-50 text-gray-500">
          <tr>
            <th class="px-5 py-3 font-medium">
              <button type="button" class="flex items-center gap-1 hover:text-gray-900" @click="toggleSort('name')">
                Device Name
                <svg v-if="sortKey === 'name'" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-180': sortDir === 'desc' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </th>
            <th class="px-5 py-3 font-medium">
              <button type="button" class="flex items-center gap-1 hover:text-gray-900" @click="toggleSort('brand')">
                Brand
                <svg v-if="sortKey === 'brand'" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-180': sortDir === 'desc' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </th>
            <th class="px-5 py-3 font-medium">
              <button type="button" class="flex items-center gap-1 hover:text-gray-900" @click="toggleSort('category')">
                Category
                <svg v-if="sortKey === 'category'" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-180': sortDir === 'desc' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </th>
            <th class="px-5 py-3 font-medium">
              <button type="button" class="flex items-center gap-1 hover:text-gray-900" @click="toggleSort('purchaseDate')">
                Date Added
                <svg v-if="sortKey === 'purchaseDate'" xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform" :class="{ 'rotate-180': sortDir === 'desc' }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 19V5M5 12l7-7 7 7" />
                </svg>
              </button>
            </th>
            <th class="px-5 py-3 font-medium">Status</th>
            <th class="px-5 py-3 text-right font-medium">Action</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-if="loading">
            <td colspan="6" class="px-5 py-6 text-center text-gray-400">Loading devices…</td>
          </tr>
          <tr v-else-if="rows.length === 0">
            <td colspan="6" class="px-5 py-6 text-center text-gray-400">No devices match the selected filters.</td>
          </tr>
          <tr
            v-for="row in rows"
            :id="'device-' + row.device.id"
            :key="row.device.id"
            class="text-gray-900"
            :class="{ highlight: highlightedId === row.device.id }"
          >
            <td class="px-5 py-3 font-medium">{{ row.device.name }}</td>
            <td class="px-5 py-3 text-gray-500">{{ row.device.brand || '—' }}</td>
            <td class="px-5 py-3 text-gray-500">{{ row.device.category || '—' }}</td>
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

<style scoped>
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
