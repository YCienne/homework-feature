/**
 * homeworkApi.js — all calls to the homework-service backend.
 *
 * Auth token priority:
 *   1. VITE_DEV_TOKEN in .env  (dev bypass — no Cognito needed)
 *   2. localStorage 'learnarium_token'  (real Cognito JWT in production)
 */

const BASE_URL = import.meta.env.VITE_HOMEWORK_API_URL || '/homework'
const DEV_TOKEN = import.meta.env.VITE_DEV_TOKEN || null

function getToken() {
  if (DEV_TOKEN) return DEV_TOKEN
  const token = localStorage.getItem('learnarium_token')
  if (!token) throw new Error('Not authenticated')
  return token
}

function getAuthHeaders() {
  return {
    'Authorization': `Bearer ${getToken()}`,
    'Content-Type': 'application/json',
  }
}

async function handleResponse(res) {
  const data = await res.json()
  if (!res.ok) {
    const message = data?.detail?.message || data?.message || 'Something went wrong.'
    const error = new Error(message)
    error.code   = data?.detail?.error || 'UNKNOWN_ERROR'
    error.status = res.status
    throw error
  }
  return data
}

export async function startSession({ question, extractionId, lessonSubject, lessonTopic }) {
  const body = { student_id: 'from_token', question }
  if (extractionId)  body.extraction_id  = extractionId
  if (lessonSubject) body.lesson_subject = lessonSubject
  if (lessonTopic)   body.lesson_topic   = lessonTopic

  const res = await fetch(`${BASE_URL}/session/start`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function sendAction({ sessionId, action, response }) {
  const body = { action }
  if (response) body.response = response

  const res = await fetch(`${BASE_URL}/session/${sessionId}/action`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function extractImage(file) {
  const formData = new FormData()
  formData.append('image', file)

  const res = await fetch(`${BASE_URL}/image/extract`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${getToken()}` },
    body: formData,
  })
  return handleResponse(res)
}

export async function getUsage(studentId) {
  const res = await fetch(`${BASE_URL}/usage/${studentId}`, {
    headers: getAuthHeaders(),
  })
  return handleResponse(res)
}

export async function getSession(sessionId) {
  const res = await fetch(`${BASE_URL}/session/${sessionId}`, {
    headers: getAuthHeaders(),
  })
  return handleResponse(res)
}
