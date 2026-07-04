import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { UserPlus, Mail, Lock, AlertCircle, ShieldCheck } from 'lucide-react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''

export default function Register() {
  const navigate = useNavigate()
  const [step, setStep] = useState('register') // 'register' | 'verify'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')

    if (password.length < 6) {
      setError('Password must be at least 6 characters.')
      return
    }

    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Registration failed')
      }
      // Registration successful — show verification code (dev fallback only)
      if (data.verification_code) {
        setCode(data.verification_code)
      }
      setStep('verify')
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleVerify = async (e) => {
    e.preventDefault()
    setError('')

    if (code.length !== 6) {
      setError('Verification code must be 6 digits.')
      return
    }

    setSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/api/auth/verify-email`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      })
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.detail || 'Verification failed')
      }
      // Verified — redirect to login
      navigate('/login?verified=1', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  const handleResendCode = async () => {
    setError('')
    try {
      const res = await fetch(`${API_BASE}/api/auth/resend-verification?email=${encodeURIComponent(email)}`, {
        method: 'POST',
      })
      const data = await res.json()
      if (res.ok) {
        if (data.verification_code) {
          setCode(data.verification_code)
        }
        setError('New code sent! Check your email.')
      } else {
        setError(data.detail || 'Failed to resend code')
      }
    } catch {
      setError('Network error. Please try again.')
    }
  }

  // Verification step
  if (step === 'verify') {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="w-full max-w-sm">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-blue-100 mb-4">
              <ShieldCheck className="w-6 h-6 text-blue-600" />
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Verify your email</h1>
            <p className="text-gray-500 mt-1">
              A 6-digit code has been sent to <strong>{email}</strong>. Please check your inbox.
            </p>
            {code && (
              <div className="mt-3 p-3 bg-amber-50 border border-amber-200 rounded-lg">
                <p className="text-xs text-amber-600 font-medium">Dev fallback — code:</p>
                <p className="text-2xl font-mono font-bold text-amber-800 tracking-[0.3em]">{code}</p>
              </div>
            )}
          </div>

          <form onSubmit={handleVerify} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
            {error && (
              <div className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                error.includes('Check your email') || error.includes('sent')
                  ? 'bg-green-50 border border-green-200 text-green-700'
                  : 'bg-red-50 border border-red-200 text-red-700'
              }`}>
                <AlertCircle className="w-4 h-4 flex-shrink-0" />{error}
              </div>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Verification Code</label>
              <input
                type="text"
                required
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-lg text-sm text-center tracking-[0.5em] font-mono text-lg focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                placeholder="000000"
                maxLength={6}
                autoFocus
              />
            </div>

            <button type="submit" disabled={submitting || code.length !== 6}
              className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors">
              {submitting ? 'Verifying...' : 'Verify Email'}
            </button>

            <div className="text-center">
              <button type="button" onClick={handleResendCode}
                className="text-xs text-green-600 hover:text-green-700">
                Resend verification code
              </button>
            </div>

            <div className="text-center">
              <button type="button" onClick={() => setStep('register')}
                className="text-xs text-gray-500 hover:text-gray-700">
                Back to registration
              </button>
            </div>
          </form>
        </div>
      </div>
    )
  }

  // Registration step
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-green-100 mb-4">
            <UserPlus className="w-6 h-6 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">Create account</h1>
          <p className="text-gray-500 mt-1">Start practicing for your IELTS exam</p>
        </div>

        <form onSubmit={handleRegister} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-4">
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
                placeholder="Min. 6 characters" minLength={6} />
            </div>
          </div>

          <button type="submit" disabled={submitting}
            className="w-full py-2.5 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors">
            {submitting ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          Already have an account?{' '}
          <Link to="/login" className="text-green-600 hover:text-green-700 font-medium">Sign in</Link>
        </p>
      </div>
    </div>
  )
}
