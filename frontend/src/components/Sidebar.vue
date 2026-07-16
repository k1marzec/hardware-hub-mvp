<script setup>
import { useRoute, useRouter } from 'vue-router'

import { useAuth } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const { user, isAdmin, logout } = useAuth()

function isActive(path) {
  return route.path.startsWith(path)
}

function handleLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <aside class="flex w-60 shrink-0 flex-col border-r border-gray-200 bg-white">
    <div class="flex items-center gap-2 border-b border-gray-100 px-5 py-5">
      <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-gray-100">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
          <path d="M3.27 6.96 12 12.01l8.73-5.05" />
          <path d="M12 22.08V12" />
        </svg>
      </div>
      <span class="font-semibold text-gray-900">Hardware Manager</span>
    </div>

    <nav class="flex-1 space-y-1 px-3 py-4">
      <router-link
        to="/hardware"
        class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition"
        :class="isActive('/hardware') ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01" />
        </svg>
        Hardware List
      </router-link>

      <router-link
        to="/rentals"
        class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition"
        :class="isActive('/rentals') ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v5l3 3" />
        </svg>
        My Rentals
      </router-link>

      <router-link
        v-if="isAdmin"
        to="/admin"
        class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition"
        :class="isActive('/admin') ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:bg-gray-50 hover:text-gray-900'"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="3" />
          <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h0A1.65 1.65 0 0 0 10 3.09V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v0a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1Z" />
        </svg>
        Admin Panel
      </router-link>
    </nav>

    <div class="border-t border-gray-100 px-3 py-4">
      <div class="truncate px-3 pb-2 text-xs text-gray-400">{{ user?.email }}</div>
      <button
        class="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-gray-500 transition hover:bg-gray-50 hover:text-gray-900"
        @click="handleLogout"
      >
        Logout
      </button>
    </div>
  </aside>
</template>
