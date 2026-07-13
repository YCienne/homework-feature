import React from 'react'

export default function Navbar() {
  return (
    <nav className="bg-white border-b border-gray-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Logo */}
        <span className="text-brand-teal font-bold text-xl tracking-tight">
          learnaiirium
        </span>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-8">
          {[
            { label: 'My Learning Focus' },
            { label: 'Courses' },
            { label: 'Ebooks' },
            { label: 'About' },
          ].map(({ label }) => (
            <button
              key={label}
              className="text-gray-700 hover:text-brand-teal text-sm font-medium transition-colors"
            >
              {label}
            </button>
          ))}
        </div>

        {/* Right side */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 bg-gray-50 border border-gray-200
                          rounded-full px-4 py-2 text-sm text-gray-400 w-48">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            Search courses...
          </div>
          <div className="w-10 h-10 rounded-full bg-brand-teal flex items-center justify-center text-white">
            <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
              <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2
                       7.2 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4
                       c0-3.2-6.4-4.8-9.6-4.8z"/>
            </svg>
          </div>
        </div>
      </div>
    </nav>
  )
}
