import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../stores/auth', () => ({
  getToken: vi.fn(),
  clearSession: vi.fn(),
}))

import { clearSession, getToken } from '../stores/auth'
import { authApi, deviceApi } from './api'

function jsonResponse(body, { status = 200 } = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  }
}

describe('api.js request helper', () => {
  beforeEach(() => {
    getToken.mockReset().mockReturnValue(null)
    clearSession.mockReset()
    global.fetch = vi.fn()
  })

  it('sends no Authorization header when there is no token', async () => {
    global.fetch.mockResolvedValue(jsonResponse([]))

    await deviceApi.list()

    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers.Authorization).toBeUndefined()
  })

  it('attaches Authorization: Bearer <token> when a token is present', async () => {
    getToken.mockReturnValue('signed-token')
    global.fetch.mockResolvedValue(jsonResponse([]))

    await deviceApi.list()

    const [, options] = global.fetch.mock.calls[0]
    expect(options.headers.Authorization).toBe('Bearer signed-token')
  })

  it('rejects with the server-provided detail message on error responses', async () => {
    global.fetch.mockResolvedValue(jsonResponse({ detail: 'Invalid email or password' }, { status: 401 }))

    await expect(authApi.login('x@booksy.com', 'wrong')).rejects.toThrow('Invalid email or password')
  })

  it('stitches FastAPI 422 validation error arrays into one readable message', async () => {
    global.fetch.mockResolvedValue(
      jsonResponse(
        { detail: [{ msg: 'String should have at least 8 characters' }, { msg: 'Field required' }] },
        { status: 422 },
      ),
    )

    await expect(authApi.login('x@booksy.com', 'short')).rejects.toThrow(
      'String should have at least 8 characters; Field required',
    )
  })

  it('clears the stored session on a 401 response', async () => {
    global.fetch.mockResolvedValue(jsonResponse({ detail: 'Invalid or expired session token' }, { status: 401 }))

    await expect(deviceApi.list()).rejects.toThrow()
    expect(clearSession).toHaveBeenCalledTimes(1)
  })

  it('does not clear the session on non-401 errors', async () => {
    global.fetch.mockResolvedValue(jsonResponse({ detail: 'Admin privileges required' }, { status: 403 }))

    await expect(deviceApi.list()).rejects.toThrow('Admin privileges required')
    expect(clearSession).not.toHaveBeenCalled()
  })

  it('rent() posts with no request body - the server derives the renter from the token', async () => {
    global.fetch.mockResolvedValue(jsonResponse({ id: 1, status: 'In Use' }))

    await deviceApi.rent(1)

    const [url, options] = global.fetch.mock.calls[0]
    expect(url).toContain('/devices/1/rent')
    expect(options.method).toBe('POST')
    expect(options.body).toBeUndefined()
  })

  it('returns null for a 204 No Content response instead of parsing a (nonexistent) body', async () => {
    global.fetch.mockResolvedValue({ ok: true, status: 204 })

    await expect(deviceApi.remove(1)).resolves.toBe(null)
  })
})
