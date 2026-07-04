import { createContext, useContext, useState, useCallback, useEffect } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => {
    // Fallback: restore from localStorage if available
    try {
      return localStorage.getItem('ielts_token') || null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)

  // Verify token on mount
  useEffect(() => {
    if (token) {
      fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => {
          if (!res.ok) throw new Error('Invalid token')
          return res.json()
        })
        .then((data) => {
          setUser(data)
          setLoading(false)
        })
        .catch(() => {
          setToken(null)
          setUser(null)
          try { localStorage.removeItem('ielts_token') } catch {}
          setLoading(false)
        })
    } else {
      setLoading(false)
    }
  }, [token])

  const login = useCallback(async (email, password) => {
    const res = await fetch(`${API_BASE}/api/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }))
      throw new Error(err.detail || 'Login failed')
    }
    const data = await res.json()
    setToken(data.access_token)
    try { localStorage.setItem('ielts_token', data.access_token) } catch {}
    // Fetch user info
    const meRes = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` },
    })
    const userData = await meRes.json()
    setUser(userData)
  }, [])

  const register = useCallback(async (email, password) => {
    const res = await fetch(`${API_BASE}/api/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }))
      throw new Error(err.detail || 'Registration failed')
    }
    // Don't auto-login - user needs to verify email first
    // The Register page will handle the verification flow
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
    try { localStorage.removeItem('ielts_token') } catch {}
  }, [])

  const apiFetch = useCallback(async (path, options = {}) => {
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
    if (res.status === 401) {
      logout()
      throw new Error('Session expired. Please log in again.')
    }
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Request failed' }))
      throw new Error(err.detail || 'Request failed')
    }
    return res.json()
  }, [token, logout])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout, apiFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
