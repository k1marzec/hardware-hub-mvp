const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

async function request(path, { method = 'GET', body } = {}) {
  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try {
      const data = await response.json()
      message = data.detail || message
    } catch {
      // response had no JSON body - keep the generic message
    }
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
  rent(id, email) {
    return request(`/devices/${id}/rent`, { method: 'POST', body: { email } })
  },
  return(id) {
    return request(`/devices/${id}/return`, { method: 'POST' })
  },
  myRentals(email) {
    return request(`/rentals?email=${encodeURIComponent(email)}`)
  },
}
