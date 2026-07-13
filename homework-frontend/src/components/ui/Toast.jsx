import React, { useEffect } from 'react'

export default function Toast({ message, subtitle, type = 'success', onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 3500)
    return () => clearTimeout(t)
  }, [onClose])

  const styles = {
    success: 'bg-gray-900 text-white',
    error:   'bg-red-600 text-white',
    warning: 'bg-amber-500 text-white',
    info:    'bg-gray-700 text-white',
  }

  const icons = {
    success: (
      <div className="w-5 h-5 rounded-full bg-green-400 flex items-center justify-center flex-shrink-0 mt-0.5">
        <svg className="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
        </svg>
      </div>
    ),
    info: (
      <div className="w-5 h-5 rounded-full bg-blue-400 flex items-center justify-center flex-shrink-0 mt-0.5">
        <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
        </svg>
      </div>
    ),
    error: (
      <div className="w-5 h-5 rounded-full bg-red-300 flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-white text-xs font-bold">!</span>
      </div>
    ),
    warning: (
      <div className="w-5 h-5 rounded-full bg-yellow-300 flex items-center justify-center flex-shrink-0 mt-0.5">
        <span className="text-white text-xs font-bold">!</span>
      </div>
    ),
  }

  return (
    <div className={`fixed top-4 left-1/2 -translate-x-1/2 z-50 rounded-xl px-5 py-3
                     shadow-xl flex items-start gap-3 min-w-72 max-w-sm
                     animate-fade-in ${styles[type] || styles.success}`}>
      {icons[type] || icons.success}
      <div>
        <p className="font-semibold text-sm">{message}</p>
        {subtitle && <p className="text-xs opacity-80 mt-0.5">{subtitle}</p>}
      </div>
    </div>
  )
}
