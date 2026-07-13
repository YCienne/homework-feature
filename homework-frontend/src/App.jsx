import React, { useState, useCallback } from 'react'
import Navbar from './components/layout/Navbar'
import LandingScreen from './components/screens/LandingScreen'
import QuestionScreen from './components/screens/QuestionScreen'
import ImageConfirmScreen from './components/screens/ImageConfirmScreen'
import SessionScreen from './components/screens/SessionScreen'
import CompletionScreen from './components/screens/CompletionScreen'
import ErrorScreen from './components/screens/ErrorScreen'
import { startSession } from './services/index.js'

const SCREENS = {
  LANDING:       'LANDING',
  QUESTION:      'QUESTION',
  IMAGE_CONFIRM: 'IMAGE_CONFIRM',
  SESSION:       'SESSION',
  COMPLETE:      'COMPLETE',
  ERROR:         'ERROR',
}

export default function App() {
  const [screen, setScreen]     = useState(SCREENS.LANDING)
  const [session, setSession]   = useState(null)
  const [imageData, setImage]   = useState(null)
  const [errorData, setError]   = useState(null)
  const [loading, setLoading]   = useState(false)

  function handleError(e) {
    setError({ code: e.code || 'INTERNAL_ERROR', message: e.message })
    setScreen(SCREENS.ERROR)
  }

  // ── Landing → Question ───────────────────────────────────────────────────────
  function handleStart() { setScreen(SCREENS.QUESTION) }

  // ── Question submitted ───────────────────────────────────────────────────────
  async function handleQuestionSubmit(payload) {
    if (payload.fromImage) {
      setImage(payload)
      setScreen(SCREENS.IMAGE_CONFIRM)
      return
    }
    await beginSession(payload.question, null)
  }

  // ── Image confirmed ──────────────────────────────────────────────────────────
  async function handleImageConfirm({ question, extractionId }) {
    await beginSession(question, extractionId)
  }

  // ── Start session — calls backend, sets session state ────────────────────────
  async function beginSession(question, extractionId) {
    setLoading(true)
    try {
      const result = await startSession({ question, extractionId })
      setSession({
        sessionId:     result.session_id,
        question,
        currentStep:   1,
        maxSteps:      5,
        stepTitle:     result.step_title    || 'Step 1',
        explanation:   result.explanation   || '',
        guideQuestion: result.question      || '',
        hint:          result.hint          || null,
        isFinal:       result.is_final_step || false,
        finalAnswer:   result.final_answer  || null,
        skipCount:     0,   // tracks SHOW_NEXT_STEP uses in current step
      })
      setScreen(SCREENS.SESSION)
    } catch (e) {
      handleError(e)
    } finally {
      setLoading(false)
    }
  }

  // ── Called by SessionScreen after every action ───────────────────────────────
  // result = the API response object
  const handleStepResult = useCallback((result) => {
    if (result.is_final_step) {
      // Show completion screen
      setSession(prev => ({
        ...prev,
        finalAnswer:   result.final_answer  || prev.finalAnswer,
        explanation:   result.explanation   || prev.explanation,
        isFinal:       true,
      }))
      setScreen(SCREENS.COMPLETE)
      return
    }

    // Advance step — force new object reference so React re-renders
    setSession(prev => ({
      ...prev,
      currentStep:   Math.min((prev.currentStep || 1) + 1, prev.maxSteps),
      stepTitle:     result.step_title    || prev.stepTitle,
      explanation:   result.explanation   || prev.explanation,
      guideQuestion: result.question      || prev.guideQuestion,
      hint:          result.hint          || null,
      isFinal:       false,
      skipCount:     0,   // reset skip counter on new step
    }))
  }, [])

  // ── Called when hint/explain-again comes back (same step, don't advance) ─────
  const handleSameStepResult = useCallback((result) => {
    setSession(prev => ({
      ...prev,
      hint:        result.hint        || prev.hint,
      explanation: result.explanation || prev.explanation,
      // keep everything else the same
    }))
  }, [])

  // ── Called when Next Step is used (increment skip counter) ──────────────────
  const handleSkipResult = useCallback((result, newSkipCount) => {
    if (result.is_final_step) {
      setSession(prev => ({ ...prev, finalAnswer: result.final_answer, isFinal: true }))
      setScreen(SCREENS.COMPLETE)
      return
    }
    setSession(prev => ({
      ...prev,
      currentStep:   Math.min((prev.currentStep || 1) + 1, prev.maxSteps),
      stepTitle:     result.step_title    || prev.stepTitle,
      explanation:   result.explanation   || prev.explanation,
      guideQuestion: result.question      || prev.guideQuestion,
      hint:          null,
      isFinal:       false,
      skipCount:     newSkipCount,
    }))
  }, [])

  function reset() {
    setSession(null); setImage(null); setError(null)
    setScreen(SCREENS.QUESTION)
  }
  function goHome() {
    setSession(null); setImage(null); setError(null)
    setScreen(SCREENS.LANDING)
  }

  return (
    <div className="min-h-screen bg-brand-teal-light font-sans">
      <Navbar />

      {loading && (
        <div className="fixed inset-0 bg-white/60 z-50 flex items-center justify-center">
          <div className="flex flex-col items-center gap-3">
            <span className="spinner spinner-dark w-8 h-8" />
            <p className="text-sm text-brand-teal font-medium">Setting up your session...</p>
          </div>
        </div>
      )}

      {screen === SCREENS.LANDING && (
        <LandingScreen onStart={handleStart} />
      )}
      {screen === SCREENS.QUESTION && (
        <QuestionScreen onSubmit={handleQuestionSubmit} onBack={goHome} />
      )}
      {screen === SCREENS.IMAGE_CONFIRM && imageData && (
        <ImageConfirmScreen
          extractedText={imageData.extractedText}
          extractionId={imageData.extractionId}
          confidence={imageData.confidence}
          onConfirm={handleImageConfirm}
          onBack={() => setScreen(SCREENS.QUESTION)}
        />
      )}
      {screen === SCREENS.SESSION && session && (
        <SessionScreen
          key={session.sessionId}
          session={session}
          onStepAdvance={handleStepResult}
          onSameStep={handleSameStepResult}
          onSkip={handleSkipResult}
          onBack={() => setScreen(SCREENS.QUESTION)}
        />
      )}
      {screen === SCREENS.COMPLETE && session && (
        <CompletionScreen
          question={session.question}
          finalAnswer={session.finalAnswer}
          explanation={session.explanation}
          onTryAnother={reset}
          onHome={goHome}
        />
      )}
      {screen === SCREENS.ERROR && errorData && (
        <ErrorScreen
          code={errorData.code}
          message={errorData.message}
          onRetry={() => setScreen(SCREENS.QUESTION)}
          onHome={goHome}
        />
      )}
    </div>
  )
}
