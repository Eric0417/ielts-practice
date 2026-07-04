import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { History, BookOpen, Headphones, PenLine, ChevronRight } from 'lucide-react'

const typeIcons = {
  reading: BookOpen,
  listening: Headphones,
  writing: PenLine,
}

function formatQuestionId(qid) {
  if (!qid) return ''
  // New v2 compound ID: "cambridge17/test1/reading"
  const parts = qid.split('/')
  if (parts.length === 3) {
    const [book, testPart, type] = parts
    const bookNum = book.replace('cambridge', '')
    const testNum = testPart.replace('test', '')
    return `Cambridge ${bookNum} Test ${testNum} - ${type.charAt(0).toUpperCase() + type.slice(1)}`
  }
  // Legacy ID: "reading-passage-001" → pass through
  if (qid.includes('-')) {
    return qid
  }
  return qid
}

export default function HistoryPage() {
  const { apiFetch } = useAuth()
  const [attempts, setAttempts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchAttempts = () => {
    setLoading(true)
    setError(null)
    apiFetch('/api/attempts')
      .then(setAttempts)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    fetchAttempts()
  }, [])

  return (
    <div>
      <div className="flex items-center gap-3 mb-8">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-green-100">
          <History className="w-5 h-5 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">Practice History</h1>
      </div>

      {loading && <LoadingSpinner message="Loading your history..." />}
      {error && <ErrorMessage message={error} onRetry={fetchAttempts} />}

      {!loading && !error && attempts.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <History className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 mb-4">You haven&apos;t practiced yet.</p>
          <Link
            to="/"
            className="inline-flex items-center gap-1 text-sm font-medium text-green-600 hover:text-green-700"
          >
            Start practicing <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      )}

      {!loading && !error && attempts.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Question</th>
                <th className="text-center px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Score</th>
                <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {attempts.map((a) => {
                const Icon = typeIcons[a.type] || BookOpen
                const scoreText = a.type === 'writing'
                  ? `${a.score} / 9`
                  : `${a.score} / ${a.max_score}`

                return (
                  <tr key={a.id} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center gap-1.5">
                        <Icon className="w-4 h-4 text-gray-400" />
                        <span className="text-sm capitalize text-gray-700">{a.type}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{formatQuestionId(a.question_id)}</td>
                    <td className="px-6 py-4 text-center">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        a.type === 'writing'
                          ? a.score >= 7 ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                          : a.score === a.max_score ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                      }`}>
                        {scoreText}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500 text-right">
                      {new Date(a.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                      })}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
