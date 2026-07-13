/**
 * mockApi.js — bypasses auth/session but uses real Gemini API for responses.
 * Set VITE_USE_MOCK=true and VITE_GEMINI_API_KEY=your-key in .env
 *
 * Flow:
 *   startSession()  → sends question to Gemini, gets Step 1
 *   sendAction()    → sends action + history to Gemini, gets next step
 *   extractImage()  → sends image to Gemini Vision, gets extracted text
 */

const GEMINI_KEY = import.meta.env.VITE_GEMINI_API_KEY
const GEMINI_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`

const delay = (ms = 300) => new Promise(r => setTimeout(r, ms))

// ── In-memory session state (replaces Redis) ──────────────────────────────────
let _session = {
  sessionId:        'mock-session-001',
  question:         '',
  subject:          'general',
  currentStepIndex: 0,
  maxSteps:         5,
  stepHistory:      [],       // [{ question, studentResponse }]
  lastStepQuestion: '',
  lastExplanation:  '',
}

// ── Gemini call ───────────────────────────────────────────────────────────────
async function callGemini(prompt) {
  const res = await fetch(GEMINI_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{ parts: [{ text: prompt }] }],
      generationConfig: { temperature: 0.3, maxOutputTokens: 800 },
    }),
  })

  if (!res.ok) {
    const err = await res.json()
    throw new Error(err?.error?.message || 'Gemini API error')
  }

  const data = await res.json()
  const raw = data.candidates?.[0]?.content?.parts?.[0]?.text || ''
  return parseGeminiResponse(raw)
}

// ── Parse JSON from Gemini response (strips markdown fences if present) ───────
function parseGeminiResponse(raw) {
  try {
    let text = raw.trim()
    if (text.startsWith('```')) {
      text = text.replace(/^```json?\n?/, '').replace(/\n?```$/, '').trim()
    }
    return JSON.parse(text)
  } catch {
    // Fallback if Gemini returns non-JSON
    return {
      step_title:    'Let\'s continue',
      explanation:   raw.trim().slice(0, 400),
      question:      'What do you think the next step should be?',
      hint:          null,
      final_answer:  null,
      is_final_step: false,
    }
  }
}

// ── Shared system prompt rules ────────────────────────────────────────────────
const SYSTEM_RULES = `
You are a patient, encouraging tutor for students aged 10-18.
You MUST respond ONLY with a valid JSON object — no markdown, no text outside the JSON.
Never give the full answer until is_final_step is true.
Keep explanation under 300 characters.

Required JSON format:
{
  "step_title": "string",
  "explanation": "string (max 300 chars)",
  "question": "string (ONE guiding question — required unless is_final_step is true)",
  "hint": null,
  "final_answer": null,
  "is_final_step": false
}
`

// ── START: first step ─────────────────────────────────────────────────────────
export async function startSession({ question }) {
  _session = {
    sessionId:        'mock-session-001',
    question,
    currentStepIndex: 0,
    maxSteps:         5,
    stepHistory:      [],
    lastStepQuestion: '',
    lastExplanation:  '',
  }

  const prompt = `${SYSTEM_RULES}

The student submitted this homework problem:
"${question}"

This is Step 1 of 5.
Restate the problem simply, then ask ONE guiding question to help the student identify what they already know.
Do NOT solve the problem. Set is_final_step to false.`

  const result = await callGemini(prompt)
  _session.lastStepQuestion = result.question || ''
  _session.lastExplanation  = result.explanation || ''

  return { ...result, session_id: _session.sessionId }
}

