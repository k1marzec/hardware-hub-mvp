<script setup>
import { nextTick, ref } from 'vue'

import AdminHardwareTab from '../components/AdminHardwareTab.vue'
import AdminUsersTab from '../components/AdminUsersTab.vue'
import AiHealthCheck from '../components/AiHealthCheck.vue'

const TABS = [
  { id: 'hardware', label: 'Hardware' },
  { id: 'users', label: 'Users' },
]

const activeTab = ref('hardware')
const hardwareTab = ref(null)
const aiHealthCheck = ref(null)

// The Inventory Auditor can flip a device's status/history/issue server-side
// (via "Create service history"); refresh the Hardware tab so the table
// reflects that immediately, even if it's the currently active tab.
function handleResolved() {
  hardwareTab.value?.loadDevices?.()
}

// Editing a device (e.g. reporting a new `issue`) updates the table in
// place - re-run the Inventory Auditor too, so a fresh issue tile appears on
// top of the dashboard immediately, without a full page reload.
function handleDevicesChanged() {
  aiHealthCheck.value?.runAudit?.()
}

// Jumps to a device's row from an Inventory Auditor tile's "locate" icon.
// Switches to the Hardware tab first if it isn't already active, then
// waits for it to mount before scrolling/highlighting the row.
async function handleLocate(deviceId) {
  activeTab.value = 'hardware'
  await nextTick()
  hardwareTab.value?.scrollToDevice?.(deviceId)
}
</script>

<template>
  <div>
    <h1 class="mb-6 text-2xl font-semibold text-gray-900">Admin Panel</h1>

    <AiHealthCheck ref="aiHealthCheck" @resolved="handleResolved" @locate="handleLocate" />

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

    <AdminHardwareTab
      v-if="activeTab === 'hardware'"
      ref="hardwareTab"
      @devices-changed="handleDevicesChanged"
    />
    <AdminUsersTab v-else />
  </div>
</template>
