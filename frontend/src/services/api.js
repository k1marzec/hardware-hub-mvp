import { clearSession, getToken } from '../stores/auth'

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function request(path, { method = 'GET', body } = {}) {
  const token = getToken()
  const headers = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      if (Array.isArray(data.detail)) {
        // FastAPI/Pydantic validation errors (422) come back as a list of
        // {loc, msg, ...} objects, not a plain string - stitch them into
        // one readable message instead of showing "[object Object]".
        message = data.detail.map((item) => item.msg || JSON.stringify(item)).join('; ')
      } else if (data.detail) {
        message = data.detail
      }
    } catch {
      // response had no JSON body - keep the generic message
    }

    // The server no longer honors this token (expired/invalid, or the
    // account was removed) - drop the stale client-side session so the
    // next navigation naturally bounces back to /login via the router
    // guard, instead of leaving the UI "logged in" but unable to do anything.
    if (response.status === 401) clearSession()

    throw new Error(message)
  }

  if (response.status === 204) return null
  return response.json()
}

export const authApi = {
  login(email, password) {
    return request('/auth/login', { method: 'POST', body: { email, password } })
  },
}

export const auditorApi = {
  run() {
    return request('/auditor/run')
  },
  resolveIssue(deviceId) {
    return request(`/devices/${deviceId}/resolve-issue`, { method: 'POST' })
  },
}

export const userApi = {
  list() {
    return request('/users')
  },
  create(email, password, role = 'user') {
    return request('/users', { method: 'POST', body: { email, password, role } })
  },
}

export const deviceApi = {
  list() {
    return request('/devices')
  },
  get(id) {
    return request(`/devices/${id}`)
  },
  create(payload) {
    return request('/devices', { method: 'POST', body: payload })
  },
  update(id, payload) {
    return request(`/devices/${id}`, { method: 'PUT', body: payload })
  },
  remove(id) {
    return request(`/devices/${id}`, { method: 'DELETE' })
  },
  sendToRepair(id) {
    return request(`/devices/${id}/repair`, { method: 'PATCH' })
  },
  restoreFromRepair(id) {
    return request(`/devices/${id}/restore`, { method: 'PATCH' })
  },
  rent(id) {
    // Who is renting is derived server-side from the auth token, never
    // sent by the client - see backend/main.py::rent_device.
    return request(`/devices/${id}/rent`, { method: 'POST' })
  },
  return(id) {
    return request(`/devices/${id}/return`, { method: 'POST' })
  },
  myRentals() {
    // Always "my" rentals - the server infers the caller from the auth
    // token (see backend/main.py::my_rentals), so there's no email to pass.
    return request('/rentals')
  },
}