// ── ACTION: continue / hint / skip / explain again ───────────────────────────
export async function sendAction({ action, response }) {
  const { question, currentStepIndex, maxSteps, stepHistory, lastStepQuestion, lastExplanation } = _session

  const historyText = stepHistory.map((s, i) =>
    `Step ${i + 1} question: ${s.question}\nStudent answered: ${s.studentResponse || '(skipped)'}`
  ).join('\n\n')

  const isLastStep = currentStepIndex >= maxSteps - 1

  let prompt = ''

  if (action === 'CONTINUE') {
    _session.stepHistory.push({ question: lastStepQuestion, studentResponse: response })
    _session.currentStepIndex += 1

    if (isLastStep) {
      prompt = `${SYSTEM_RULES}

Problem: "${question}"
Progress so far:
${historyText}
Student's final response: "${response}"

This is the LAST step. The student has completed all steps.
Evaluate their response, deliver the final answer, and give a warm closing explanation.
Set is_final_step to true and populate final_answer.
Set question to null.`
    } else {
      prompt = `${SYSTEM_RULES}

Problem: "${question}"
Progress so far:
${historyText}
Student just answered Step ${currentStepIndex + 1}: "${response}"

This is Step ${_session.currentStepIndex + 1} of ${maxSteps}.
Evaluate their answer (confirm if correct, gently correct if wrong).
Then guide them to the next step with ONE new question.
Do NOT give the final answer. Set is_final_step to false.`
    }
  }

  else if (action === 'IM_NOT_SURE') {
    prompt = `${SYSTEM_RULES}

Problem: "${question}"
The student is stuck on this question: "${lastStepQuestion}"
They clicked "I'm not sure".

Provide a helpful hint that nudges them in the right direction.
Do NOT reveal the answer. Keep the same question.
Set is_final_step to false.`
  }

  else if (action === 'SHOW_NEXT_STEP') {
    _session.stepHistory.push({ question: lastStepQuestion, studentResponse: null })
    _session.currentStepIndex += 1

    prompt = `${SYSTEM_RULES}

Problem: "${question}"
Progress so far:
${historyText || 'No steps completed yet.'}

The student skipped to Step ${_session.currentStepIndex + 1} of ${maxSteps}.
Briefly acknowledge where they are and present the next step with ONE guiding question.
Do NOT give the final answer. Set is_final_step to false.`
  }

  else if (action === 'EXPLAIN_AGAIN') {
    prompt = `${SYSTEM_RULES}

Problem: "${question}"
The current step explanation was: "${lastExplanation}"
The current step question is: "${lastStepQuestion}"

The student clicked "Explain again".
Re-explain this step using simpler language or a different example.
Keep the same question at the end. Set is_final_step to false.`
  }

  const result = await callGemini(prompt)
  _session.lastStepQuestion = result.question || _session.lastStepQuestion
  _session.lastExplanation  = result.explanation || ''

  return { ...result, session_id: _session.sessionId }
}

// ── IMAGE EXTRACT: uses Gemini Vision ─────────────────────────────────────────
export async function extractImage(file) {
  await delay(200)

  // Convert file to base64
  const base64 = await new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload  = () => resolve(reader.result.split(',')[1])
    reader.onerror = reject
    reader.readAsDataURL(file)
  })

  const VISION_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_KEY}`

  const res = await fetch(VISION_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      contents: [{
        parts: [
          {
            inline_data: {
              mime_type: file.type,
              data: base64,
            }
          },
          {
            text: `Extract ALL text from this image exactly as it appears.
Preserve mathematical symbols and equations.
Do not solve or interpret — only transcribe.
Return ONLY the extracted text, nothing else.`
          }
        ]
      }],
      generationConfig: { temperature: 0.1, maxOutputTokens: 500 },
    }),
  })

  if (!res.ok) {
    const err = await res.json()
    throw Object.assign(new Error("Sorry, I couldn't read this clearly. Please type the question."), { code: 'IMAGE_UNREADABLE' })
  }

  const data = await res.json()
  const extracted = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() || ''

  if (!extracted || extracted.length < 5) {
    throw Object.assign(new Error("Sorry, I couldn't read this clearly. Please type the question."), { code: 'IMAGE_UNREADABLE' })
  }

  return {
    extraction_id:  'mock-extraction-' + Date.now(),
    extracted_text: extracted,
    confidence:     'high',
    message:        'Text extracted successfully. Please confirm this is correct.',
  }
}

// ── Unused in mock — kept for API compatibility ───────────────────────────────
export async function getUsage() {
  return { sessions_today: 1, sessions_limit: 5, sessions_remaining: 4 }
}

export async function getSession() {
  return {}
}
