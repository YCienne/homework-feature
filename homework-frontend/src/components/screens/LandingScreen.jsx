import React from 'react'

const features = [
  {
    icon: (
      <svg className="w-5 h-5 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <circle cx="12" cy="12" r="9" strokeWidth={2}/>
        <circle cx="12" cy="12" r="4" strokeWidth={2}/>
        <circle cx="12" cy="12" r="1" fill="currentColor" strokeWidth={0}/>
      </svg>
    ),
    label: 'Guided step-by-step solutions',
  },
  {
    icon: (
      <svg className="w-5 h-5 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707
             m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4
             0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
      </svg>
    ),
    label: 'Hints when you need them',
  },
  {
    icon: (
      <svg className="w-5 h-5 text-brand-teal" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438
             0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806
             1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138
             3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0
             00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42
             3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z"/>
      </svg>
    ),
    label: 'Learn while you solve',
  },
]

export default function LandingScreen({ onStart }) {
  return (
    <div className="min-h-screen bg-brand-teal-light flex flex-col">
      {/* Breadcrumb */}
      <div className="border-b border-brand-teal-border bg-white/60 px-6 py-3
                      flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="text-brand-teal font-medium">My Learning Focus</span>
          <span className="text-gray-300">(Mathematics)</span>
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7"/>
          </svg>
          <span className="text-gray-700 font-medium">homework-help</span>
        </div>
        <button className="flex items-center gap-2 text-sm font-medium text-brand-teal
                           border border-brand-teal-border rounded-full px-4 py-1.5
                           hover:bg-brand-teal-light transition-colors">
          <span>⊙</span> Back to My Focus
        </button>
      </div>

      {/* Tip bar */}
      <div className="bg-white/40 border-b border-brand-teal-border px-6 py-2 text-sm text-gray-600">
        <span className="text-yellow-500 mr-1">💡</span>
        <span className="font-medium">Tip:</span>
        {' '}This is optional browsing. Your weekly focus on{' '}
        <strong className="text-brand-teal">Mathematics</strong> is waiting for you.
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col items-center px-4 py-8">
        {/* Back */}
        <div className="w-full max-w-2xl mb-6">
          <button className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-colors">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7"/>
            </svg>
            Back
          </button>
        </div>

        {/* Card */}
        <div className="card w-full max-w-2xl p-10 flex flex-col items-center text-center">
          {/* Brain icon */}
          <div className="w-20 h-20 rounded-2xl flex items-center justify-center mb-6"
               style={{ background: 'linear-gradient(135deg, #2ab5a5, #1a9e8f)' }}>
            <svg className="w-10 h-10 text-white" fill="currentColor" viewBox="0 0 24 24">
              <path d="M13 3a4 4 0 014 4c0 .35-.05.69-.13 1.02A4 4 0 0119 11a4 4 0 01-2
                       3.46V16a3 3 0 01-3 3H10a3 3 0 01-3-3v-1.54A4 4 0 015 11a4 4 0
                       012.13-3.54A4.003 4.003 0 017 7a4 4 0 014-4h2zm-1 2H11a2 2 0
                       00-2 2c0 .34.09.66.23.94l.27.52-.55.26A2 2 0 007 10.59V11a2
                       2 0 001.5 1.94V16a1 1 0 001 1h4a1 1 0 001-1v-3.06A2 2 0
                       0017 11v-.41a2 2 0 00-1.45-1.92l-.55-.18.22-.55A1.99 1.99
                       0 0015.27 7 2 2 0 0013 5z"/>
            </svg>
          </div>

          <h1 className="text-4xl font-bold text-gray-900 mb-3">Homework Help</h1>
          <p className="text-gray-500 text-base mb-8">Get step-by-step help with your homework</p>

          {/* Features */}
          <div className="w-full space-y-4 mb-10">
            {features.map(({ icon, label }) => (
              <div key={label} className="flex items-center gap-3 text-left">
                <div className="w-10 h-10 rounded-full bg-brand-teal-light border border-brand-teal-border
                                flex items-center justify-center flex-shrink-0">
                  {icon}
                </div>
                <span className="text-gray-700 font-medium">{label}</span>
              </div>
            ))}
          </div>

          {/* CTA */}
          <button onClick={onStart} className="btn-gradient">
            Start
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
