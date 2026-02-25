const API_BASE = '/api'

async function fetchApi(path, options = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || res.statusText)
  }
  return res.json()
}

export const api = {
  getSchemes: (lang = 'en') => fetchApi(`/schemes?lang=${lang}`),
  getStats: () => fetchApi('/stats'),
  getLanguages: () => fetchApi('/languages'),
  checkEligibility: (profile) => fetchApi('/check-eligibility', {
    method: 'POST',
    body: JSON.stringify(profile),
  }),
  chat: (message, lang = 'en') => fetchApi('/chat', {
    method: 'POST',
    body: JSON.stringify({ message, lang }),
  }),
  simplify: (text, lang = 'en') => fetchApi('/simplify', {
    method: 'POST',
    body: JSON.stringify({ text, lang }),
  }),
  scrape: () => fetchApi('/scrape', { method: 'POST' }),
}
