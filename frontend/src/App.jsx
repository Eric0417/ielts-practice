import { Routes, Route, Navigate, useParams } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import AdminRoute from './components/AdminRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import PracticeList from './pages/PracticeList'
import ObjectivePractice from './pages/ObjectivePractice'
import WritingPractice from './pages/WritingPractice'
import HistoryPage from './pages/History'
import AdminPage from './pages/Admin'

function PracticeRouter() {
  const { type, book, test } = useParams()
  if (type === 'writing-task1' || type === 'writing-task2') {
    return <WritingPractice />
  }
  return <ObjectivePractice />
}

function AppRoutes() {
  const { user } = useAuth()

  return (
    <Routes>
      {/* Public routes */}
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route path="/register" element={user ? <Navigate to="/" replace /> : <Register />} />

      {/* Protected routes */}
      <Route path="/" element={<ProtectedRoute><Layout><Dashboard /></Layout></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><Layout><HistoryPage /></Layout></ProtectedRoute>} />
      <Route path="/admin" element={<AdminRoute><Layout><AdminPage /></Layout></AdminRoute>} />

      {/* Practice — type list */}
      <Route path="/practice/:type" element={<ProtectedRoute><Layout><PracticeList /></Layout></ProtectedRoute>} />

      {/* Practice — specific test (flat layout: /practice/:type/:test) */}
      <Route path="/practice/:type/:test" element={<ProtectedRoute><Layout><PracticeRouter /></Layout></ProtectedRoute>} />

      {/* Catch-all */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  )
}
