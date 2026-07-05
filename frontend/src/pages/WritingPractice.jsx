import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'
import RadarChart from '../components/RadarChart'
import { ArrowLeft, Send, Clock, FileText, Award, Lightbulb, TrendingUp, AlertCircle, Check, Eye } from 'lucide-react'

// In production, frontend and backend are separate Render services.
// Asset URLs (PDFs) need the backend base URL as a prefix.
const ASSET_BASE = import.meta.env.VITE_API_BASE_URL || ''
const assetUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${ASSET_BASE}${path}`
}

export default function WritingPractice() {
  const { type, test } = useParams()  // flat layout: /practice/:type/:test
  const { apiFetch } = useAuth()
  const book = '_flat_'  // virtual book id for flat API
  const [testDetail, setTestDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [essay, setEssay] = useState('')
  const [result, setResult] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const task = type === 'writing-task1' ? 'task1' : 'task2'
  const wordMinimum = task === 'task1' ? 150 : 250
  const taskLabel = task === 'task1' ? 'Task 1' : 'Task 2'

  const fetchTest = () => {
    setLoading(true)
    setError(null)
    setResult(null)
    setEssay('')
    apiFetch(`/api/v2/tests/${book}/${test}/writing`)
      .then((data) => {
        setTestDetail(data)
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchTest()
  }, [book, test])

  const wordCount = essay.trim() ? essay.trim().split(/\s+/).length : 0
  const belowMinimum = wordCount < wordMinimum

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const res = await apiFetch('/api/grade/v2/writing', {
        method: 'POST',
        body: JSON.stringify({ book, test, task, essay }),
      })
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) return <LoadingSpinner message="Loading writing task..." />
  if (error) return <ErrorMessage message={error} onRetry={fetchTest} />
  if (!testDetail) return <ErrorMessage message="Writing test not found." />

  const done = result !== null
  const pdfUrl = testDetail.pdfs?.[task]
  const backPath = `/practice/${type}`

  return (
    <div>
      <Link to={backPath} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to {taskLabel} list
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">{testDetail.label}</h1>
      <p className="text-sm text-gray-500 mb-6">
        {taskLabel} · Minimum {wordMinimum} words
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT: PDF viewer only */}
        <div>
          {pdfUrl ? (
            <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
              <div className="flex items-center gap-2 px-5 py-3 bg-gray-50 border-b border-gray-100">
                <Eye className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-500">Question Paper — {taskLabel}</span>
              </div>
              <iframe
                src={assetUrl(pdfUrl)}
                className="w-full"
                style={{ height: 'calc(100vh - 180px)', minHeight: '600px' }}
                title={`${taskLabel} PDF`}
              />
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-6 text-center">
              <p className="text-amber-700 text-sm">No PDF available for this task.</p>
            </div>
          )}
        </div>

        {/* RIGHT: Essay input + results */}
        <div className="space-y-6">
          {/* Essay input */}
          {!done && (
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <div className="flex items-center justify-between mb-3">
                <label className="text-sm font-medium text-gray-500">Your Essay</label>
                <div className={`flex items-center gap-2 text-sm ${belowMinimum ? 'text-amber-600' : 'text-green-600'}`}>
                  <Clock className="w-4 h-4" />
                  <span>{wordCount} / {wordMinimum} words</span>
                  {belowMinimum && <AlertCircle className="w-4 h-4" />}
                </div>
              </div>
              <textarea
                value={essay}
                onChange={(e) => setEssay(e.target.value)}
                placeholder={`Write your ${taskLabel} essay here... (minimum ${wordMinimum} words)`}
                className="w-full h-64 p-4 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent resize-y font-mono"
              />
              {belowMinimum && wordCount > 0 && (
                <p className="mt-2 text-sm text-amber-600">
                  You need at least {wordMinimum} words. Currently at {wordCount}.
                </p>
              )}

              <button
                onClick={handleSubmit}
                disabled={submitting || !essay.trim()}
                className="mt-4 w-full py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
              >
                {submitting ? (
                  <>
                    <span className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    AI is grading your essay...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Submit for AI Grading
                  </>
                )}
              </button>
            </div>
          )}

          {/* Results */}
          {done && (
            <div className="space-y-6">
              <div className="bg-white rounded-xl border border-gray-200 p-6 text-center">
                <Award className="w-12 h-12 text-green-600 mx-auto mb-2" />
                <p className="text-sm text-gray-500 mb-1">Overall Band Score</p>
                <p className="text-4xl font-bold text-green-700">{result.overall_band}</p>
              </div>

              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-sm font-medium text-gray-500 mb-4">Band Score Breakdown</h3>
                <RadarChart data={result.criteria} />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {Object.entries(result.criteria).map(([key, val]) => (
                  <div key={key} className="bg-white rounded-xl border border-gray-200 p-5">
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-sm font-medium text-gray-900 capitalize">
                        {formatCriterionName(key)}
                      </h4>
                      <span className="text-sm font-bold text-green-600 bg-green-50 px-2 py-0.5 rounded">
                        {val.band}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 leading-relaxed">{val.comment}</p>
                  </div>
                ))}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-white rounded-xl border border-green-200 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Check className="w-4 h-4 text-green-600" />
                    <h3 className="text-sm font-medium text-green-900">Strengths</h3>
                  </div>
                  <ul className="space-y-2">
                    {result.strengths.map((s, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2">
                        <span className="text-green-500 mt-1">•</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="bg-white rounded-xl border border-amber-200 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp className="w-4 h-4 text-amber-600" />
                    <h3 className="text-sm font-medium text-amber-900">Areas to Improve</h3>
                  </div>
                  <ul className="space-y-2">
                    {result.improvements.map((s, i) => (
                      <li key={i} className="text-sm text-gray-700 flex gap-2">
                        <span className="text-amber-500 mt-1">•</span>{s}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>

              {result.corrected_examples?.length > 0 && (
                <div className="bg-white rounded-xl border border-gray-200 p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <Lightbulb className="w-4 h-4 text-yellow-500" />
                    <h3 className="text-sm font-medium text-gray-900">Suggested Corrections</h3>
                  </div>
                  <div className="space-y-4">
                    {result.corrected_examples.map((ex, i) => (
                      <div key={i} className="space-y-2">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                          <div className="p-3 bg-red-50 rounded-lg">
                            <p className="text-xs text-red-500 mb-1 uppercase tracking-wider">Original</p>
                            <p className="text-red-800">{ex.original}</p>
                          </div>
                          <div className="p-3 bg-green-50 rounded-lg">
                            <p className="text-xs text-green-500 mb-1 uppercase tracking-wider">Suggestion</p>
                            <p className="text-green-800">{ex.suggestion}</p>
                          </div>
                        </div>
                        {ex.explanation && (
                          <div className="p-3 bg-blue-50 rounded-lg text-sm">
                            <p className="text-xs text-blue-500 mb-1 uppercase tracking-wider">Explanation</p>
                            <p className="text-blue-800">{ex.explanation}</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <button
                onClick={() => setResult(null)}
                className="w-full py-3 bg-gray-100 text-gray-700 rounded-xl font-medium hover:bg-gray-200 transition-colors"
              >
                Write another essay
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function formatCriterionName(key) {
  const map = {
    task_response: 'Task Achievement / Response',
    coherence_cohesion: 'Coherence & Cohesion',
    lexical_resource: 'Lexical Resource',
    grammatical_range_accuracy: 'Grammatical Range & Accuracy',
  }
  return map[key] || key
}
