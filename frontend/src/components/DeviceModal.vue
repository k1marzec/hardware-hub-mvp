<script setup>
import { computed, reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  device: { type: Object, default: null },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const CATEGORIES = ['Laptop', 'Phone', 'Tablet', 'Monitor', 'Keyboard', 'Mouse', 'Headphones', 'Other']

const isEditing = computed(() => !!props.device)

const form = reactive({
  name: '',
  serialNumber: '',
  brand: '',
  category: '',
  issue: '',
  notes: '',
  history: '',
})

function resetForm(device) {
  form.name = device?.name ?? ''
  form.serialNumber = device?.serialNumber ?? ''
  form.brand = device?.brand ?? ''
  form.category = device?.category ?? ''
  form.issue = device?.issue ?? ''
  form.notes = device?.notes ?? ''
  form.history = device?.history ?? ''
}

watch(() => props.device, resetForm, { immediate: true })

// Also reset to a blank form whenever the modal re-opens for "Add" mode.
watch(
  () => props.modelValue,
  (open) => {
    if (open && !props.device) resetForm(null)
  },
)

function close() {
  emit('update:modelValue', false)
}

function submit() {
  emit('saved', { ...form })
}
</script>

<template>
  <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl max-h-[90vh] overflow-y-auto">
      <div class="mb-5 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">
            {{ isEditing ? 'Edit Device' : 'Add New Device' }}
          </h2>
          <p class="text-sm text-gray-500">
            Enter the details of the {{ isEditing ? '' : 'new ' }}hardware device
          </p>
        </div>
        <button type="button" class="text-gray-400 hover:text-gray-600" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Name</label>
          <input
            v-model="form.name"
            required
            type="text"
            placeholder="e.g., MacBook Pro 16"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Serial Number</label>
          <input
            v-model="form.serialNumber"
            type="text"
            placeholder="e.g., MBP-2024-001"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Brand</label>
          <input
            v-model="form.brand"
            type="text"
            placeholder="e.g., Apple"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Category</label>
          <select
            v-model="form.category"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 outline-none focus:ring-2 focus:ring-gray-300"
          >
            <option value="" disabled>Select a category</option>
            <option v-for="cat in CATEGORIES" :key="cat" :value="cat">{{ cat }}</option>
          </select>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Issue</label>
          <textarea
            v-model="form.issue"
            rows="2"
            placeholder="e.g., Battery swelling, do not issue without service."
            class="w-full resize-none rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
          <p class="mt-1 text-xs text-gray-400">
          </p>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Notes</label>
          <textarea
            v-model="form.notes"
            rows="2"
            placeholder="e.g., internal remarks, warranty info…"
            class="w-full resize-none rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
          <p class="mt-1 text-xs text-gray-400">
          </p>
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">History</label>
          <textarea
            v-model="form.history"
            rows="3"
            placeholder="e.g., Returned by user with liquid damage. Keyboard sticky."
            class="w-full resize-none rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <button
            type="button"
            class="rounded-lg px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100"
            @click="close"
          >
            Cancel
          </button>
          <button
            type="submit"
            class="rounded-lg bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-black"
          >
            {{ isEditing ? 'Save Changes' : 'Add Device' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
