import { useState } from 'react'
import { Link } from 'react-router-dom'
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

export default function Eligibility() {
  const [income, setIncome] = useState('')
  const [state, setState] = useState('')
  const [age, setAge] = useState('')
  const [lang, setLang] = useState('en')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    setResults(null)
    try {
      const incomeNum = income ? parseFloat(income) : null
      const ageNum = age ? parseInt(age, 10) : null
      const profile = {
        income: incomeNum != null && !isNaN(incomeNum) ? incomeNum : undefined,
        state: (state || '').trim() || undefined,
        age: ageNum != null && !isNaN(ageNum) ? ageNum : undefined,
        lang,
      }
      const data = await api.checkEligibility(profile)
      setResults(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Check Eligibility</h2>
        <p>Enter your profile to see which schemes you may be eligible for.</p>
      </div>

      <form onSubmit={handleSubmit} className="form card">
        <div className="form-row">
          <label htmlFor="income">Annual Income (₹)</label>
          <input
            id="income"
            type="number"
            placeholder="e.g. 200000"
            value={income}
            onChange={(e) => setIncome(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label htmlFor="state">State</label>
          <input
            id="state"
            type="text"
            placeholder="e.g. Maharashtra"
            value={state}
            onChange={(e) => setState(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label htmlFor="age">Age</label>
          <input
            id="age"
            type="number"
            placeholder="e.g. 28"
            min="0"
            max="120"
            value={age}
            onChange={(e) => setAge(e.target.value)}
          />
        </div>
        <div className="form-row">
          <label>Language</label>
          <select value={lang} onChange={(e) => setLang(e.target.value)} className="select">
            {LANG_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
        <button type="submit" disabled={loading} className="btn btn-primary">
          {loading ? 'Checking...' : 'Check Eligibility'}
        </button>
      </form>

      {error && (
        <div className="alert alert-error">
          {error}
          {error.includes('No schemes') && (
            <p style={{ marginTop: '0.5rem' }}>
              <Link to="/schemes">Go to Schemes</Link> and click &quot;Refresh schemes&quot; to load data.
            </p>
          )}
        </div>
      )}

      {results && (
        <div className="results-section">
          <h3>Results ({results.total_eligible} of {results.total_checked} eligible)</h3>
          <div className="results-list">
            {results.eligible_schemes.map((r) => (
              <div key={r.scheme_id} className={`card result-card ${r.eligible ? 'eligible' : 'not-eligible'}`}>
                <div className="result-header">
                  <strong>{r.scheme_name}</strong>
                  <span className={`badge ${r.eligible ? 'badge-success' : 'badge-neutral'}`}>
                    {r.eligible ? 'Eligible' : 'Not eligible'}
                  </span>
                </div>
                <p className="result-reason">{r.reason}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
