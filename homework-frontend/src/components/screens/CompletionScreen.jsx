import React from 'react'

export default function CompletionScreen({ question, finalAnswer, explanation, onTryAnother, onHome }) {
  return (
    <div className="min-h-screen bg-brand-teal-light flex flex-col items-center px-4 py-8">
      <div className="w-full max-w-xl">
        <div className="card overflow-hidden">

          {/* Teal gradient header with trophy */}
          <div className="flex items-center justify-center py-10"
               style={{ background: 'linear-gradient(135deg, #2ab5a5, #1a9e8f)' }}>
            <div className="w-20 h-20 rounded-full bg-white flex items-center justify-center shadow-lg">
              <svg className="w-10 h-10 text-orange-400" fill="currentColor" viewBox="0 0 24 24">
                <path d="M19 5h-2V3H7v2H5C3.9 5 3 5.9 3 7v1c0 2.55 1.92 4.63 4.39 4.94.63
                         1.5 1.98 2.63 3.61 2.96V18H9v2h6v-2h-2v-2.1c1.63-.33 2.98-1.46
                         3.61-2.96C19.08 12.63 21 10.55 21 8V7c0-1.1-.9-2-2-2zM5 8V7h2v3.82
                         C5.84 10.4 5 9.3 5 8zm14 0c0 1.3-.84 2.4-2 2.82V7h2v1z"/>
              </svg>
            </div>
          </div>

          <div className="p-8 flex flex-col items-center text-center">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Great job!</h1>
            <p className="text-gray-500 text-sm mb-7">You've completed all the steps!</p>

            {/* Final answer card */}
            <div className="w-full border-2 border-brand-teal-border rounded-2xl p-6 mb-8">
              <p className="text-xs font-semibold text-brand-teal uppercase tracking-widest mb-3">
                Final Answer
              </p>
              {finalAnswer && (
                <p className="text-2xl font-bold text-gray-900 mb-4 pb-4 border-b border-gray-100">
                  {finalAnswer}
                </p>
              )}
              {explanation && (
                <p className="text-sm text-gray-600 leading-relaxed">
                  {explanation}
                </p>
              )}
            </div>

            {/* Actions */}
            <button onClick={onTryAnother} className="btn-gradient mb-3">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0
                     0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
              </svg>
              Try another problem
            </button>

            <button
              onClick={onHome}
              className="w-full py-3.5 rounded-full border-2 border-gray-200 text-gray-700
                         font-semibold text-sm hover:border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Back to Home
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
