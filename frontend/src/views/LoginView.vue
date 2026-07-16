<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { authApi } from '../services/api'
import { useAuth } from '../stores/auth'

const router = useRouter()
const { setSession } = useAuth()

const form = reactive({ email: '', password: '' })
const domainError = ref('')
const formError = ref('')
const loading = ref(false)

function validateDomain() {
  if (form.email && !form.email.toLowerCase().endsWith('@booksy.com')) {
    domainError.value = 'Invalid domain. Please use @booksy.com'
  } else {
    domainError.value = ''
  }
}

async function handleSubmit() {
  validateDomain()
  if (domainError.value) return

  formError.value = ''
  loading.value = true
  try {
    const { user, token } = await authApi.login(form.email, form.password)
    setSession({ user, token })
    router.push('/hardware')
  } catch (err) {
    formError.value = err.message || 'Unable to sign in. Please try again.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-gray-50 px-4">
    <div class="w-full max-w-sm rounded-2xl bg-white p-8 shadow-sm">
      <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-gray-100">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6 text-gray-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
          <path d="M3.27 6.96 12 12.01l8.73-5.05" />
          <path d="M12 22.08V12" />
        </svg>
      </div>

      <h1 class="text-center text-xl font-semibold text-gray-900">Welcome back</h1>
      <p class="mb-6 text-center text-sm text-gray-500">Sign in to your account</p>

      <form class="space-y-4" @submit.prevent="handleSubmit">
        <div>
          <label class="mb-1 block text-sm font-medium text-gray-900">Email (company domain only)</label>
          <input
            v-model="form.email"
            type="email"
            placeholder="name@booksy.com"
            class="w-full rounded-lg bg-gray-100 px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
            @blur="validateDomain"
            @input="domainError = ''"
          />
          <p v-if="domainError" class="mt-1 text-sm text-red-600">{{ domainError }}</p>
        </div>

        <div>
          <label class="mb-1 block text-sm font-medium text-gray-900">Password</label>
          <input
            v-model="form.password"
            type="password"
            placeholder="Enter your password"
            class="w-full rounded-lg bg-gray-100 px-3 py-2.5 text-sm text-gray-900 placeholder-gray-400 outline-none focus:ring-2 focus:ring-gray-300"
          />
        </div>

        <p v-if="formError" class="text-sm text-red-600">{{ formError }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full rounded-lg bg-gray-900 py-2.5 text-sm font-semibold text-white transition hover:bg-black disabled:opacity-60"
        >
          {{ loading ? 'Signing in…' : 'Login' }}
        </button>
      </form>

      <p class="mt-4 text-center text-xs text-gray-400">Demo admin: demo@booksy.com / demo123</p>
    </div>
  </div>
</template>
