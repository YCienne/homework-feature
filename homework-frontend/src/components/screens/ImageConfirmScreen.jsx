import React, { useState } from 'react'

export default function ImageConfirmScreen({ extractedText, extractionId, confidence, onConfirm, onBack }) {
  const [text, setText] = useState(extractedText)
  const [editing, setEditing] = useState(false)

  return (
    <div className="min-h-screen bg-brand-teal-light flex flex-col">
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
          {/* Image icon — teal */}
          <div className="w-16 h-16 rounded-2xl bg-brand-teal flex items-center justify-center mb-5">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828
                   0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2
                   2v12a2 2 0 002 2z"/>
            </svg>
          </div>

          <h1 className="text-2xl font-bold text-gray-900 mb-2 text-center">
            Check your question
          </h1>
          <p className="text-gray-500 text-sm mb-7 text-center">
            Make sure this is correct before continuing
          </p>

          {/* Extracted text box */}
          <div className="w-full mb-2">
            <div className="flex items-center gap-2 mb-3">
              <svg className="w-5 h-5 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
              </svg>
              <span className="font-semibold text-sm text-gray-800">Extracted text</span>
            </div>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              readOnly={!editing}
              rows={4}
              className={`w-full border-2 rounded-xl px-4 py-3 text-sm text-gray-800
                          resize-none outline-none transition-all
                          ${editing
                            ? 'border-purple-400 bg-white'
                            : 'border-brand-teal-border bg-brand-teal-light'}`}
            />
            {confidence === 'medium' && (
              <p className="text-xs text-amber-600 mt-1.5">
                ⚠ Some parts may be unclear. Please review carefully.
              </p>
            )}
            <p className="text-xs text-gray-400 mt-1.5">
              You can edit the text if anything looks wrong
            </p>
          </div>

          {/* Actions */}
          <div className="w-full flex gap-3 mt-4">
            <button
              onClick={() => setEditing(e => !e)}
              className="flex-1 flex items-center justify-center gap-2 border-2
                         border-gray-200 rounded-full py-3 text-sm font-medium
                         text-gray-700 hover:border-purple-300 transition-colors"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2
                     2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
              </svg>
              {editing ? 'Done editing' : 'Edit'}
            </button>
            <button
              onClick={() => onConfirm({ question: text.trim(), extractionId })}
              className="flex-1 flex items-center justify-center gap-2 rounded-full py-3
                         text-sm font-semibold text-white transition-opacity"
              style={{ background: 'linear-gradient(to right, #7c3aed, #ec4899)' }}
            >
              Continue
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17 8l4 4m0 0l-4 4m4-4H3"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
