import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { AuthUser, TokenResponse } from '../types'
import { authApi } from '../api/auth'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('hrms_token')
    const stored = localStorage.getItem('hrms_user')
    if (token && stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem('hrms_user')
      }
    }
    setIsLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const resp: TokenResponse = await authApi.login(email, password)
    localStorage.setItem('hrms_token', resp.access_token)
    const authUser: AuthUser = {
      id: resp.user_id,
      email: resp.email,
      full_name: resp.full_name,
      role: resp.role,
      company_id: resp.company_id,
      company_name: resp.company_name,
    }
    localStorage.setItem('hrms_user', JSON.stringify(authUser))
    setUser(authUser)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('hrms_token')
    localStorage.removeItem('hrms_user')
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
