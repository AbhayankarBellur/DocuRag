'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { queryAPI, folderAPI } from '@/services/api';
import { Query, Folder } from '@/types';
import { Send, MessageSquare, Clock, Zap, FileText, Loader2, Settings, CheckCircle2, Sparkles, Folder as FolderIcon } from 'lucide-react';

const REASONING_LEVELS = [
  { value: 'basic', label: 'Basic', description: 'Quick, direct answers (temp: 0.3, tokens: 256)' },
  { value: 'intermediate', label: 'Intermediate', description: 'Balanced reasoning (temp: 0.5, tokens: 512)' },
  { value: 'advanced', label: 'Advanced', description: 'Detailed analysis (temp: 0.7, tokens: 1024)' },
  { value: 'expert', label: 'Expert', description: 'Deep analysis (temp: 0.9, tokens: 2048)' },
];

const PROMPT_TEMPLATES = [
  { value: 'factual_qa', label: 'Factual Q&A' },
  { value: 'analysis', label: 'Analysis' },
  { value: 'summary', label: 'Summary' },
  { value: 'comparison', label: 'Comparison' },
  { value: 'creative', label: 'Creative' },
  { value: 'code_explanation', label: 'Code Explanation' },
  { value: 'step_by_step', label: 'Step-by-Step' },
  { value: 'critical_thinking', label: 'Critical Thinking' },
];

const QUICK_EXAMPLES = [
  "What are the main features of this system?",
  "How does the authentication work?",
  "Explain the document processing pipeline",
  "What chunking strategies are available?",
  "How are embeddings generated?",
];

