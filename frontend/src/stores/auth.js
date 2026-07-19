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
  const token = computed(() => state.session?.token ?? null)

  function setSession(session) {
    state.session = session
    localStorage.setItem(STORAGE_KEY, JSON.stringify(session))
  }

  function logout() {
    state.session = null
    localStorage.removeItem(STORAGE_KEY)
  }

  return { isAuthenticated, user, isAdmin, token, setSession, logout }
}

// Plain (non-reactive) accessor for the current token, for use outside of
// component/composable context - e.g. the `api.js` request helper, which
// needs to read it on every call but isn't itself a composable.
export function getToken() {
  return state.session?.token ?? null
}

// Lets the API layer react to a 401 (invalid/expired token) by dropping the
// stale session immediately, instead of leaving the user "logged in" client-side
// with a token the server no longer honors.
export function clearSession() {
  state.session = null
  localStorage.removeItem(STORAGE_KEY)
}
