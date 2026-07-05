import { useState, useEffect, useRef, useCallback } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { ArrowLeft, Check, X, Award, Volume2, AlertCircle, Tag, FileText, ChevronDown, ChevronRight } from 'lucide-react'
import { RadioGroup, CheckboxGroup, DropdownSelect, TextInput } from '../components/QuestionInputs'

const LABEL_MAP = {
  passage1: 'Passage 1', passage2: 'Passage 2', passage3: 'Passage 3',
  section1: 'Section 1', section2: 'Section 2', section3: 'Section 3', section4: 'Section 4',
}

// In production, frontend and backend are separate Render services.
// Asset URLs (PDFs, audio) need the backend base URL as a prefix.
// In dev, Vite proxys /content/* → localhost:8000, so empty prefix works.
const ASSET_BASE = import.meta.env.VITE_API_BASE_URL || ''
const assetUrl = (path) => {
  if (!path) return ''
  if (path.startsWith('http')) return path
  return `${ASSET_BASE}${path}`
}

export default function ObjectivePractice() {
  const { type, test } = useParams()  // flat layout: /practice/:type/:test
  const { apiFetch } = useAuth()
  const book = '_flat_'  // virtual book id for flat API
  const [testDetail, setTestDetail] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [answersBySection, setAnswersBySection] = useState({}) // { passage1: {1: "B", 2: "TRUE"}, passage2: {1: "C"} }
  const [resultsBySection, setResultsBySection] = useState({})  // { passage1: resultData }
  const [submitting, setSubmitting] = useState(false)
  const [activePdf, setActivePdf] = useState(null)
  const [activeAudio, setActiveAudio] = useState(null)
  const [activeSection, setActiveSection] = useState(null)
  const questionRefs = useRef({})

  const backendType = type === 'listening' ? 'listening' : 'reading'

  useEffect(() => {
    if (!book || !test) return
    setLoading(true)
    setError(null)
    setResultsBySection({})
    setAnswersBySection({})
    apiFetch(`/api/v2/tests/${book}/${test}/${backendType}`)
      .then((data) => {
        setTestDetail(data)
        const pdfKeys = Object.keys(data.pdfs || {})
        if (pdfKeys.length > 0) {
          const first = pdfKeys[0]
          setActivePdf(first)
          if (data.audio) setActiveAudio(first)
          // Reading: set active section to first passage so only it shows
          setActiveSection(first)
        }
        setLoading(false)
      })
      .catch((err) => {
        setError(err.message)
        setLoading(false)
      })
  }, [book, test, backendType])

  const handleAnswer = useCallback((sectionKey, qNum, value) => {
    setAnswersBySection((prev) => ({
      ...prev,
      [sectionKey]: { ...(prev[sectionKey] || {}), [qNum]: value },
    }))
  }, [])

  const handleSubmit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const sectionAnswers = answersBySection[activeSection] || {}
      const res = await apiFetch('/api/grade/v2/passage', {
        method: 'POST',
        body: JSON.stringify({ book, test, type: backendType, passage: activeSection, answers: sectionAnswers }),
      })
      setResultsBySection(prev => ({ ...prev, [activeSection]: res }))
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  // ── Loading / error / empty states ──
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="animate-spin rounded-full h-10 w-10 border-2 border-gray-300 border-t-green-600 mb-4" />
        <p className="text-gray-500 text-sm">Loading test...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-md mx-auto mt-12 p-6 bg-red-50 border border-red-200 rounded-lg text-center">
        <p className="text-red-700 mb-3">{error}</p>
        <Link to={`/practice/${type}`} className="text-sm text-red-600 underline hover:text-red-800">Back to list</Link>
      </div>
    )
  }

  if (!testDetail) {
    return (
      <div className="max-w-md mx-auto mt-12 p-6 bg-amber-50 border border-amber-200 rounded-lg text-center">
        <p className="text-amber-700">Test not found.</p>
        <Link to={`/practice/${type}`} className="text-sm text-amber-600 underline mt-2 inline-block">Back to list</Link>
      </div>
    )
  }

  // ── Data from new sections-based API ──
  const sections = testDetail.sections || {}
  const pdfKeys = Object.keys(testDetail.pdfs || {})
  const sectionKeys = Object.keys(sections)

  // All questions across all sections, flattened
  const allQuestions = Object.values(sections).flatMap((s) => s.questions)

  // Per-section results
  const currentSectionResults = activeSection ? resultsBySection[activeSection] : null
  const done = currentSectionResults !== undefined

  const visibleSections = activeSection
    ? sectionKeys.filter((k) => k === activeSection)
    : sectionKeys

  return (
    <div>
      {/* Header */}
      <Link to={`/practice/${type}`} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-900 mb-6">
        <ArrowLeft className="w-4 h-4" />
        Back to {backendType === 'listening' ? 'Listening' : 'Reading'} tests
      </Link>

      <h1 className="text-2xl font-bold text-gray-900 mb-2">{testDetail.label}</h1>
      <p className="text-sm text-gray-500 mb-6">
        {testDetail.total_questions || allQuestions.length} questions · {sectionKeys.length} {backendType === 'listening' ? 'sections' : 'passages'}
      </p>

      {/* Score bar — only for the submitted section */}
      {done && (
        <div className={`flex items-center gap-3 p-4 rounded-xl mb-6 ${currentSectionResults.score === currentSectionResults.max_score ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200'}`}>
          <Award className={`w-6 h-6 ${currentSectionResults.score === currentSectionResults.max_score ? 'text-green-600' : 'text-amber-600'}`} />
          <div>
            <span className="font-bold text-lg text-gray-900">{currentSectionResults.score} / {currentSectionResults.max_score}</span>
            <span className="text-sm text-gray-500 ml-2">
              ({Math.round((currentSectionResults.score / currentSectionResults.max_score) * 100)}%)
            </span>
            <span className="text-xs text-gray-400 ml-2">
              — {LABEL_MAP[activeSection] || activeSection}
            </span>
          </div>
        </div>
      )}

      {/* Switch passage to clear results */}
      {sectionKeys.some(k => !resultsBySection[k]) && sectionKeys.length > 1 && (
        <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700 mb-4">
          Switch to another passage tab and click Submit to grade that passage too.
        </div>
      )}

      <div className="split-panel">
        {/* ═══════════════ LEFT PANEL: PDF + Audio ═══════════════ */}
        <div className="split-panel-left">
          <div>
          {/* Audio */}
          {backendType === 'listening' && activeAudio && testDetail.audio?.[activeAudio] && (
            <div className="bg-white rounded-xl border border-gray-200 p-4 mb-4">
              <div className="flex items-center gap-2 mb-2">
                <Volume2 className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-500">
                  {LABEL_MAP[activeAudio] || activeAudio} Audio
                </span>
              </div>
              <audio controls className="w-full" key={activeAudio}>
                <source src={assetUrl(testDetail.audio[activeAudio])} type="audio/mpeg" />
              </audio>
            </div>
          )}

          {/* PDF tabs */}
          {pdfKeys.length > 1 && (
            <div className="flex border-b border-gray-200 bg-white rounded-t-xl">
              {pdfKeys.map((key) => (
                <button
                  key={key}
                  onClick={() => {
                    setActivePdf(key)
                    if (backendType === 'listening') {
                      setActiveAudio(key)
                      setActiveSection(key)
                    }
                  }}
                  className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 ${
                    activePdf === key
                      ? 'border-green-600 text-green-700 bg-green-50/50'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  {LABEL_MAP[key] || key}
                </button>
              ))}
            </div>
          )}

          {/* PDF iframe */}
          {activePdf && testDetail.pdfs[activePdf] && (
            <div className={`bg-white ${pdfKeys.length > 1 ? 'rounded-b-xl' : 'rounded-xl'} border border-gray-200 ${pdfKeys.length > 1 ? 'border-t-0' : ''}`}>
              <iframe
                src={assetUrl(testDetail.pdfs[activePdf])}
                className="w-full h-full"
                style={{ height: 'calc(100vh - 300px)', minHeight: '500px' }}
                title={activePdf}
              />
            </div>
          )}
        </div>
        </div>

        {/* ═══════════════ RIGHT PANEL: Answer form ═══════════════ */}
        <div className="split-panel-right">
        <div className="space-y-6">
          {/* ═══ Passage tabs (reading) — always show 3 tabs ═══ */}
          {backendType === 'reading' && sectionKeys.length > 1 && (
            <div className="flex gap-1 bg-white rounded-xl border border-gray-200 p-1 sticky top-0 z-10">
              {sectionKeys.map((key) => {
                const sec = sections[key]
                const qs = sec?.questions || []
                const range = qs.length > 0
                  ? `Q${qs[0].q}–${qs[qs.length - 1].q}`
                  : ''
                const sectionAnswers = answersBySection[key] || {}
                const answered = Object.values(sectionAnswers).filter(v => v && v.toString().trim()).length
                const sectionDone = resultsBySection[key] !== undefined
                const sectionScore = sectionDone ? resultsBySection[key] : null
                return (
                  <button
                    key={key}
                    onClick={() => {
                      setActiveSection(key)
                      setActivePdf(key)
                    }}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      activeSection === key
                        ? 'bg-green-600 text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {LABEL_MAP[key] || key}
                    {range && <span className="block opacity-70">{range}</span>}
                    {answered > 0 && !sectionDone && (
                      <span className="block text-[10px] opacity-70">{answered}/{qs.length} answered</span>
                    )}
                    {sectionDone && (
                      <span className="block text-[10px] opacity-70">{sectionScore.score}/{sectionScore.max_score}</span>
                    )}
                  </button>
                )
              })}
            </div>
          )}

          {/* Listening section tabs */}
          {backendType === 'listening' && sectionKeys.length > 1 && (
            <div className="flex gap-1 bg-white rounded-xl border border-gray-200 p-1">
              {sectionKeys.map((key) => {
                const sec = sections[key]
                const qs = sec?.questions || []
                const range = qs.length > 0
                  ? `Q${qs[0].q}–${qs[qs.length - 1].q}`
                  : ''
                return (
                  <button
                    key={key}
                    onClick={() => {
                      setActiveSection(key)
                      setActivePdf(key)
                      setActiveAudio(key)
                    }}
                    className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                      activeSection === key
                        ? 'bg-green-600 text-white shadow-sm'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {LABEL_MAP[key] || key}
                    {range && <span className="block opacity-70">{range}</span>}
                  </button>
                )
              })}
            </div>
          )}

          {/* No answer key warning */}
          {sectionKeys.length === 0 && (
            <div className="p-6 bg-amber-50 border border-amber-200 rounded-xl text-center">
              <AlertCircle className="w-8 h-8 text-amber-500 mx-auto mb-2" />
              <p className="text-sm text-amber-700 font-medium mb-1">No answer key available for this test yet.</p>
              <p className="text-xs text-amber-500">You can still preview the PDF passages, but grading is disabled.</p>
            </div>
          )}

          {/* Sections with questions */}
          {visibleSections.map((secKey) => {
            const sec = sections[secKey]
            if (!sec || !sec.questions?.length) return null

            return (
              <div key={secKey} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                {/* Section header with type label */}
                <div className="px-5 py-3 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-semibold text-gray-700">
                      {LABEL_MAP[secKey] || secKey}
                    </h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <Tag className="w-3 h-3 text-gray-400" />
                      <span className="text-xs text-gray-500">{sec.label}</span>
                    </div>
                  </div>
                  <span className="text-xs text-gray-400">
                    {sec.questions.length} question{sec.questions.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Questions */}
                <div className="p-5 space-y-4">
                  {sec.questions.map((q) => {
                    const qNum = q.q
                    const itemResult = done
                      ? currentSectionResults?.results?.find((r) => r.question_id === qNum)
                      : null
                    const isCorrect = itemResult?.is_correct
                    const correctAnswer = itemResult?.correct_answer
                    const hasResult = itemResult !== undefined

                    return (
                      <div
                        key={qNum}
                        ref={(el) => { questionRefs.current[qNum] = el }}
                        className={`rounded-lg border p-4 transition-colors ${
                          done
                            ? hasResult
                              ? isCorrect ? 'border-green-200 bg-green-50/50' : 'border-red-200 bg-red-50/50'
                              : 'border-gray-200'
                            : 'border-gray-200'
                        }`}
                      >
                        <label className="block text-sm font-medium text-gray-900 mb-2">
                          Question {qNum}
                          <span className="ml-2 text-xs text-gray-400 font-normal">
                            ({q.type ? q.type.replace(/-/g, ' ') : 'unknown'})
                          </span>
                        </label>

                        {/* ── TEXT INPUT ── (note-completion, short-answer, etc.) */}
                        {q.ui === 'text' && (
                          <TextInput
                            value={(answersBySection[secKey] || {})[qNum] || ''}
                            onChange={(v) => handleAnswer(secKey, qNum, v)}
                            done={done}
                            isCorrect={isCorrect}
                            correctAnswer={correctAnswer}
                            userAnswer={itemResult?.user_answer}
                          />
                        )}

                        {/* ── TFNG ── (true-false-not-given / yes-no-not-given) */}
                        {q.ui === 'tfng' && q.choices && (
                          <RadioGroup
                            choices={q.choices}
                            selected={(answersBySection[secKey] || {})[qNum]}
                            onChange={(v) => handleAnswer(secKey, qNum, v)}
                            done={done}
                            correctAnswer={correctAnswer}
                            userAnswer={(answersBySection[secKey] || {})[qNum]}
                          />
                        )}

                        {/* ── RADIO ── (mcq-single) */}
                        {q.ui === 'radio' && q.choices && (
                          <RadioGroup
                            choices={q.choices}
                            selected={(answersBySection[secKey] || {})[qNum]}
                            onChange={(v) => handleAnswer(secKey, qNum, v)}
                            done={done}
                            correctAnswer={correctAnswer}
                            userAnswer={(answersBySection[secKey] || {})[qNum]}
                          />
                        )}

                        {/* ── CHECKBOX ── (mcq-multi) */}
                        {q.ui === 'checkbox' && q.choices && (
                          <CheckboxGroup
                            choices={q.choices}
                            selected={(answersBySection[secKey] || {})[qNum] || []}
                            onChange={(v) => handleAnswer(secKey, qNum, v)}
                            done={done}
                            correctAnswers={correctAnswer ? correctAnswer.split(',').map(s => s.trim()) : []}
                            min={q.meta?.min || 2}
                            max={q.meta?.max || 3}
                          />
                        )}

                        {/* ── DROPDOWN ── (matching-features, matching-sentence-endings) */}
                        {q.ui === 'dropdown' && q.choices && (
                          <DropdownSelect
                            qNum={qNum}
                            choices={q.choices}
                            selected={(answersBySection[secKey] || {})[qNum] || ''}
                            onChange={(v) => handleAnswer(secKey, qNum, v)}
                            done={done}
                            correctAnswer={correctAnswer}
                          />
                        )}

                        {/* ── PAIRED ── */}
                        {q.ui === 'paired' && (
                          <p className="text-sm text-gray-400 italic">
                            Paired question (manual grading)
                          </p>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}

          {/* Submit */}
          {!done && allQuestions.length > 0 && (
            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full py-3 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors sticky bottom-4 shadow-lg"
            >
              {submitting ? 'Submitting...' : 'Submit answers'}
            </button>
          )}
        </div>
        </div>
      </div>
    </div>
  )
}
