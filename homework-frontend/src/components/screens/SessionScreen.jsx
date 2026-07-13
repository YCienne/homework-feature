import React, { useState, useEffect, useRef } from 'react'
import { sendAction } from '../../services/index.js'
import Toast from '../ui/Toast.jsx'

const MAX_SKIPS_PER_STEP = 2
const MAX_WRONG_BEFORE_RESET = 3

export default function SessionScreen({ session, onStepAdvance, onSameStep, onSkip, onBack }) {
  const { sessionId, question, currentStep, maxSteps, stepTitle, explanation, guideQuestion, hint, skipCount = 0 } = session

  const [answer, setAnswer]       = useState('')
  const [loading, setLoading]     = useState(false)
  const [activeBtn, setActiveBtn] = useState('')
  const [inlineHint, setHint]     = useState(hint || null)
  const [reExplain, setReExplain] = useState(null)
  const [wrongCount, setWrong]    = useState(0)
  const [errorMsg, setErrorMsg]   = useState('')
  const [toast, setToast]         = useState(null)
  const [localSkips, setSkips]    = useState(skipCount)
  const inputRef = useRef(null)

  // Reset everything when the step changes
  useEffect(() => {
    setAnswer(''); setHint(null); setReExplain(null)
    setWrong(0); setErrorMsg(''); setLoading(false); setActiveBtn('')
    setSkips(skipCount)
    setTimeout(() => inputRef.current?.focus(), 100)
  }, [currentStep, sessionId])

  useEffect(() => { if (hint) setHint(hint) }, [hint])

  const progressPct = Math.round((currentStep / maxSteps) * 100)
  const canSkip     = localSkips < MAX_SKIPS_PER_STEP || wrongCount >= MAX_WRONG_BEFORE_RESET
  const busy        = loading || activeBtn !== ''

  // ── CONTINUE ─────────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!answer.trim()) { setErrorMsg('Please type your answer before submitting.'); return }
    setLoading(true); setErrorMsg('')
    try {
      const result = await sendAction({ sessionId, action: 'CONTINUE', response: answer.trim() })

      if (result.is_final_step) {
        onStepAdvance(result)
        return
      }

      // Determine if the explanation signals correctness or correction
      // The backend always returns 200 — we check the content
      const explanationLower = (result.explanation || '').toLowerCase()
      const isCorrect = explanationLower.includes('correct') ||
                        explanationLower.includes('well done') ||
                        explanationLower.includes('great') ||
                        explanationLower.includes('right') ||
                        explanationLower.includes('good job') ||
                        explanationLower.includes('exactly')
      const isWrong   = explanationLower.includes('not quite') ||
                        explanationLower.includes('incorrect') ||
                        explanationLower.includes('try again') ||
                        explanationLower.includes("that's not") ||
                        explanationLower.includes('wrong')

      if (isWrong) {
        const newWrong = wrongCount + 1
        setWrong(newWrong)
        setErrorMsg("That's not quite right. Try again!")
        setHint(result.hint || null)
        if (newWrong >= MAX_WRONG_BEFORE_RESET) {
          setSkips(0) // reset skip counter after 3 wrong
          setToast({ type: 'info', message: 'Keep trying!', subtitle: 'You can now use Next step if needed.' })
          setTimeout(() => setToast(null), 3000)
        }
      } else {
        // Correct or advancing — show toast then move to next step
        setToast({ type: 'success', message: 'Correct! 🎉', subtitle: 'Great thinking!' })
        setTimeout(() => { setToast(null); onStepAdvance(result) }, 1200)
      }

    } catch (e) {
      setErrorMsg(e.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── IM_NOT_SURE ───────────────────────────────────────────────────────────────
  async function handleNotSure() {
    setActiveBtn('IM_NOT_SURE')
    try {
      const result = await sendAction({ sessionId, action: 'IM_NOT_SURE' })
      setHint(result.hint || result.explanation || 'Think about what information the question has given you.')
      onSameStep(result)
    } catch {
      setHint('Think carefully — break the problem into its smallest parts and tackle just the first one.')
    } finally { setActiveBtn('') }
  }

  // ── SHOW_NEXT_STEP ────────────────────────────────────────────────────────────
  async function handleNextStep() {
    if (!canSkip) return
    const newSkips = localSkips + 1
    setSkips(newSkips)
    setActiveBtn('SHOW_NEXT_STEP')
    try {
      const result = await sendAction({ sessionId, action: 'SHOW_NEXT_STEP' })
      onSkip(result, newSkips)
    } catch (e) {
      setErrorMsg(e.message || 'Something went wrong.')
    } finally { setActiveBtn('') }
  }

  // ── EXPLAIN_AGAIN ─────────────────────────────────────────────────────────────
  async function handleExplain() {
    setActiveBtn('EXPLAIN_AGAIN')
    try {
      const result = await sendAction({ sessionId, action: 'EXPLAIN_AGAIN' })
      setReExplain(result.explanation)
      onSameStep(result)
    } catch {
      setReExplain('Let me try again: break the problem into the smallest possible part and focus only on that one step.')
    } finally { setActiveBtn('') }
  }

  return (
    <div className="min-h-screen bg-brand-teal-light">
      {toast && <Toast message={toast.message} subtitle={toast.subtitle} type={toast.type} onClose={() => setToast(null)} />}

      <div className="max-w-3xl mx-auto px-4 py-6">

        {/* Back */}
        <button onClick={onBack} className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors mb-5">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/>
          </svg>
          Back
        </button>

        {/* Problem card */}
        <div className="card p-4 flex items-center gap-4 mb-5">
          <div className="w-10 h-10 rounded-full bg-brand-teal flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="8" strokeWidth={2}/><circle cx="12" cy="12" r="3" strokeWidth={2}/>
            </svg>
          </div>
          <div>
            <p className="text-xs font-semibold text-brand-teal uppercase tracking-wide mb-0.5">Problem</p>
            <p className="font-bold text-gray-900">{question}</p>
          </div>
        </div>

        {/* Progress */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Step {currentStep} of {maxSteps}</span>
          <span className="text-xs font-semibold text-brand-teal bg-brand-teal-light border border-brand-teal-border rounded-full px-3 py-0.5">
            {progressPct}% Complete
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full mb-6" style={{ height: 6 }}>
          <div className="progress-bar h-full rounded-full transition-all duration-700" style={{ width: `${progressPct}%` }} />
        </div>

        {/* Step card */}
        <div className="card overflow-hidden mb-4">
          {/* Header */}
          <div className="bg-brand-teal-light border-b border-brand-teal-border px-5 py-4 flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-brand-teal flex items-center justify-center flex-shrink-0">
              <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z"/>
              </svg>
            </div>
            <div>
              <span className="inline-block text-xs font-bold text-white bg-brand-teal rounded-full px-2.5 py-0.5 mb-1">Step {currentStep}</span>
              <p className="font-bold text-gray-900">{stepTitle}</p>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {/* Explanation */}
            <div className="border border-brand-teal-border rounded-xl p-4 text-sm text-gray-700 leading-relaxed">
              {explanation}
            </div>

            {/* Re-explain */}
            {reExplain && reExplain !== explanation && (
              <div className="border border-purple-200 bg-purple-50 rounded-xl p-4 text-sm text-purple-800 leading-relaxed">
                <p className="text-xs font-semibold text-purple-500 uppercase tracking-wide mb-1">Explained differently</p>
                {reExplain}
              </div>
            )}

            {/* Hint */}
            {inlineHint && (
              <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-sm text-amber-800 flex gap-2">
                <svg className="w-4 h-4 flex-shrink-0 mt-0.5 text-amber-500" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>
                <div>
                  <p className="font-semibold text-amber-700 text-xs uppercase tracking-wide mb-1">Hint</p>
                  {inlineHint}
                </div>
              </div>
            )}

            {/* Guide question */}
            {guideQuestion && (
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-brand-teal flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006
                       2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <p className="font-semibold text-gray-800">{guideQuestion}</p>
              </div>
            )}

            {/* Answer input */}
            <div>
              <input
                ref={inputRef}
                type="text"
                value={answer}
                onChange={e => { setAnswer(e.target.value); setErrorMsg('') }}
                onKeyDown={e => e.key === 'Enter' && !busy && handleSubmit()}
                placeholder="Type your answer here..."
                disabled={busy}
                className={`w-full border-2 rounded-xl px-4 py-3 text-sm outline-none transition-all
                            disabled:bg-gray-50 disabled:text-gray-400
                            ${errorMsg ? 'border-red-400 bg-red-50' : answer ? 'border-purple-400' : 'border-gray-200 focus:border-purple-400'}`}
              />
              {errorMsg && (
                <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                  <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                  </svg>
                  {errorMsg}
                </p>
              )}
            </div>

            {/* Submit */}
            <button onClick={handleSubmit} disabled={busy || !answer.trim()} className="btn-gradient">
              {loading ? <><span className="spinner" /> Checking...</> : <>Submit Answer
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
              </>}
            </button>
          </div>
        </div>

        {/* Action buttons */}
        <div className="grid grid-cols-3 gap-3">
          {/* I'm not sure */}
          <button onClick={handleNotSure} disabled={busy}
            className="flex flex-col items-center gap-1.5 border border-gray-200 bg-white rounded-xl py-4 px-2
                       text-xs font-medium text-gray-700 hover:border-amber-300 hover:bg-amber-50 transition-all disabled:opacity-50">
            {activeBtn === 'IM_NOT_SURE'
              ? <span className="spinner spinner-dark" />
              : <svg className="w-5 h-5 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707
                       m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4
                       0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
                </svg>}
            I'm not sure
          </button>

          {/* Next step */}
          <button onClick={handleNextStep} disabled={busy || !canSkip}
            title={!canSkip ? `Try answering — you've used ${MAX_SKIPS_PER_STEP} skips` : ''}
            className={`flex flex-col items-center gap-1.5 border bg-white rounded-xl py-4 px-2
                        text-xs font-medium transition-all
                        ${canSkip
                          ? 'border-gray-200 text-gray-700 hover:border-brand-teal hover:bg-brand-teal-light'
                          : 'border-gray-100 text-gray-300 cursor-not-allowed'}`}>
            {activeBtn === 'SHOW_NEXT_STEP'
              ? <span className="spinner spinner-dark" />
              : <svg className="w-5 h-5 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>}
            Next step
          </button>

          {/* Explain again */}
          <button onClick={handleExplain} disabled={busy}
            className="flex flex-col items-center gap-1.5 border border-gray-200 bg-white rounded-xl py-4 px-2
                       text-xs font-medium text-gray-700 hover:border-purple-300 hover:bg-purple-50 transition-all disabled:opacity-50">
            {activeBtn === 'EXPLAIN_AGAIN'
              ? <span className="spinner spinner-dark" />
              : <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0
                       0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>}
            Explain again
          </button>
        </div>
      </div>
    </div>
  )
}
