<script setup>
import { reactive, watch } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'saved'])

const form = reactive({ email: '', password: '' })

// Always start from a blank form whenever the modal is (re)opened.
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      form.email = ''
      form.password = ''
    }
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
    <div class="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
      <div class="mb-5 flex items-start justify-between">
        <div>
          <h2 class="text-lg font-semibold text-gray-900">Create User</h2>
          <p class="text-sm text-gray-500">Grant a teammate access to the system</p>
        </div>
        <button type="button" class="text-gray-400 hover:text-gray-600" @click="close">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Email</label>
          <input
            v-model="form.email"
            required
            type="email"
            placeholder="name@booksy.com"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-700">Password</label>
          <input
            v-model="form.password"
            required
            type="password"
            placeholder="Enter a password"
            class="w-full rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
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
            Create User
          </button>
        </div>
      </form>
    </div>
  </div>
</template>
