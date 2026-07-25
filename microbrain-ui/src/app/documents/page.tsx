'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { documentAPI, folderAPI } from '@/services/api';
import { Document, Folder } from '@/types';
import { Upload, FileText, Trash2, Clock, CheckCircle, XCircle, Loader2, Settings, FolderPlus } from 'lucide-react';

const CHUNKING_STRATEGIES = [
  { value: 'fixed', label: 'Fixed Size', description: 'Fixed chunk size with overlap' },
  { value: 'semantic', label: 'Semantic', description: 'Content-based chunking' },
  { value: 'section', label: 'Section-based', description: 'Document structure aware' },
  { value: 'recursive', label: 'Recursive', description: 'Hierarchical chunking' },
];

const EMBEDDING_MODELS = [
  { value: 'BAAI/bge-small-en-v1.5', label: 'BGE Small (384 dim)' },
  { value: 'BAAI/bge-base-en-v1.5', label: 'BGE Base (768 dim)' },
  { value: 'BAAI/bge-large-en-v1.5', label: 'BGE Large (1024 dim)' },
];

const VECTOR_STORES = [
  { value: 'chroma', label: 'ChromaDB' },
  { value: 'faiss', label: 'FAISS' },
  { value: 'qdrant', label: 'Qdrant' },
];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [selectedFolder, setSelectedFolder] = useState<string>('');
  const [showNewFolder, setShowNewFolder] = useState(false);
  const [newFolderName, setNewFolderName] = useState('');
  
  // Processing configuration
  const [chunkingStrategy, setChunkingStrategy] = useState('fixed');
  const [embeddingModel, setEmbeddingModel] = useState('BAAI/bge-small-en-v1.5');
  const [vectorStore, setVectorStore] = useState('chroma');

  const loadDocuments = async () => {
    try {
      const response = await documentAPI.list();
      setDocuments(response.data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFolders = async () => {
    try {
      const response = await folderAPI.list();
      setFolders(response.data);
    } catch (error) {
      console.error('Failed to load folders:', error);
    }
  };

  useEffect(() => {
    loadDocuments();
    loadFolders();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    setUploading(true);
    try {
      await documentAPI.upload(
        file, 
        title || file.name, 
        selectedFolder || undefined,
        chunkingStrategy,
        embeddingModel,
        vectorStore
      );
      setFile(null);
      setTitle('');
      setSelectedFolder('');
      loadDocuments();
    } catch (error) {
      console.error('Failed to upload document:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleCreateFolder = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFolderName.trim()) return;

    try {
      await folderAPI.create({ name: newFolderName });
      setNewFolderName('');
      setShowNewFolder(false);
      loadFolders();
    } catch (error) {
      console.error('Failed to create folder:', error);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    
    try {
      await documentAPI.delete(id);
      loadDocuments();
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  const getStatusIcon = (status: Document['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'processing':
        return <Clock className="h-4 w-4 text-yellow-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  const getStatusBadge = (status: Document['status']) => {
    const variants: Record<Document['status'], 'default' | 'secondary' | 'destructive'> = {
      completed: 'default',
      processing: 'secondary',
      failed: 'destructive',
      uploading: 'secondary'
    };
    return <Badge variant={variants[status]}>{status}</Badge>;
  };

  if (loading) {
    return (
      <MainLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <div className="flex gap-6 h-[calc(100vh-8rem)]">
        {/* Configuration Sidebar */}
        <div className="w-80 flex-shrink-0 space-y-4">
          <Card className="h-full">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Processing Config
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Chunking Strategy */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Chunking Strategy</Label>
                <Select value={chunkingStrategy} onValueChange={(value) => setChunkingStrategy(value || 'fixed')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CHUNKING_STRATEGIES.map((strategy) => (
                      <SelectItem key={strategy.value} value={strategy.value}>
                        <div className="flex flex-col">
                          <span>{strategy.label}</span>
                          <span className="text-xs text-muted-foreground">{strategy.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Embedding Model */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Embedding Model</Label>
                <Select value={embeddingModel} onValueChange={(value) => setEmbeddingModel(value || 'BAAI/bge-small-en-v1.5')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {EMBEDDING_MODELS.map((model) => (
                      <SelectItem key={model.value} value={model.value}>
                        {model.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Vector Store */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Vector Store</Label>
                <Select value={vectorStore} onValueChange={(value) => setVectorStore(value || 'chroma')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {VECTOR_STORES.map((store) => (
                      <SelectItem key={store.value} value={store.value}>
                        {store.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-lg text-sm">
                <p className="font-medium mb-2">Current Configuration</p>
                <div className="space-y-1 text-muted-foreground">
                  <p>Chunking: {chunkingStrategy}</p>
                  <p>Embedding: {embeddingModel}</p>
                  <p>Store: {vectorStore}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 space-y-4 overflow-auto">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
            <p className="text-muted-foreground mt-1">
              Manage and upload your documents for RAG processing
            </p>
          </div>

          {/* Upload Card */}
          <Card>
            <CardHeader>
              <CardTitle>Upload Document</CardTitle>
              <CardDescription>
                Upload PDF, DOCX, TXT, or other supported files
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleUpload} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="file">File</Label>
                  <Input
                    id="file"
                    type="file"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    accept=".pdf,.docx,.txt,.md,.html,.pptx"
                    disabled={uploading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="title">Title (optional)</Label>
                  <Input
                    id="title"
                    type="text"
                    placeholder="Document title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    disabled={uploading}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="folder">Folder (optional)</Label>
                  <div className="flex gap-2">
                    <Select value={selectedFolder} onValueChange={(value) => setSelectedFolder(value || '')}>
                      <SelectTrigger className="flex-1">
                        <SelectValue placeholder="Select folder" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="">No folder</SelectItem>
                        {folders.map((folder) => (
                          <SelectItem key={folder.id} value={folder.id}>
                            {folder.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <Button
                      type="button"
                      variant="outline"
                      size="icon"
                      onClick={() => setShowNewFolder(!showNewFolder)}
                    >
                      <FolderPlus className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {showNewFolder && (
                  <div className="space-y-2 p-4 bg-slate-50 dark:bg-slate-800 rounded-lg">
                    <Label htmlFor="newFolder">New Folder Name</Label>
                    <div className="flex gap-2">
                      <Input
                        id="newFolder"
                        type="text"
                        placeholder="Folder name"
                        value={newFolderName}
                        onChange={(e) => setNewFolderName(e.target.value)}
                      />
                      <Button type="button" onClick={handleCreateFolder}>
                        Create
                      </Button>
                    </div>
                  </div>
                )}
                <Button type="submit" disabled={!file || uploading}>
                  {uploading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Uploading...
                    </>
                  ) : (
                    <>
                      <Upload className="mr-2 h-4 w-4" />
                      Upload
                    </>
                  )}
                </Button>
              </form>
            </CardContent>
          </Card>

          {/* Documents List */}
          <Card className="flex-1">
            <CardHeader>
              <CardTitle>Your Documents</CardTitle>
              <CardDescription>
                {documents.length} document{documents.length !== 1 ? 's' : ''} uploaded
              </CardDescription>
            </CardHeader>
            <CardContent>
              {documents.length === 0 ? (
                <div className="text-center py-12">
                  <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No documents uploaded yet</p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-3">
                    {documents.map((doc) => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-4 border rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                      >
                        <div className="flex items-center gap-4 flex-1 min-w-0">
                          <div className="flex-shrink-0">
                            {getStatusIcon(doc.status)}
                          </div>
                          <div className="flex-1 min-w-0">
                            <h3 className="font-medium truncate">{doc.title}</h3>
                            <p className="text-sm text-muted-foreground truncate">
                              {doc.filename}
                            </p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                              {getStatusBadge(doc.status)}
                              {doc.chunk_count > 0 && (
                                <Badge variant="outline">{doc.chunk_count} chunks</Badge>
                              )}
                              {doc.chunking_strategy && (
                                <Badge variant="outline" className="text-xs">{doc.chunking_strategy}</Badge>
                              )}
                              {doc.embedding_model && (
                                <Badge variant="outline" className="text-xs">{doc.embedding_model.split('/')[1]}</Badge>
                              )}
                            </div>
                          </div>
                        </div>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(doc.id)}
                          className="flex-shrink-0"
                          title="Delete document"
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
