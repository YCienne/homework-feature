import React, { useState, useRef } from 'react'
import { extractImage } from '../../services/index.js'
import Toast from '../ui/Toast'

export default function QuestionScreen({ onSubmit, onBack }) {
  const [question, setQuestion]         = useState('')
  const [loading, setLoading]           = useState(false)
  const [imageLoading, setImageLoading] = useState(false)
  const [fileName, setFileName]         = useState('')
  const [error, setError]               = useState('')
  const [toast, setToast]               = useState(null)
  const fileRef = useRef()

  // ── Text submit ──────────────────────────────────────────────────────────────
  async function handleSubmit() {
    if (!question.trim()) {
      setError("Please type your question before continuing.")
      return
    }
    setLoading(true)
    setError('')
    try {
      await onSubmit({ question: question.trim() })
    } catch (e) {
      setError(e.message || 'Something went wrong. Please try again.')
      setLoading(false)
    }
  }

  // ── Image upload ─────────────────────────────────────────────────────────────
  async function handleFile(e) {
    const file = e.target.files[0]
    if (!file) return

    const allowed = ['image/jpeg', 'image/png', 'image/webp']
    if (!allowed.includes(file.type)) {
      setError('Please upload a JPEG, PNG, or WebP image.')
      return
    }
    if (file.size > 5 * 1024 * 1024) {
      setError('Image must be under 5MB.')
      return
    }

    setFileName(file.name)
    setImageLoading(true)
    setError('')

    try {
      const result = await extractImage(file)
      setImageLoading(false)
      setToast({ message: 'Question extracted!', subtitle: 'Review it before continuing' })
      // Hand off to confirmation screen
      await onSubmit({
        extractedText:  result.extracted_text,
        extractionId:   result.extraction_id,
        confidence:     result.confidence,
        fromImage:      true,
      })
    } catch (e) {
      setImageLoading(false)
      setFileName('')
      setError(e.message || "Sorry, I couldn't read this clearly. Please type the question.")
    }
  }

  const isProcessing = loading || imageLoading

  return (
    <div className="min-h-screen bg-brand-teal-light flex flex-col">
      {toast && (
        <Toast
          message={toast.message}
          subtitle={toast.subtitle}
          type="success"
          onClose={() => setToast(null)}
        />
      )}

      <div className="flex-1 flex flex-col items-center px-4 py-8">
        {/* Back */}
        <div className="w-full max-w-xl mb-4">
          <button onClick={onBack}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/>
            </svg>
            Back
          </button>
        </div>

        {/* Card */}
        <div className="card w-full max-w-xl p-8 flex flex-col items-center">

          {/* Book icon — purple-pink gradient */}
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-5"
               style={{ background: 'linear-gradient(135deg, #9333ea, #ec4899)' }}>
            <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 2C8.13 2 5 5.13 5 9v11l7-3 7 3V9c0-3.87-3.13-7-7-7zm0 2
                       c2.76 0 5 2.24 5 5v8.18l-5-2.14-5 2.14V9c0-2.76 2.24-5 5-5z"/>
            </svg>
          </div>

          <h1 className="text-3xl font-bold text-gray-900 mb-2 text-center">
            What's your question?
          </h1>
          <p className="text-gray-500 text-sm mb-7 text-center">
            Type it or upload an image
          </p>

          {/* Text input */}
          <div className="w-full mb-5">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your homework question
            </label>
            <div className="relative">
              <textarea
                value={question}
                onChange={e => { setQuestion(e.target.value); setError('') }}
                placeholder="Type your homework question here..."
                rows={5}
                disabled={isProcessing}
                className={`w-full border-2 rounded-xl px-4 py-3 text-sm text-gray-800
                            resize-none outline-none transition-all placeholder:text-gray-400
                            disabled:bg-gray-50 disabled:text-gray-400
                            ${error && !imageLoading
                              ? 'border-red-300 focus:border-red-400'
                              : question
                                ? 'border-purple-400 focus:border-purple-500'
                                : 'border-gray-200 focus:border-purple-400'}`}
              />
              {question && (
                <div className="absolute bottom-3 right-3 w-6 h-6 rounded-full bg-green-500
                                flex items-center justify-center">
                  <svg className="w-3.5 h-3.5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7"/>
                  </svg>
                </div>
              )}
            </div>
            {error && (
              <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">
                <svg className="w-3.5 h-3.5 flex-shrink-0" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2
                           12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                </svg>
                {error}
              </p>
            )}
          </div>

          {/* Divider */}
          <div className="w-full flex items-center gap-3 mb-5">
            <hr className="flex-1 border-gray-200" />
            <span className="text-sm text-gray-400">or</span>
            <hr className="flex-1 border-gray-200" />
          </div>

          {/* Image upload */}
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={handleFile}
          />
          <button
            onClick={() => !isProcessing && fileRef.current.click()}
            disabled={isProcessing}
            className="w-full border-2 border-dashed border-brand-teal-border rounded-xl
                       py-4 flex items-center justify-center gap-2 text-brand-teal
                       font-medium text-sm hover:bg-brand-teal-light transition-colors
                       disabled:opacity-60 disabled:cursor-not-allowed mb-2"
          >
            {imageLoading ? (
              <>
                <span className="spinner spinner-dark" />
                Processing image...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                </svg>
                Upload image
              </>
            )}
          </button>
          {fileName && (
            <p className="text-xs text-gray-400 mb-3 text-center">{fileName}</p>
          )}

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={isProcessing || !question.trim()}
            className="btn-gradient mt-2"
          >
            {loading ? (
              <>
                <span className="spinner" />
                Processing...
              </>
            ) : (
              <>
                Get Help
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M17 8l4 4m0 0l-4 4m4-4H3"/>
                </svg>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}
