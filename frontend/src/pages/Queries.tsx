import { useEffect, useState } from 'react'
import { queryAPI } from '../services/api'
import { Send, MessageSquare } from 'lucide-react'

export default function Queries() {
  const [query, setQuery] = useState('')
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)

  useEffect(() => {
    loadHistory()
  }, [])

  const loadHistory = async () => {
    try {
      const response = await queryAPI.history()
      setHistory(response.data)
    } catch (error) {
      console.error('Failed to load history:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setSending(true)
    try {
      await queryAPI.create({ question: query })
      setQuery('')
      loadHistory()
    } catch (error) {
      console.error('Failed to submit query:', error)
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Queries</h1>

      <div className="card">
        <form onSubmit={handleSubmit} className="flex gap-4">
          <input
            type="text"
            className="input flex-1"
            placeholder="Ask a question about your documents..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={sending}
          />
          <button type="submit" className="btn btn-primary" disabled={sending}>
            <Send className="w-4 h-4 mr-2 inline" />
            {sending ? 'Sending...' : 'Ask'}
          </button>
        </form>
      </div>

      {history.length === 0 ? (
        <div className="card text-center py-12">
          <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500">No queries yet. Ask your first question!</p>
        </div>
      ) : (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">Query History</h2>
          {history.map((item) => (
            <div key={item.id} className="card">
              <p className="font-medium text-gray-900 mb-2">{item.question}</p>
              {item.answer && (
                <p className="text-gray-700 text-sm">{item.answer}</p>
              )}
              <div className="mt-2 text-xs text-gray-500">
                {new Date(item.created_at).toLocaleString()}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
