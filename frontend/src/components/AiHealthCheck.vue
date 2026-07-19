<script setup>
import { onMounted, ref } from 'vue'

import { auditorApi } from '../services/api'

const emit = defineEmits(['resolved', 'locate'])

const loading = ref(true)
const error = ref('')
const categories = ref([])
const dismissed = ref(false)

const busyDeviceId = ref(null)
const issueError = ref('')

async function runAudit() {
  loading.value = true
  error.value = ''
  issueError.value = ''
  dismissed.value = false
  try {
    const data = await auditorApi.run()
    // Stamp a stable, index-free key onto each issue up front so
    // <TransitionGroup> can track tiles by identity even after the array is
    // spliced (an index-based key would shift and break the leave animation).
    categories.value = (data.categories || []).map((category, ci) => ({
      ...category,
      issues: (category.issues || []).map((issue, ii) => ({ ...issue, _key: `${ci}-${ii}` })),
    }))
  } catch (err) {
    error.value = err.message || 'The Inventory Auditor is temporarily unavailable.'
  } finally {
    loading.value = false
  }
}

function dismiss() {
  dismissed.value = true
}

// Local State Mutation: rebuild `categories` by filtering the resolved tile
// out (by its stable `_key`), rather than re-fetching the whole audit report
// from the server. This is what lets the tile disappear immediately/in
// real-time, with <TransitionGroup> below animating the removal.
function removeIssue(issue) {
  categories.value = categories.value
    .map((category) => ({
      ...category,
      issues: category.issues.filter((candidate) => candidate._key !== issue._key),
    }))
    .filter((category) => category.issues.length > 0)
}

// "Create service history" / Predictive Maintenance: instead of just reporting
// the anomaly, ask the AI to triage it and flip the device into a real repair
// workflow (status -> Repair, issue cleared, history stamped).
async function resolveIssue(issue) {
  if (!issue.device_id || busyDeviceId.value) return

  busyDeviceId.value = issue.device_id
  issueError.value = ''
  try {
    await auditorApi.resolveIssue(issue.device_id)
    removeIssue(issue)
    emit('resolved')
  } catch (err) {
    issueError.value = err.message || 'Failed to create service history via AI.'
  } finally {
    busyDeviceId.value = null
  }
}

// Lets the parent view jump the currently-visible hardware table to this
// issue's device row (see scrollToDevice in AdminHardwareTab.vue).
function locateDevice(issue) {
  if (!issue.device_id) return
  emit('locate', issue.device_id)
}

onMounted(runAudit)

defineExpose({ runAudit })
</script>

<template>
  <div v-if="!dismissed" class="mb-6">
    <!-- Loading state -->
    <div
      v-if="loading"
      class="flex items-center gap-3 rounded-xl border border-indigo-100 bg-indigo-50 px-4 py-4 text-sm text-indigo-700"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M21 12a9 9 0 1 1-9-9" />
      </svg>
      AI is analyzing inventory records…
    </div>

    <!-- Error state -->
    <div
      v-else-if="error"
      class="flex items-start gap-3 rounded-xl border border-red-100 bg-red-50 px-4 py-4 text-sm text-red-700"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="mt-0.5 h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M12 9v4m0 4h.01M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      </svg>
      <p class="flex-1">{{ error }}</p>
      <button type="button" class="font-medium text-red-700 hover:text-red-900" @click="runAudit">Retry</button>
      <button type="button" class="text-red-400 hover:text-red-600" title="Dismiss" @click="dismiss">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Report card -->
    <div v-else class="rounded-xl border border-indigo-100 bg-indigo-50/60 px-5 py-4">
      <div class="mb-3 flex items-center justify-between gap-3">
        <h2 class="flex items-center gap-2 text-sm font-semibold text-indigo-900">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 shrink-0 text-indigo-500" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2l1.6 4.8L18 8l-4.4 1.2L12 14l-1.6-4.8L6 8l4.4-1.2L12 2Z" />
          </svg>
          Inventory Auditor
        </h2>
        <div class="flex items-center gap-3 text-indigo-400">
          <button type="button" class="hover:text-indigo-700" title="Re-run" @click="runAudit">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 1 1-2.64-6.36M21 3v6h-6" />
            </svg>
          </button>
          <button type="button" class="hover:text-indigo-700" title="Dismiss" @click="dismiss">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>

      <p v-if="categories.length === 0" class="text-sm text-gray-600">
        No anomalies detected. Inventory looks healthy.
      </p>

      <TransitionGroup v-else name="category" tag="div" class="space-y-5">
        <div v-for="category in categories" :key="category.title">
          <h3 class="mb-2 text-xs font-semibold uppercase tracking-wide text-indigo-700/80">
            {{ category.title }}
          </h3>
          <TransitionGroup name="list" tag="div" class="relative space-y-2">
            <div
              v-for="issue in category.issues"
              :key="issue._key"
              class="flex items-start justify-between gap-3 rounded-lg border border-indigo-100 bg-white px-4 py-3"
            >
              <div class="flex-1">
                <p v-if="issue.device_id" class="mb-0.5 text-xs font-semibold text-gray-500">
                  {{ issue.device_name || `Device #${issue.device_id}` }}
                </p>
                <p class="text-sm text-gray-800">{{ issue.description }}</p>
              </div>
              <div class="flex shrink-0 items-center gap-2">
                <button
                  v-if="issue.device_id"
                  type="button"
                  title="Find in table"
                  class="rounded-lg p-1.5 text-indigo-400 hover:bg-indigo-50 hover:text-indigo-700"
                  @click="locateDevice(issue)"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8" />
                    <path d="m21 21-4.3-4.3" />
                  </svg>
                </button>
                <button
                  v-if="issue.actionable && issue.device_id"
                  type="button"
                  :disabled="busyDeviceId === issue.device_id"
                  class="whitespace-nowrap rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
                  @click="resolveIssue(issue)"
                >
                  {{ busyDeviceId === issue.device_id ? 'Create history...' : 'Create service history' }}
                </button>
              </div>
            </div>
          </TransitionGroup>
        </div>
      </TransitionGroup>

      <p v-if="issueError" class="mt-3 text-sm text-red-600">{{ issueError }}</p>
    </div>
  </div>
</template>

<style scoped>
/* Tile-level transition: a resolved issue's tile fades + slides out (and the
   tiles below it smoothly slide up into the freed space) instead of just
   vanishing when it's filtered out of `categories` in real time. */
.list-enter-active,
.list-leave-active {
  transition: all 0.5s ease;
}
.list-enter-from,
.list-leave-to {
  opacity: 0;
  transform: translateY(30px);
}
/* Taking the leaving tile out of the flow is what lets the *remaining*
   tiles animate into their new position instead of jumping there instantly. */
.list-leave-active {
  position: absolute;
  width: 100%;
}

/* Category-level transition: once a category's last tile is resolved and
   removed, its (now-empty) section fades out too, instead of the heading
   abruptly disappearing. */
.category-leave-active {
  transition: opacity 0.4s ease;
}
.category-leave-to {
  opacity: 0;
}
</style>
