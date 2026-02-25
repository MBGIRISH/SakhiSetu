import { useState, useRef, useEffect } from 'react'
import { api } from '../api'
import './Page.css'
import './Chat.css'

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

export default function Chat() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [lang, setLang] = useState('en')
  const [error, setError] = useState(null)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  useEffect(scrollToBottom, [messages])

  async function handleSubmit(e) {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMsg = input.trim()
    setInput('')
    setMessages((m) => [...m, { role: 'user', content: userMsg }])
    setLoading(true)
    setError(null)

    try {
      const data = await api.chat(userMsg, lang)
      setMessages((m) => [
        ...m,
        {
          role: 'assistant',
          content: data.answer,
          sources: data.sources,
        },
      ])
    } catch (e) {
      setError(e.message)
      setMessages((m) => [...m, { role: 'assistant', content: `Error: ${e.message}` }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h2>Ask AI</h2>
        <p>Ask questions about women government schemes. The AI will search and answer based on your query.</p>
        <div className="page-actions">
          <select value={lang} onChange={(e) => setLang(e.target.value)} className="select">
            {LANG_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="chat-container card">
        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-placeholder">
              <p>Ask something like:</p>
              <ul>
                <li>What schemes are available for pregnant women?</li>
                <li>What documents do I need for PMMVY?</li>
                <li>What is the eligibility for Beti Bachao Beti Padhao?</li>
              </ul>
            </div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`chat-message ${msg.role}`}>
              <div className="message-bubble">
                {msg.content}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="message-sources">
                    <small>Sources: {msg.sources.map((s) => s.name).join(', ')}</small>
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="chat-message assistant">
              <div className="message-bubble">
                <span className="typing">Thinking...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSubmit} className="chat-input-form">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about schemes..."
            disabled={loading}
            className="chat-input"
          />
          <button type="submit" disabled={loading || !input.trim()} className="btn btn-primary">
            Send
          </button>
        </form>
      </div>
    </div>
  )
}
