import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { BookOpen, Headphones, PenLine, LogOut, User, LayoutDashboard, History } from 'lucide-react'

export default function Layout({ children }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navbar */}
      <nav className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-gray-900 font-semibold text-lg hover:text-green-700 transition-colors">
            <BookOpen className="w-5 h-5 text-green-600" />
            IELTS Practice
          </Link>

          {user && (
            <div className="flex items-center gap-4">
              <Link
                to="/"
                className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
              >
                <LayoutDashboard className="w-4 h-4" />
                <span className="hidden sm:inline">Dashboard</span>
              </Link>
              <Link
                to="/history"
                className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
              >
                <History className="w-4 h-4" />
                <span className="hidden sm:inline">History</span>
              </Link>
              {user.is_admin && (
                <Link
                  to="/admin"
                  className="text-sm text-gray-600 hover:text-gray-900 flex items-center gap-1"
                >
                  <User className="w-4 h-4" />
                  <span className="hidden sm:inline">Admin</span>
                </Link>
              )}
              <span className="text-sm text-gray-400 hidden md:inline">{user.email}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-gray-500 hover:text-red-600 flex items-center gap-1 transition-colors"
              >
                <LogOut className="w-4 h-4" />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Main content */}
      <main className="max-w-6xl mx-auto px-4 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-200 mt-auto py-6 text-center text-sm text-gray-400">
        IELTS Practice Platform &middot; Built with React + FastAPI
      </footer>
    </div>
  )
}
