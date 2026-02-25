import { useState } from 'react'
import { api } from '../api'
import './Page.css'

const LANG_OPTIONS = [
  { value: 'en', label: 'English' },
  { value: 'hi', label: 'हिन्दी' },
  { value: 'ta', label: 'தமிழ்' },
  { value: 'te', label: 'తెలుగు' },
  { value: 'mr', label: 'मराठी' },
  { value: 'bn', label: 'বাংলা' },
  { value: 'gu', label: 'ગુજરાતી' },
  { value: 'kn', label: 'ಕನ್ನಡ' },
  { value: 'ml', label: 'മലയാളം' },
  { value: 'pa', label: 'ਪੰਜਾਬੀ' },
]

export default function Simplify() {
  const [text, setText] = useState('')
  const [simplified, setSimplified] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lang, setLang] = useState('en')

  async function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim()) return

    setLoading(true)
    setError(null)
    setSimplified(null)
    try {
      const data = await api.simplify(text.trim(), lang)
      setSimplified(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleExample() {
    const example = "The applicant must be a beneficiary pursuant to the BPL list. Notwithstanding the foregoing, income not exceeding Rs. 2.5 lakh per annum is mandatory."
    setText(example)
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Simplify Text</h2>
        <p>Convert complex legal or eligibility text into simple, readable language.</p>
      </div>

      <form onSubmit={handleSubmit} className="form card">
        <div className="form-row">
          <label htmlFor="text">Text to simplify</label>
          <textarea
            id="text"
            rows={5}
            placeholder="Paste complex eligibility or legal text here..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label>Output language</label>
          <select value={lang} onChange={(e) => setLang(e.target.value)} className="select">
            {LANG_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <div className="form-actions">
          <button type="button" onClick={handleExample} className="btn btn-secondary">
            Load example
          </button>
          <button type="submit" disabled={loading || !text.trim()} className="btn btn-primary">
            {loading ? 'Simplifying...' : 'Simplify'}
          </button>
        </div>
      </form>

      {error && <div className="alert alert-error">{error}</div>}

      {simplified && (
        <div className="simplify-result card">
          <h3>Simplified result</h3>
          <div className="result-box">
            <p>{simplified.simplified}</p>
          </div>
          <details className="original-details">
            <summary>Original text</summary>
            <p>{simplified.original}</p>
          </details>
        </div>
      )}
    </div>
  )
}
