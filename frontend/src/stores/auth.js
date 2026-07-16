import { computed, reactive } from 'vue'

const STORAGE_KEY = 'hardware-hub-auth'

function loadFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

// Module-level state: acts as a tiny singleton store shared by every
// component that calls useAuth(), without needing an extra dependency
// like Pinia for this MVP.
const state = reactive({
  session: loadFromStorage(),
})

export function useAuth() {
  const isAuthenticated = computed(() => !!state.session)
  const user = computed(() => state.session?.user ?? null)
  const isAdmin = computed(() => state.session?.user?.role === 'admin')

  function setSession(session) {
    state.session = session
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  }

  function logout() {
    state.session = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return { isAuthenticated, user, isAdmin, setSession, logout }
}
