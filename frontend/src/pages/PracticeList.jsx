import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import { BookOpen, Headphones, PenLine, BarChart3, ArrowLeft, ChevronRight, FileText, Volume2, CheckCircle, HelpCircle } from 'lucide-react'

const TYPE_CONFIG = {
  reading: { label: 'Reading', icon: BookOpen },
  listening: { label: 'Listening', icon: Headphones },
  'writing-task1': { label: 'Writing Task 1', icon: BarChart3 },
  'writing-task2': { label: 'Writing Task 2', icon: PenLine },
}

// Skills that use the flat layout (no book step)
const FLAT_SKILLS = ['reading', 'writing']

export default function PracticeList() {
  const { type } = useParams()
  const { apiFetch } = useAuth()
  const [books, setBooks] = useState([])
  const [selectedBook, setSelectedBook] = useState(null)
  const [tests, setTests] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingTests, setLoadingTests] = useState(false)
  const [error, setError] = useState(null)

  const config = TYPE_CONFIG[type]
  const backendType = type?.startsWith('writing-') ? 'writing' : type
  const isWriting = type?.startsWith('writing-')
  const isListening = type === 'listening'
  const writingTask = isWriting ? type.replace('writing-', '') : null
  const isFlat = FLAT_SKILLS.includes(backendType)

  // Fetch on mount
  useEffect(() => {
    setError(null)
    setLoading(true)
    setSelectedBook(null)
    setTests([])

    if (isFlat) {
      // Reading / Writing — load tests directly, no book picker
      apiFetch(`/api/v2/books/_flat_/tests?type=${backendType}`)
        .then((data) => {
          let filtered = data.tests
          if (isWriting && writingTask) {
            filtered = data.tests.filter((t) => t.tasks?.includes(writingTask))
          }
          setTests(filtered)
          setLoading(false)
        })
        .catch((err) => {
          setError(err.message)
          setLoading(false)
        })
    } else {
      // Listening — show book picker first
      apiFetch('/api/v2/books')
        .then((data) => {
          const filtered = data.books.filter((b) => {
            if (backendType === 'listening') return b.has_listening
            return true
          })
          setBooks(filtered)
          setLoading(false)
        })
        .catch((err) => {
          setError(err.message)
          setLoading(false)
        })
    }
  }, [type])

  // Fetch tests when a book is selected (listening only)
  const selectBook = (bookId) => {
    setSelectedBook(bookId)
    setLoadingTests(true)
    setError(null)
    apiFetch(`/api/v2/books/${bookId}/tests?type=${backendType}`)
      .then((data) => {
        setTests(data.tests)
        setLoadingTests(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoadingTests(false)
      })
  }

  if (!config) {
    return (
      <div className="text-center py-20">
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Unknown practice type</h2>
        <Link to="/" className="text-green-600 hover:text-green-700">Go to Dashboard</Link>
      </div>
    )
  }

  const Icon = config.icon

  return (
    <div>
      <Link to="/" className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to Dashboard
      </Link>

      <div className="flex items-center gap-3 mb-6">
        <div className="inline-flex items-center justify-center w-10 h-10 rounded-lg bg-green-100">
          <Icon className="w-5 h-5 text-green-600" />
        </div>
        <h1 className="text-2xl font-bold text-gray-900">{config.label} Practice</h1>
      </div>

      {loading && <LoadingSpinner message="Loading..." />}
      {error && <ErrorMessage message={error} onRetry={() => window.location.reload()} />}

      {!loading && !error && tests.length === 0 && !isFlat && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <p className="text-gray-500">No {config.label.toLowerCase()} content available yet.</p>
        </div>
      )}

      {!loading && !error && type === 'listening' && (
        <div className="text-center py-16 bg-white rounded-xl border border-gray-200">
          <Headphones className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500 text-lg font-medium mb-1">Coming Soon</p>
          <p className="text-gray-400 text-sm">Listening practice is under development.</p>
        </div>
      )}

      {!loading && !error && type !== 'listening' && (
        <>
          {/* Book tabs — only for listening */}
          {!isFlat && books.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              {books.map((book) => (
                <button
                  key={book.id}
                  onClick={() => selectBook(book.id)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    selectedBook === book.id
                      ? 'bg-green-600 text-white shadow-sm'
                      : 'bg-white text-gray-700 border border-gray-200 hover:border-green-300 hover:text-green-700'
                  }`}
                >
                  {book.label}
                </button>
              ))}
            </div>
          )}

          {/* Test grid */}
          {(isFlat || selectedBook) && (
            <div>
              {!isFlat && selectedBook && (
                <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
                  Tests in {books.find((b) => b.id === selectedBook)?.label || selectedBook}
                </h2>
              )}
              {isFlat && (
                <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
                  Available Tests
                </h2>
              )}

              {loadingTests && <LoadingSpinner message="Loading tests..." />}

              {!loadingTests && tests.length === 0 && (
                <div className="text-center py-12 bg-white rounded-xl border border-gray-200">
                  <p className="text-gray-500">No tests available.</p>
                </div>
              )}

              {!loadingTests && tests.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {tests.map((t) => {
                    const testLabel = t.test.replace('test', 'Test ')
                    const linkPath = isFlat
                      ? `/practice/${type}/${t.test}`
                      : `/practice/${type}/${selectedBook}/${t.test}`

                    const parts = t.passages || t.sections || t.tasks || []
                    const partLabel = t.passages ? 'passage' : t.sections ? 'section' : 'task'

                    return (
                      <Link
                        key={t.test}
                        to={linkPath}
                        className="bg-white rounded-xl border border-gray-200 p-5 hover:border-green-300 hover:shadow-sm transition-all group"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <h3 className="font-semibold text-gray-900">{testLabel}</h3>
                          {!isWriting && t.has_answers && (
                            <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                          )}
                          {!isWriting && !t.has_answers && (
                            <HelpCircle className="w-4 h-4 text-amber-400 flex-shrink-0" />
                          )}
                        </div>

                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {parts.map((p) => (
                            <span key={p} className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600">
                              {p === 'passage1' || p === 'passage2' || p === 'passage3' ? (
                                <><FileText className="w-3 h-3" />{p.replace('passage', 'P')}</>
                              ) : p === 'section1' || p === 'section2' || p === 'section3' || p === 'section4' ? (
                                <><Volume2 className="w-3 h-3" />{p.replace('section', 'S')}</>
                              ) : (
                                <><PenLine className="w-3 h-3" />{p.replace('task', 'T')}</>
                              )}
                            </span>
                          ))}
                        </div>

                        <div className="flex items-center justify-between">
                          <span className="text-xs text-gray-400">
                            {parts.length} {partLabel}{parts.length !== 1 ? 's' : ''}
                          </span>
                          {!t.has_answers && !isWriting && (
                            <span className="text-xs text-amber-500 bg-amber-50 px-2 py-0.5 rounded">
                              Preview only
                            </span>
                          )}
                          <span className="text-green-600 text-sm group-hover:translate-x-0.5 transition-transform">
                            <ChevronRight className="w-4 h-4" />
                          </span>
                        </div>
                      </Link>
                    )
                  })}
                </div>
              )}
            </div>
          )}

          {/* Placeholder when no book selected (listening) */}
          {!isFlat && !selectedBook && books.length > 0 && (
            <div className="text-center py-16 bg-white rounded-xl border border-gray-200 border-dashed">
              <BookOpen className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Select a Cambridge book above to see available tests</p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
