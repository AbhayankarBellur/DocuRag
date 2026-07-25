'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout/main-layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { documentAPI, queryAPI } from '@/services/api';
import { Document, Query } from '@/types';
import { FileText, MessageSquare, Clock, Zap, TrendingUp, Loader2 } from 'lucide-react';

export default function DashboardPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [queries, setQueries] = useState<Query[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const [docsRes, queriesRes] = await Promise.all([
          documentAPI.list(),
          queryAPI.history(0, 10)
        ]);
        setDocuments(docsRes.data);
        setQueries(queriesRes.data);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const stats = [
    {
      title: 'Total Documents',
      value: documents.length,
      icon: FileText,
      description: 'Uploaded documents'
    },
    {
      title: 'Total Queries',
      value: queries.length,
      icon: MessageSquare,
      description: 'Questions asked'
    },
    {
      title: 'Completed Queries',
      value: queries.filter(q => q.status === 'completed').length,
      icon: Zap,
      description: 'Successfully processed'
    },
    {
      title: 'Avg Response Time',
      value: queries.length > 0 
        ? `${Math.round(queries.reduce((acc, q) => acc + (q.total_time || 0), 0) / queries.length)}ms`
        : '0ms',
      icon: Clock,
      description: 'Average processing time'
    }
  ];

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
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1">
            Overview of your RAG system activity
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">
                  {stat.description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {/* Recent Documents */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Documents</CardTitle>
              <CardDescription>
                Latest uploaded documents
              </CardDescription>
            </CardHeader>
            <CardContent>
              {documents.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No documents yet
                </p>
              ) : (
                <div className="space-y-3">
                  {documents.slice(0, 5).map((doc) => (
                    <div
                      key={doc.id}
                      className="flex items-center justify-between text-sm"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{doc.title}</p>
                        <p className="text-xs text-muted-foreground">
                          {doc.chunk_count} chunks • {doc.status}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Recent Queries */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Queries</CardTitle>
              <CardDescription>
                Latest questions and answers
              </CardDescription>
            </CardHeader>
            <CardContent>
              {queries.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No queries yet
                </p>
              ) : (
                <div className="space-y-3">
                  {queries.slice(0, 5).map((query) => (
                    <div
                      key={query.id}
                      className="space-y-1"
                    >
                      <p className="text-sm font-medium line-clamp-1">
                        {query.question}
                      </p>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{query.status}</span>
                        {query.total_time && (
                          <span>• {query.total_time}ms</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Activity Overview */}
        <Card>
          <CardHeader>
            <CardTitle>System Activity</CardTitle>
            <CardDescription>
              Your RAG system is ready to process documents and answer questions
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-muted-foreground">Backend Connected</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-muted-foreground">Vector Store Ready</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="h-2 w-2 rounded-full bg-green-500" />
                <span className="text-muted-foreground">Embedding Model Loaded</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
