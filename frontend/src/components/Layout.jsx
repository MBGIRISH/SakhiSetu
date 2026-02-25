import { NavLink } from 'react-router-dom'
import './Layout.css'

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/schemes', label: 'Schemes' },
  { to: '/eligibility', label: 'Check Eligibility' },
  { to: '/chat', label: 'Ask AI' },
  { to: '/simplify', label: 'Simplify Text' },
]

export default function Layout({ children }) {
  return (
    <div className="layout">
      <header className="header">
        <div className="header-inner">
          <h1 className="logo">
            <span className="logo-icon">🌉</span>
            SakhiSetu
          </h1>
          <p className="tagline">Women Government Scheme Navigator</p>
          <nav className="nav">
            {navItems.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>
      <main className="main">
        {children}
      </main>
      <footer className="footer">
        <p>SakhiSetu — Empowering women with access to government schemes</p>
      </footer>
    </div>
  )
}
