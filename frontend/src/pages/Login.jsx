import { useState, useEffect } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LogIn, UserPlus, Mail, Lock, AlertCircle, KeyRound, ArrowLeft } from 'lucide-react'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [message, setMessage] = useState(
    searchParams.get('verified') === '1' ? 'Email verified! Please log in.' :
    searchParams.get('reset') === 'ok' ? 'Password reset successfully. Please log in.' : ''
  )
  const [submitting, setSubmitting] = useState(false)

  // Forgot password flow
  const [showForgotPassword, setShowForgotPassword] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotSent, setForgotSent] = useState(false)
  const [forgotError, setForgotError] = useState('')

  // Reset password flow (with token)
  const [showResetForm, setShowResetForm] = useState(!!searchParams.get('token'))
  const [resetToken, setResetToken] = useState(searchParams.get('token') || '')
  const [resetPassword, setResetPassword] = useState('')
  const [resetError, setResetError] = useState('')
  const [resetDone, setResetDone] = useState(false)

  const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(email, password)
      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleForgotPassword = async (e) => {
    e.preventDefault()
    setForgotError('')
    try {
      const res = await fetch(`${API_BASE}/api/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: forgotEmail }),
      })
      const data = await res.json()
      if (res.ok) {
        setForgotSent(true)
        // If dev mode returns the token directly, pre-fill it
        if (data.reset_token) {
          setResetToken(data.reset_token)
        }
      } else {
        setForgotError(data.detail || 'Failed to send reset email')
      }
    } catch {
      setForgotError('Network error. Please try again.')
    }
  }

  const handleResetPassword = async (e) => {
    e.preventDefault()
    setResetError('')
    try {
      const res = await fetch(`${API_BASE}/api/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token: resetToken, new_password: resetPassword }),
      })
      if (res.ok) {
        setResetDone(true)
      } else {
        const data = await res.json()
        setResetError(data.detail || 'Reset failed')
      }
    } catch {
      setResetError('Network error. Please try again.')
    }
  }

  // Reset password form (from email link)
  if (showResetForm) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-100 mb-4">
              <KeyRound className="w-6 h-6 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Reset Password</h1>
            <p className="text-gray-500 mt-1">Enter your new password</p>
          </div>

          {resetDone ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 text-center">
              <div className="text-green-600 font-medium mb-3">Password reset successfully!</div>
              <Link to="/login" className="text-sm text-green-600 hover:text-green-700 font-medium">
                Go to login
              </Link>
            </div>
          ) : (
            <form onSubmit={handleResetPassword} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
              {resetError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />{resetError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reset Token</label>
                <input type="text" required value={resetToken}
                  onChange={(e) => setResetToken(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Paste reset token from email" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">New Password</label>
                <input type="password" required value={resetPassword}
                  onChange={(e) => setResetPassword(e.target.value)}
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                  placeholder="Min. 6 characters" minLength={6} />
              </div>
              <button type="submit"
                className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors">
                Reset Password
              </button>
              <button type="button" onClick={() => { setShowResetForm(false); setShowForgotPassword(false) }}
                className="w-full text-sm text-gray-500 hover:text-gray-700">
                Back to login
              </button>
            </form>
          )}
        </div>
      </div>
    )
  }

  // Forgot password form
  if (showForgotPassword) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-100 mb-4">
              <KeyRound className="w-6 h-6 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Forgot Password</h1>
            <p className="text-gray-500 mt-1">Enter your email to receive a reset link</p>
          </div>

          {forgotSent ? (
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
              <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                Reset link sent! Check your email.
              </div>
              {resetToken && (
                <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                  <p className="text-xs text-amber-700 font-medium mb-1">Dev mode — reset token:</p>
                  <code className="text-xs text-amber-800 break-all">{resetToken}</code>
                </div>
              )}
              <button onClick={() => setShowResetForm(true)}
                className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors">
                I have my reset token
              </button>
              <button onClick={() => { setShowForgotPassword(false); setForgotSent(false) }}
                className="w-full text-sm text-gray-500 hover:text-gray-700">
                Back to login
              </button>
            </div>
          ) : (
            <form onSubmit={handleForgotPassword} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
              {forgotError && (
                <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 flex-shrink-0" />{forgotError}
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input type="email" required value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    className="w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                    placeholder="you@example.com" />
                </div>
              </div>
              <button type="submit"
                className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors">
                Send Reset Link
              </button>
              <button type="button" onClick={() => setShowForgotPassword(false)}
                className="w-full text-sm text-gray-500 hover:text-gray-700">
                Back to login
              </button>
            </form>
          )}
        </div>
      </div>
    )
  }

  // Normal login form
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-green-100 mb-4">
            <LogIn className="w-6 h-6 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Welcome back</h1>
          <p className="text-gray-500 mt-1">Sign in to your IELTS practice account</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
          {message && (
            <div className="flex items-center gap-2 p-3 bg-green-50 border border-green-200 rounded-lg text-sm text-green-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />{message}
            </div>
          )}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="you@example.com" />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full pl-10 pr-3 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="••••••••" />
            </div>
          </div>

          <div className="text-right">
            <button type="button" onClick={() => setShowForgotPassword(true)}
              className="text-xs text-green-600 hover:text-green-700">
              Forgot password?
            </button>
          </div>

          <button type="submit" disabled={submitting}
            className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors">
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Don&apos;t have an account?{' '}
          <Link to="/register" className="text-green-600 hover:text-green-700 font-medium">Create one</Link>
        </p>
      </div>
    </div>
  )
}
