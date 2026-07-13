import React from 'react'

const ERROR_CONFIGS = {
  DAILY_LIMIT_REACHED: {
    icon: '🚫',
    title: 'Daily limit reached',
    color: 'text-amber-600',
    bg: 'bg-amber-50 border-amber-200',
  },
  SESSION_NOT_FOUND: {
    icon: '⏱',
    title: 'Session expired',
    color: 'text-blue-600',
    bg: 'bg-blue-50 border-blue-200',
  },
  IMAGE_UNREADABLE: {
    icon: '🖼',
    title: "Couldn't read image",
    color: 'text-red-600',
    bg: 'bg-red-50 border-red-200',
  },
  INTERNAL_ERROR: {
    icon: '⚠️',
    title: 'Something went wrong',
    color: 'text-red-600',
    bg: 'bg-red-50 border-red-200',
  },
}

export default function ErrorScreen({ code, message, onRetry, onHome }) {
  const config = ERROR_CONFIGS[code] || ERROR_CONFIGS.INTERNAL_ERROR

  return (
    <div className="min-h-screen bg-brand-teal-light flex flex-col items-center
                    justify-center px-4 py-8">
      <div className="card w-full max-w-md p-8 flex flex-col items-center text-center">
        <div className="text-5xl mb-4">{config.icon}</div>

        <h2 className={`text-xl font-bold mb-2 ${config.color}`}>
          {config.title}
        </h2>

        <div className={`w-full border rounded-xl p-4 mb-6 text-sm ${config.bg}`}>
          {message || 'Something went wrong. Please try again.'}
        </div>

        <button onClick={onRetry} className="btn-gradient mb-3">
          Try again
        </button>

        <button
          onClick={onHome}
          className="w-full py-3 rounded-full border-2 border-gray-200
                     text-gray-700 font-medium text-sm hover:bg-gray-50 transition-colors"
        >
          Back to Home
        </button>
      </div>
    </div>
  )
}
