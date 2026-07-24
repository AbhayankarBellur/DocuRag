import { useEffect, useState } from 'react'
import { documentAPI, queryAPI } from '../services/api'
import { FileText, MessageSquare, Clock } from 'lucide-react'

export default function Dashboard() {
  const [stats, setStats] = useState({
    documents: 0,
    queries: 0,
    recentDocuments: [],
    recentQueries: []
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      const [docsRes, queriesRes] = await Promise.all([
        documentAPI.list(0, 5),
        queryAPI.history(0, 5)
      ])
      setStats({
        documents: docsRes.data.length,
        queries: queriesRes.data.length,
        recentDocuments: docsRes.data,
        recentQueries: queriesRes.data
      })
    } catch (error) {
      console.error('Failed to load dashboard:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Documents</p>
              <p className="text-3xl font-bold text-gray-900">{stats.documents}</p>
            </div>
            <FileText className="w-12 h-12 text-primary-600" />
          </div>
        </div>

        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Total Queries</p>
              <p className="text-3xl font-bold text-gray-900">{stats.queries}</p>
            </div>
            <MessageSquare className="w-12 h-12 text-primary-600" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Recent Documents</h2>
          {stats.recentDocuments.length === 0 ? (
            <p className="text-gray-500">No documents yet</p>
          ) : (
            <ul className="space-y-3">
              {stats.recentDocuments.map((doc: any) => (
                <li key={doc.id} className="flex items-center text-sm">
                  <FileText className="w-4 h-4 mr-2 text-gray-400" />
                  <span className="truncate">{doc.title}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="card">
          <h2 className="text-lg font-semibold mb-4">Recent Queries</h2>
          {stats.recentQueries.length === 0 ? (
            <p className="text-gray-500">No queries yet</p>
          ) : (
            <ul className="space-y-3">
              {stats.recentQueries.map((query: any) => (
                <li key={query.id} className="flex items-center text-sm">
                  <MessageSquare className="w-4 h-4 mr-2 text-gray-400" />
                  <span className="truncate">{query.question}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  )
}
