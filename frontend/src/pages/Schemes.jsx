import { useState, useEffect } from 'react'
import { api } from '../api'
import './Page.css'
import './Schemes.css'

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

export default function Schemes() {
  const [schemes, setSchemes] = useState([])
  const [stats, setStats] = useState({ total_schemes: 0, last_updated: null })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lang, setLang] = useState('en')
  const [scraping, setScraping] = useState(false)
  const [categoryFilter, setCategoryFilter] = useState('')

  useEffect(() => {
    loadSchemes()
    api.getStats().then(setStats).catch(() => {})
  }, [lang])

  async function loadSchemes() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getSchemes(lang)
      setSchemes(data)
      api.getStats().then(setStats).catch(() => {})
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleScrape() {
    setScraping(true)
    setError(null)
    try {
      const res = await api.scrape()
      await loadSchemes()
      alert(res.message)
    } catch (e) {
      setError(e.message)
    } finally {
      setScraping(false)
    }
  }

  const categories = [...new Set(schemes.map((s) => s.category).filter(Boolean))].sort()
  const filtered = categoryFilter
    ? schemes.filter((s) => s.category === categoryFilter)
    : schemes

  const lastUpdated = stats.last_updated
    ? new Date(stats.last_updated).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : null

  return (
    <div className="page">
      <div className="page-header schemes-header">
        <div>
          <h2>Government Schemes</h2>
          <p>Browse women-related government schemes. Use the language selector for translations.</p>
        </div>
        <div className="schemes-meta">
          {lastUpdated && (
            <span className="last-updated">Last updated: {lastUpdated}</span>
          )}
          <div className="page-actions">
            <select value={lang} onChange={(e) => setLang(e.target.value)} className="select">
              {LANG_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
            {categories.length > 0 && (
              <select
                value={categoryFilter}
                onChange={(e) => setCategoryFilter(e.target.value)}
                className="select"
              >
                <option value="">All categories</option>
                {categories.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            )}
            <button onClick={handleScrape} disabled={scraping} className="btn btn-secondary">
              {scraping ? 'Updating...' : 'Refresh schemes'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <div className="loading">Loading schemes...</div>}

      {!loading && schemes.length === 0 && (
        <div className="empty">
          <p>No schemes found. Click &quot;Refresh schemes&quot; to load from official sources.</p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="scheme-grid">
          {filtered.map((s) => (
            <article key={s.id} className="card scheme-card">
              <div className="scheme-card-header">
                {s.category && <span className="scheme-category">{s.category}</span>}
                <h3>{s.name}</h3>
              </div>
              {s.description && <p className="card-desc">{s.description}</p>}
              {s.benefits && (
                <div className="card-benefits">
                  <strong>Benefits:</strong>
                  <p>{s.benefits}</p>
                </div>
              )}
              {s.eligibility_text && (
                <p className="card-meta"><strong>Eligibility:</strong> {s.eligibility_text.slice(0, 120)}…</p>
              )}
              {s.income_limit && (
                <p className="card-meta">Income limit: ₹{s.income_limit.toLocaleString()}</p>
              )}
              <div className="scheme-card-footer">
                {s.application_link && (
                  <a href={s.application_link} target="_blank" rel="noopener noreferrer" className="btn btn-small btn-primary">
                    Apply →
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  )
}