export default function QueriesPage() {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<Query[]>([]);
  const [folders, setFolders] = useState<Folder[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  
  // Configuration state
  const [reasoningLevel, setReasoningLevel] = useState('intermediate');
  const [promptTemplate, setPromptTemplate] = useState('factual_qa');
  const [nResults, setNResults] = useState([5]);
  const [showSources, setShowSources] = useState(true);
  const [selectedFolder, setSelectedFolder] = useState<string>('');

  const loadHistory = async () => {
    try {
      const response = await queryAPI.history();
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to load history:', error);
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
    loadHistory();
    loadFolders();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setSending(true);
    try {
      await queryAPI.create({ 
        question: query,
        reasoning_level: reasoningLevel as any,
        prompt_template: promptTemplate,
        n_results: nResults[0],
        folder_id: selectedFolder || undefined
      });
      setQuery('');
      loadHistory();
    } catch (error) {
      console.error('Failed to submit query:', error);
    } finally {
      setSending(false);
    }
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
                Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* System Status */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">System Status</Label>
                <div className="space-y-2">
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>Backend Connected</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>Vector Store Ready</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>Embedding Model Loaded</span>
                  </div>
                </div>
              </div>

              <Separator />

              {/* Reasoning Level */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Reasoning Level</Label>
                <Select value={reasoningLevel} onValueChange={(value) => setReasoningLevel(value || 'intermediate')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {REASONING_LEVELS.map((level) => (
                      <SelectItem key={level.value} value={level.value}>
                        <div className="flex flex-col">
                          <span>{level.label}</span>
                          <span className="text-xs text-muted-foreground">{level.description}</span>
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Prompt Template */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Prompt Template</Label>
                <Select value={promptTemplate} onValueChange={(value) => setPromptTemplate(value || 'factual_qa')}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROMPT_TEMPLATES.map((template) => (
                      <SelectItem key={template.value} value={template.value}>
                        {template.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Number of Results */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">
                  Number of Retrieved Documents: {nResults[0]}
                </Label>
                <Slider
                  value={nResults}
                  onValueChange={(value) => setNResults(Array.isArray(value) ? value : [value])}
                  min={1}
                  max={20}
                  step={1}
                  className="w-full"
                />
              </div>

              {/* Show Sources Toggle */}
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="showSources"
                  checked={showSources}
                  onChange={(e) => setShowSources(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="showSources" className="text-sm cursor-pointer">
                  Show source documents
                </Label>
              </div>

              {/* Folder Selection */}
              <div className="space-y-3">
                <Label className="text-sm font-medium flex items-center gap-2">
                  <FolderIcon className="h-4 w-4" />
                  Target Folder (Optional)
                </Label>
                <Select value={selectedFolder} onValueChange={(value) => setSelectedFolder(value || '')}>
                  <SelectTrigger>
                    <SelectValue placeholder="All folders" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">All folders</SelectItem>
                    {folders.map((folder) => (
                      <SelectItem key={folder.id} value={folder.id}>
                        {folder.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Separator />

              {/* Quick Examples */}
              <div className="space-y-3">
                <Label className="text-sm font-medium">Quick Examples</Label>
                <div className="space-y-2">
                  {QUICK_EXAMPLES.map((example, idx) => (
                    <Button
                      key={idx}
                      variant="outline"
                      size="sm"
                      className="w-full text-left justify-start text-xs h-auto py-2"
                      onClick={() => setQuery(example)}
                    >
                      {example}
                    </Button>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 space-y-4 overflow-auto">
          <div>
            <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-purple-500" />
              RAG System
            </h1>
            <p className="text-muted-foreground mt-1">
              Ask questions about your documents using advanced retrieval and generation
            </p>
          </div>

          {/* Query Input */}
          <Card>
            <CardHeader>
              <CardTitle>Ask Your Question</CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSubmit} className="space-y-4">
                <Textarea
                  placeholder="What would you like to know about your documents?"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={sending}
                  rows={4}
                  className="resize-none"
                />
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span>{query.length} characters</span>
                    <Badge variant="outline">{reasoningLevel}</Badge>
                  </div>
                  <Button type="submit" disabled={!query.trim() || sending} size="lg">
                    {sending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Get Answer
                      </>
                    )}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>

          {/* Query History */}
          <Card className="flex-1">
            <CardHeader>
              <CardTitle>Query History</CardTitle>
              <CardDescription>
                {history.length} quer{history.length !== 1 ? 'ies' : 'y'} submitted
              </CardDescription>
            </CardHeader>
            <CardContent>
              {history.length === 0 ? (
                <div className="text-center py-12">
                  <MessageSquare className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No queries yet. Ask your first question!</p>
                </div>
              ) : (
                <ScrollArea className="h-[400px]">
                  <div className="space-y-4">
                    {history.map((item) => (
                      <div key={item.id} className="border rounded-lg overflow-hidden">
                        <div className="p-4 bg-slate-50 dark:bg-slate-800">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1">
                              <p className="font-medium text-slate-900 dark:text-slate-50">
                                Your Question: {item.question}
                              </p>
                              <div className="flex items-center gap-2 mt-2 flex-wrap">
                                <Badge variant={item.status === 'completed' ? 'default' : 'secondary'}>
                                  {item.status}
                                </Badge>
                                {item.total_time && (
                                  <Badge variant="outline" className="flex items-center gap-1">
                                    <Clock className="h-3 w-3" />
                                    {item.total_time}ms
                                  </Badge>
                                )}
                                {item.prompt_template && (
                                  <Badge variant="outline">{item.prompt_template}</Badge>
                                )}
                              </div>
                            </div>
                            <p className="text-xs text-muted-foreground whitespace-nowrap">
                              {new Date(item.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>
                        
                        {item.answer && (
                          <>
                            <Separator />
                            <div className="p-4">
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <Zap className="h-4 w-4" />
                                Answer
                              </h4>
                              <p className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                                {item.answer}
                              </p>
                            </div>
                          </>
                        )}

                        {showSources && item.sources && item.sources.length > 0 && (
                          <>
                            <Separator />
                            <div className="p-4">
                              <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                                <FileText className="h-4 w-4" />
                                Documents Retrieved: {item.sources.length}
                              </h4>
                              <div className="space-y-2">
                                {item.sources.map((source, idx) => (
                                  <div
                                    key={idx}
                                    className="p-3 bg-slate-50 dark:bg-slate-800 rounded-md text-sm"
                                  >
                                    <p className="text-slate-700 dark:text-slate-300 line-clamp-3">
                                      {source.text}
                                    </p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </>
                        )}

                        {item.retrieval_time && item.generation_time && (
                          <>
                            <Separator />
                            <div className="p-4 bg-slate-50 dark:bg-slate-800">
                              <div className="flex items-center gap-4 text-xs text-muted-foreground">
                                <span>Retrieval: {item.retrieval_time}ms</span>
                                <span>Generation: {item.generation_time}ms</span>
                                {item.token_usage && <span>Tokens: {item.token_usage}</span>}
                              </div>
                            </div>
                          </>
                        )}
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
