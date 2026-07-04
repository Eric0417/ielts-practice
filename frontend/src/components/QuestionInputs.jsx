import { Check, X, AlertCircle } from 'lucide-react'

/**
 * Single-select radio group — used for:
 *  - multiple-choice     (A / B / C / D)
 *  - true-false-not-given (TRUE / FALSE / NOT GIVEN)
 *  - yes-no-not-given    (YES / NO / NOT GIVEN)
 */
export function RadioGroup({ choices, selected, onChange, done, correctAnswer, userAnswer }) {
  return (
    <div className="space-y-1.5">
      {choices.map((choice) => {
        const isCorrectChoice = done && choice === correctAnswer
        const isSelectedWrong = done && selected === choice && !isCorrectChoice

        let cls = 'border-gray-300 bg-white hover:bg-gray-50 text-gray-700'
        if (done) {
          if (isCorrectChoice) cls = 'border-green-500 bg-green-50 text-green-700 font-medium'
          else if (isSelectedWrong) cls = 'border-red-400 bg-red-50 text-red-600'
          else cls = 'border-gray-200 bg-gray-50 text-gray-400'
        } else if (selected === choice) {
          cls = 'border-green-500 bg-green-50 text-green-700 font-medium'
        }

        return (
          <button
            key={choice}
            onClick={() => onChange(choice)}
            disabled={done}
            className={`w-full text-left px-3 py-2 rounded-lg border text-sm transition-colors flex items-center justify-between ${cls}`}
          >
            <span>{choice}</span>
            {done && isCorrectChoice && <Check className="w-4 h-4 text-green-600 flex-shrink-0" />}
            {done && isSelectedWrong && <X className="w-4 h-4 text-red-500 flex-shrink-0" />}
          </button>
        )
      })}
    </div>
  )
}

/**
 * Multi-select checkbox group — used for:
 *  - multiple-choice-multi   (pick 2–3 of A–F)
 */
export function CheckboxGroup({ choices, selected, onChange, done, correctAnswers, min, max }) {
  const selSet = new Set(selected || [])
  const atMin = selSet.size >= (min || 2)
  const atMax = selSet.size >= (max || 3)

  const toggle = (choice) => {
    if (done) return
    const next = new Set(selSet)
    if (next.has(choice)) {
      next.delete(choice)
    } else {
      if (atMax && !next.has(choice)) return // enforce max
      next.add(choice)
    }
    onChange(Array.from(next))
  }

  const correctSet = done ? new Set(correctAnswers || []) : null

  return (
    <div>
      <div className="space-y-1.5">
        {choices.map((choice) => {
          const isChecked = selSet.has(choice)
          const isCorrect = done && correctSet?.has(choice)
          const isWrong = done && isChecked && !isCorrect

          let cls = 'border-gray-300 bg-white hover:bg-gray-50'
          if (done) {
            if (isCorrect) cls = 'border-green-500 bg-green-50'
            else if (isWrong) cls = 'border-red-400 bg-red-50'
            else cls = 'border-gray-200 bg-gray-50 text-gray-400'
          } else if (isChecked) {
            cls = 'border-green-500 bg-green-50'
          }

          return (
            <label
              key={choice}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg border text-sm transition-colors ${cls} ${done ? 'cursor-default' : 'cursor-pointer'}`}
            >
              <input
                type="checkbox"
                checked={isChecked}
                onChange={() => toggle(choice)}
                disabled={done}
                className="w-4 h-4 text-green-600 rounded focus:ring-green-500"
              />
              <span className={`${done && !isCorrect && !isWrong ? 'text-gray-400' : ''}`}>
                {choice}
              </span>
              {done && isCorrect && <Check className="w-4 h-4 text-green-600 ml-auto flex-shrink-0" />}
              {done && isWrong && <X className="w-4 h-4 text-red-500 ml-auto flex-shrink-0" />}
            </label>
          )
        })}
      </div>
      {!done && (
        <p className="text-xs text-gray-400 mt-1.5">
          Select {min || 2}–{max || 3} answers.
          {selSet.size > 0 && (
            <span className="ml-1 text-green-600">{selSet.size} selected</span>
          )}
        </p>
      )}
    </div>
  )
}

/**
 * Dropdown select — used for:
 *  - matching-features        (Q1→option B, Q2→option A, …)
 *  - matching-sentence-endings (start → ending letter)
 */
export function DropdownSelect({ qNum, choices, selected, onChange, done, correctAnswer }) {
  const isCorrect = done && selected === correctAnswer
  const isWrong = done && selected && !isCorrect

  let cls = 'border-gray-300 bg-white'
  if (done) {
    if (isCorrect) cls = 'border-green-500 bg-green-50'
    else if (isWrong) cls = 'border-red-400 bg-red-50'
    else cls = 'border-gray-200 bg-gray-50'
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={selected || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={done}
        className={`px-3 py-2 rounded-lg border text-sm focus:outline-none focus:ring-2 focus:ring-green-500 transition-colors ${cls}`}
      >
        <option value="">— Select —</option>
        {choices.map((c) => (
          <option key={c} value={c}>{c}</option>
        ))}
      </select>
      {done && isCorrect && <Check className="w-4 h-4 text-green-600 flex-shrink-0" />}
      {done && isWrong && (
        <span className="text-sm text-red-600 flex items-center gap-1">
          <X className="w-4 h-4 flex-shrink-0" />
          <span className="text-green-700 font-medium">{correctAnswer}</span>
        </span>
      )}
    </div>
  )
}

/**
 * Text input — used for:
 *  - note-completion     (1–3 words)
 *  - summary-completion   (from word bank)
 *  - table-completion / flow-chart-completion / diagram-labelling
 *  - short-answer         (word count enforced)
 */
export function TextInput({ value, onChange, done, isCorrect, correctAnswer, userAnswer, placeholder }) {
  return (
    <div>
      <input
        type="text"
        value={value || ''}
        onChange={(e) => onChange(e.target.value)}
        disabled={done}
        placeholder={placeholder || "Type your answer..."}
        className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-green-500 ${
          done
            ? isCorrect ? 'border-green-300 bg-green-50' : 'border-red-300 bg-red-50'
            : 'border-gray-300'
        }`}
      />
      {done && (
        <div className="flex items-center gap-2 mt-1.5">
          {isCorrect ? (
            <span className="inline-flex items-center gap-1 text-sm text-green-700">
              <Check className="w-4 h-4" /> Correct
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-sm text-red-600">
              <X className="w-4 h-4" /> Your answer: &ldquo;{userAnswer}&rdquo; — Correct: <strong className="text-green-700">{correctAnswer}</strong>
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/**
 * No-answer placeholder — displayed when there's no answer key for this question.
 */
export function NoAnswerPlaceholder() {
  return (
    <div className="flex items-center gap-2 text-sm text-amber-600 bg-amber-50 border border-amber-200 rounded-lg p-3">
      <AlertCircle className="w-4 h-4 flex-shrink-0" />
      <span>Answer key not available for this question yet.</span>
    </div>
  )
}
