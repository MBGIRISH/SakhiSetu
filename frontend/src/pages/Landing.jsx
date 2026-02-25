import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import './Landing.css'

const BENEFITS = [
  {
    icon: '📋',
    title: 'Discover Schemes',
    desc: 'Browse 25+ government schemes for women across maternity, education, livelihood, safety, and economic empowerment.',
  },
  {
    icon: '✓',
    title: 'Instant Eligibility Check',
    desc: 'Enter your profile once and instantly see which schemes you qualify for—no need to read lengthy documents.',
  },
  {
    icon: '💬',
    title: 'AI-Powered Chat',
    desc: 'Ask questions in plain language. Get answers in 10 Indian languages with sources from official scheme data.',
  },
  {
    icon: '📖',
    title: 'Simplified Text',
    desc: 'Complex eligibility text simplified into easy-to-understand language. Available in multiple languages.',
  },
  {
    icon: '🔄',
    title: 'Always Up-to-Date',
    desc: 'Schemes are scraped from official government sources and updated automatically when new schemes are added.',
  },
  {
    icon: '🌐',
    title: 'Multilingual',
    desc: 'Access in English, Hindi, Tamil, Telugu, Marathi, Bengali, Gujarati, Kannada, Malayalam, and Punjabi.',
  },
]

export default function Landing() {
  const [stats, setStats] = useState({ total_schemes: 0, last_updated: null })

  useEffect(() => {
    api.getStats()
      .then(setStats)
      .catch(() => {})
  }, [])

  const lastUpdated = stats.last_updated
    ? new Date(stats.last_updated).toLocaleDateString('en-IN', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : null

  return (
    <div className="landing">
      <section className="hero">
        <div className="hero-content">
          <h1 className="hero-title">
            <span className="hero-bridge">SakhiSetu</span>
            <br />
            Your Bridge to Government Schemes
          </h1>
          <p className="hero-subtitle">
            Find, understand, and apply for women-focused government schemes in India.
            One platform. Multiple languages. Always updated.
          </p>
          <div className="hero-actions">
            <Link to="/schemes" className="btn btn-primary btn-hero">
              Browse Schemes
            </Link>
            <Link to="/eligibility" className="btn btn-outline btn-hero">
              Check Eligibility
            </Link>
          </div>
        </div>
        <div className="hero-stats">
          <div className="stat-card">
            <span className="stat-value">{stats.total_schemes || '—'}</span>
            <span className="stat-label">Schemes</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">10</span>
            <span className="stat-label">Languages</span>
          </div>
          {lastUpdated && (
            <div className="stat-card">
              <span className="stat-value stat-date">{lastUpdated}</span>
              <span className="stat-label">Last Updated</span>
            </div>
          )}
        </div>
      </section>

      <section className="benefits-section">
        <h2 className="section-title">Why SakhiSetu?</h2>
        <p className="section-desc">
          We bring government schemes to your fingertips—simplified, searchable, and always current.
        </p>
        <div className="benefits-grid">
          {BENEFITS.map((b, i) => (
            <article key={i} className="benefit-card">
              <span className="benefit-icon">{b.icon}</span>
              <h3>{b.title}</h3>
              <p>{b.desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="cta-section">
        <h2>Ready to Find Your Schemes?</h2>
        <p>Start by browsing schemes or check your eligibility in seconds.</p>
        <div className="cta-actions">
          <Link to="/schemes" className="btn btn-primary">Browse Schemes</Link>
          <Link to="/eligibility" className="btn btn-secondary">Check Eligibility</Link>
          <Link to="/chat" className="btn btn-outline">Ask AI</Link>
        </div>
      </section>
    </div>
  )
}
