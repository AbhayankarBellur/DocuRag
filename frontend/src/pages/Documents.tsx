import { useEffect, useState } from 'react'
import { documentAPI } from '../services/api'
import { Upload, Trash2, FileText } from 'lucide-react'

export default function Documents() {
  const [documents, setDocuments] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const response = await documentAPI.list()
      setDocuments(response.data)
    } catch (error) {
      console.error('Failed to load documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    try {
      await documentAPI.upload(file, file.name)
      loadDocuments()
    } catch (error) {
      console.error('Failed to upload document:', error)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await documentAPI.delete(id)
      loadDocuments()
    } catch (error) {
      console.error('Failed to delete document:', error)
    }
  }

  if (loading) {
    return <div className="text-center py-12">Loading...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Documents</h1>
        <label className="btn btn-primary cursor-pointer">
          <Upload className="w-4 h-4 mr-2 inline" />
          Upload Document
          <input
            type="file"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      {documents.length === 0 ? (
        <div className="card text-center py-12">
          <FileText className="w-12 h-12 mx-auto text-gray-400 mb-4" />
          <p className="text-gray-500">No documents yet. Upload your first document!</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {documents.map((doc) => (
            <div key={doc.id} className="card flex justify-between items-center">
              <div className="flex items-center">
                <FileText className="w-5 h-5 mr-3 text-gray-400" />
                <div>
                  <p className="font-medium">{doc.title}</p>
                  <p className="text-sm text-gray-500">
                    {doc.document_type} • {doc.chunk_count} chunks
                  </p>
                </div>
              </div>
              <button
                onClick={() => handleDelete(doc.id)}
                className="text-red-600 hover:text-red-700"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
