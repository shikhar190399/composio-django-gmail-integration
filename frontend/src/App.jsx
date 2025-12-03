import { useState, useEffect, useRef } from 'react'
import { api } from './api'
import './App.css'

function App() {
  const [emails, setEmails] = useState([])
  const [selectedEmail, setSelectedEmail] = useState(null)
  const [stats, setStats] = useState({ total: 0, unread: 0 })
  const [connectionStatus, setConnectionStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState(null)
  
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1)
  const [totalCount, setTotalCount] = useState(0)
  const [hasNext, setHasNext] = useState(false)
  const [hasPrevious, setHasPrevious] = useState(false)
  const pageSize = 20

  // Load initial data
  useEffect(() => {
    loadData()
  }, [])

  // Load emails when page changes
  useEffect(() => {
    loadEmails(currentPage)
  }, [currentPage])

  async function loadData() {
    setLoading(true)
    setError(null)
    try {
      const [emailsRes, statsRes, connStatus] = await Promise.all([
        api.getEmails(1),
        api.getStats(),
        api.getConnectionStatus(),
      ])
      setEmails(emailsRes.results || [])
      setTotalCount(emailsRes.count || 0)
      setHasNext(!!emailsRes.next)
      setHasPrevious(!!emailsRes.previous)
      setCurrentPage(1)
      setStats(statsRes)
      setConnectionStatus(connStatus)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function loadEmails(page) {
    try {
      const emailsRes = await api.getEmails(page)
      setEmails(emailsRes.results || [])
      setTotalCount(emailsRes.count || 0)
      setHasNext(!!emailsRes.next)
      setHasPrevious(!!emailsRes.previous)
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleConnect() {
    try {
      const result = await api.initiateConnection()
      window.open(result.redirect_url, '_blank', 'width=600,height=700')
      alert('Complete the Gmail authorization in the popup, then click "Complete Connection"')
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleCompleteConnection() {
    const accountId = prompt('Enter the connected_account_id from Composio:')
    if (!accountId) return
    
    try {
      await api.completeConnection('default-user', accountId)
      await loadData()
      alert('Connection completed! Trigger enabled.')
    } catch (err) {
      setError(err.message)
    }
  }

  async function handleSync() {
    setSyncing(true)
    try {
      const result = await api.syncEmails()
      alert(`Synced ${result.emails_fetched} emails (${result.emails_created} new)`)
      await loadData()
    } catch (err) {
      setError(err.message)
    } finally {
      setSyncing(false)
    }
  }

  async function handleEmailClick(email) {
    try {
      const fullEmail = await api.getEmail(email.id)
      setSelectedEmail(fullEmail)
      if (!email.is_read) {
        await api.markRead(email.id)
        setEmails(emails.map(e => 
          e.id === email.id ? { ...e, is_read: true } : e
        ))
        setStats(s => ({ ...s, unread: Math.max(0, s.unread - 1) }))
      }
    } catch (err) {
      setError(err.message)
    }
  }

  function handleNextPage() {
    if (hasNext) {
      setCurrentPage(p => p + 1)
      setSelectedEmail(null)
    }
  }

  function handlePreviousPage() {
    if (hasPrevious) {
      setCurrentPage(p => p - 1)
      setSelectedEmail(null)
    }
  }

  function formatDate(dateStr) {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now - date
    
    if (diff < 86400000) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
    if (diff < 604800000) {
      return date.toLocaleDateString([], { weekday: 'short' })
    }
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
  }

  function formatFullDate(dateStr) {
    const date = new Date(dateStr)
    return date.toLocaleDateString([], { 
      weekday: 'long', 
      year: 'numeric', 
      month: 'long', 
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  function extractName(sender) {
    if (!sender) return 'Unknown'
    const match = sender.match(/^([^<]+)/)
    return match ? match[1].trim() : sender
  }

  function extractEmail(sender) {
    if (!sender) return ''
    const match = sender.match(/<([^>]+)>/)
    return match ? match[1] : sender
  }

  // Clean up snippet - remove JSON artifacts and decode HTML entities
  function cleanSnippet(snippet) {
    if (!snippet) return ''
    
    // If it's a JSON-like object, extract the body
    if (typeof snippet === 'object') {
      return snippet.body || snippet.subject || ''
    }
    
    // If it looks like JSON string, try to parse
    if (snippet.startsWith('{') || snippet.startsWith("{'")) {
      try {
        const parsed = JSON.parse(snippet.replace(/'/g, '"'))
        return parsed.body || parsed.subject || snippet
      } catch {
        // Not valid JSON, continue
      }
    }
    
    // Decode HTML entities
    const txt = document.createElement('textarea')
    txt.innerHTML = snippet
    let decoded = txt.value
    
    // Remove excessive whitespace
    decoded = decoded.replace(/\s+/g, ' ').trim()
    
    return decoded.substring(0, 150)
  }

  // Get initials for avatar
  function getInitials(sender) {
    const name = extractName(sender)
    const parts = name.split(' ')
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase()
    }
    return name.substring(0, 2).toUpperCase()
  }

  // Get avatar color based on sender
  function getAvatarColor(sender) {
    const colors = [
      '#e74c3c', '#3498db', '#2ecc71', '#9b59b6', 
      '#f39c12', '#1abc9c', '#e91e63', '#00bcd4'
    ]
    let hash = 0
    const name = extractName(sender)
    for (let i = 0; i < name.length; i++) {
      hash = name.charCodeAt(i) + ((hash << 5) - hash)
    }
    return colors[Math.abs(hash) % colors.length]
  }

  const totalPages = Math.ceil(totalCount / pageSize)
  const startItem = (currentPage - 1) * pageSize + 1
  const endItem = Math.min(currentPage * pageSize, totalCount)

  if (loading) {
    return (
      <div className="app">
        <div className="loading-screen">
          <div className="spinner"></div>
          <p>Loading emails...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="logo">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect width="20" height="16" x="2" y="4" rx="2"/>
              <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
            </svg>
            <span>Email Access</span>
          </div>
          <div className="stats">
            <span className="stat">{stats.total} emails</span>
            {stats.unread > 0 && (
              <span className="stat unread">{stats.unread} unread</span>
            )}
          </div>
        </div>
        <div className="header-actions">
          {connectionStatus?.is_active ? (
            <span className="connection-badge connected">
              <span className="dot"></span>
              Connected
            </span>
          ) : (
            <>
              <button onClick={handleConnect} className="btn btn-primary">
                Connect Gmail
              </button>
              <button onClick={handleCompleteConnection} className="btn btn-secondary">
                Complete Connection
              </button>
            </>
          )}
          <button 
            onClick={handleSync} 
            disabled={syncing || !connectionStatus?.is_active}
            className="btn btn-secondary"
          >
            {syncing ? 'Syncing...' : 'Sync'}
          </button>
          <button onClick={loadData} className="btn btn-ghost">
            Refresh
          </button>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="error-banner">
          <span>{error}</span>
          <button onClick={() => setError(null)}>×</button>
        </div>
      )}

      {/* Main content */}
      <main className="main">
        {/* Email list */}
        <aside className="email-list">
          {emails.length === 0 ? (
            <div className="empty-state">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <rect width="20" height="16" x="2" y="4" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              <h3>No emails yet</h3>
              <p>Connect your Gmail account to start receiving emails</p>
            </div>
          ) : (
            <>
              {emails.map(email => (
                <div 
                  key={email.id}
                  className={`email-item ${!email.is_read ? 'unread' : ''} ${selectedEmail?.id === email.id ? 'selected' : ''}`}
                  onClick={() => handleEmailClick(email)}
                >
                  <div className="email-avatar" style={{ backgroundColor: getAvatarColor(email.sender) }}>
                    {getInitials(email.sender)}
                  </div>
                  <div className="email-content">
                    <div className="email-item-header">
                      <span className="email-sender">{extractName(email.sender)}</span>
                      <span className="email-date">{formatDate(email.received_at)}</span>
                    </div>
                    <div className="email-subject">{email.subject || '(No Subject)'}</div>
                    <div className="email-snippet">{cleanSnippet(email.snippet)}</div>
                  </div>
                  {!email.is_read && <div className="unread-dot"></div>}
                </div>
              ))}
              
              {/* Pagination Controls */}
              {totalCount > pageSize && (
                <div className="pagination">
                  <button 
                    className="pagination-btn"
                    onClick={handlePreviousPage}
                    disabled={!hasPrevious}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M15 18l-6-6 6-6"/>
                    </svg>
                    Previous
                  </button>
                  <span className="pagination-info">
                    {startItem}-{endItem} of {totalCount}
                  </span>
                  <button 
                    className="pagination-btn"
                    onClick={handleNextPage}
                    disabled={!hasNext}
                  >
                    Next
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M9 18l6-6-6-6"/>
                    </svg>
                  </button>
                </div>
              )}
            </>
          )}
        </aside>

        {/* Email detail */}
        <section className="email-detail">
          {selectedEmail ? (
            <div className="email-view">
              {/* Email Header */}
              <div className="email-view-header">
                <h1 className="email-view-subject">{selectedEmail.subject || '(No Subject)'}</h1>
                
                <div className="email-view-meta">
                  <div className="email-view-avatar" style={{ backgroundColor: getAvatarColor(selectedEmail.sender) }}>
                    {getInitials(selectedEmail.sender)}
                  </div>
                  <div className="email-view-sender-info">
                    <div className="email-view-sender-name">
                      {extractName(selectedEmail.sender)}
                    </div>
                    <div className="email-view-sender-email">
                      {extractEmail(selectedEmail.sender)}
                    </div>
                  </div>
                  <div className="email-view-date">
                    {formatFullDate(selectedEmail.received_at)}
                  </div>
                </div>

                {selectedEmail.recipient && (
                  <div className="email-view-to">
                    <span className="label-text">To:</span> {selectedEmail.recipient}
                  </div>
                )}

                {selectedEmail.labels && selectedEmail.labels.length > 0 && (
                  <div className="email-view-labels">
                    {selectedEmail.labels.map((label, i) => (
                      <span key={i} className="email-label">{label}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Email Body */}
              <div className="email-view-body">
                <EmailBody email={selectedEmail} />
              </div>
            </div>
          ) : (
            <div className="no-selection">
              <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1">
                <rect width="20" height="16" x="2" y="4" rx="2"/>
                <path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
              </svg>
              <p>Select an email to view</p>
            </div>
          )}
        </section>
      </main>
    </div>
  )
}

// Separate component for email body rendering
function EmailBody({ email }) {
  const [iframeHeight, setIframeHeight] = useState(400)
  
  // Create the full HTML document for the iframe
  const getHtmlDocument = (htmlContent) => {
    return `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <base target="_blank">
        <style>
          * { box-sizing: border-box; }
          html, body {
            margin: 0;
            padding: 16px;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333;
            background: #fff;
            word-wrap: break-word;
            overflow-wrap: break-word;
          }
          img { max-width: 100%; height: auto; }
          a { color: #1a73e8; }
          table { max-width: 100%; }
          pre, code {
            background: #f5f5f5;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 13px;
          }
          blockquote {
            border-left: 3px solid #ddd;
            margin: 1em 0;
            padding-left: 1em;
            color: #666;
          }
        </style>
      </head>
      <body>${htmlContent}</body>
      </html>
    `
  }

  const handleIframeLoad = (e) => {
    try {
      const iframe = e.target
      const body = iframe.contentDocument?.body
      if (body) {
        const height = Math.max(body.scrollHeight, body.offsetHeight, 300)
        setIframeHeight(height + 50)
      }
    } catch (err) {
      // Cross-origin issues, use default height
      setIframeHeight(500)
    }
  }

  // If we have HTML content, render in iframe using srcDoc
  if (email.body_html) {
    return (
      <iframe
        srcDoc={getHtmlDocument(email.body_html)}
        className="email-iframe"
        title="Email content"
        style={{ height: `${iframeHeight}px` }}
        onLoad={handleIframeLoad}
        sandbox="allow-same-origin allow-popups"
      />
    )
  }

  // Otherwise render plain text nicely
  if (email.body_text) {
    // Clean up the text
    const cleanText = email.body_text
      .replace(/\r\n/g, '\n')
      .replace(/\r/g, '\n')
    
    return (
      <div className="email-plain-text">
        {cleanText.split('\n').map((line, i) => (
          <div key={i} className="text-line">
            {line || '\u00A0'}
          </div>
        ))}
      </div>
    )
  }

  return <p className="no-content">No content available</p>
}

export default App
