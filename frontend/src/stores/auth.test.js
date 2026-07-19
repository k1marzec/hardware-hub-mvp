import { beforeEach, describe, expect, it, vi } from 'vitest'

// `stores/auth.js` keeps a module-level singleton (`state`), initialized
// from `localStorage` at import time - so each test needs both a clean
// `localStorage` AND a fresh module instance (via `vi.resetModules()` +
// re-import) to be properly isolated from the others.
async function freshAuthModule() {
  vi.resetModules()
  return import('./auth')
}

describe('useAuth store', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts unauthenticated when localStorage is empty', async () => {
    const { useAuth } = await freshAuthModule()
    const { isAuthenticated, user, isAdmin, token } = useAuth()

    expect(isAuthenticated.value).toBe(false)
    expect(user.value).toBe(null)
    expect(isAdmin.value).toBe(false)
    expect(token.value).toBe(null)
  })

  it('setSession updates all computed values and persists to localStorage', async () => {
    const { useAuth, getToken } = await freshAuthModule()
    const { setSession, isAuthenticated, user, isAdmin, token } = useAuth()

    setSession({ user: { id: 1, email: 'admin@booksy.com', role: 'admin' }, token: 'signed-token' })

    expect(isAuthenticated.value).toBe(true)
    expect(user.value.email).toBe('admin@booksy.com')
    expect(isAdmin.value).toBe(true)
    expect(token.value).toBe('signed-token')
    expect(getToken()).toBe('signed-token')
    expect(JSON.parse(localStorage.getItem('hardware-hub-auth')).token).toBe('signed-token')
  })

  it('a "user"-role session is not an admin session', async () => {
    const { useAuth } = await freshAuthModule()
    const { setSession, isAdmin } = useAuth()

    setSession({ user: { id: 2, email: 'user@booksy.com', role: 'user' }, token: 't' })

    expect(isAdmin.value).toBe(false)
  })

  it('logout clears both the reactive state and localStorage', async () => {
    const { useAuth, getToken } = await freshAuthModule()
    const { setSession, logout, isAuthenticated } = useAuth()
    setSession({ user: { id: 1, email: 'user@booksy.com', role: 'user' }, token: 't' })

    logout()

    expect(isAuthenticated.value).toBe(false)
    expect(getToken()).toBe(null)
    expect(localStorage.getItem('hardware-hub-auth')).toBe(null)
  })

  it('clearSession (used by api.js on a 401) drops a stale session the same way logout() does', async () => {
    const { useAuth, clearSession, getToken } = await freshAuthModule()
    const { setSession, isAuthenticated } = useAuth()
    setSession({ user: { id: 1, email: 'x@booksy.com', role: 'user' }, token: 't' })

    clearSession()

    expect(isAuthenticated.value).toBe(false)
    expect(getToken()).toBe(null)
  })

  it('rehydrates an existing session from localStorage on module load', async () => {
    localStorage.setItem(
      'hardware-hub-auth',
      JSON.stringify({ user: { id: 2, email: 'restored@booksy.com', role: 'user' }, token: 'restored-token' }),
    )

    const { useAuth } = await freshAuthModule()
    const { isAuthenticated, user, token } = useAuth()

    expect(isAuthenticated.value).toBe(true)
    expect(user.value.email).toBe('restored@booksy.com')
    expect(token.value).toBe('restored-token')
  })

  it('falls back to an empty session if localStorage holds invalid JSON', async () => {
    localStorage.setItem('hardware-hub-auth', 'not-valid-json{')

    const { useAuth } = await freshAuthModule()
    const { isAuthenticated } = useAuth()

    expect(isAuthenticated.value).toBe(false)
  })
})
