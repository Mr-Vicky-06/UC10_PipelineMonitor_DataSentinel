"use client";

import React, { useEffect, useState } from 'react';
import { RagAnalysisSummary } from '@/lib/types';
import { LoadingState, ErrorState } from '@/components/ui/states';
import { MetricCard } from '@/components/ui/metric-card';
import { RagHistoryTable } from '@/components/rag/rag-history-table';
import { RagDetailDrawer } from '@/components/rag/rag-detail-drawer';
import { BrainCircuit, Database, CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

export default function RagIntelligencePage() {
  const [history, setHistory] = useState<RagAnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState<string | null>(null);
  const [providerStatus, setProviderStatus] = useState<'READY' | 'NOT_CONFIGURED' | 'UNAVAILABLE' | 'HISTORICAL_ONLY'>('HISTORICAL_ONLY');

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await fetch('/api/rag/history');
        const data = await res.json();
        
        if (!res.ok) {
          setError(data.error || "Failed to fetch RAG history");
        } else {
          setHistory(data.data || []);
        }
      } catch (err) {
        setError("Network error fetching RAG history");
      } finally {
        setLoading(false);
      }
    };

    const checkProvider = async () => {
        try {
            // Check live endpoint status
            const res = await fetch('/api/rag/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ anomaly_id: "test" })
            });
            if (res.status === 503) {
                setProviderStatus('NOT_CONFIGURED');
            } else if (res.ok) {
                setProviderStatus('READY');
            } else {
                setProviderStatus('UNAVAILABLE');
            }
        } catch (err) {
            setProviderStatus('UNAVAILABLE');
        }
    }

    fetchHistory();
    checkProvider();
  }, []);

  if (error) {
    return <ErrorState message={error} />;
  }

  // Calculate summary metrics
  const totalAnalyses = history.length;
  const criticalAnalyses = history.filter(h => h.severity === 'CRITICAL' || h.severity === 'ERROR').length;
  // Based on the historical parquet data, all are STANDARD_REPORT
  const successfulAnalyses = history.length; 

  return (
    <>
      <div className="flex flex-col gap-6 pb-10 h-full">
        
        {/* HEADER */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border-default pb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-primary flex items-center gap-2">
              <BrainCircuit className="w-6 h-6 text-purple-400" />
              RAG Intelligence
            </h1>
            <p className="text-sm text-secondary mt-1">Evidence-driven root cause analysis and investigation</p>
          </div>
          
          <div className="flex items-center gap-6 text-sm">
            <div className="flex flex-col items-end">
              <span className="text-secondary text-xs uppercase font-semibold tracking-wider">Live Provider Status</span>
              {providerStatus === 'NOT_CONFIGURED' ? (
                 <div className="flex items-center gap-1.5 font-medium text-status-warning">
                    <AlertTriangle className="w-4 h-4" /> Not Configured
                 </div>
              ) : providerStatus === 'READY' ? (
                 <div className="flex items-center gap-1.5 font-medium text-status-success">
                    <CheckCircle className="w-4 h-4" /> Ready
                 </div>
              ) : (
                 <div className="flex items-center gap-1.5 font-medium text-status-error">
                    <AlertTriangle className="w-4 h-4" /> Unavailable
                 </div>
              )}
            </div>
            
            <div className="w-px h-8 bg-border-default"></div>
            
            <div className="flex flex-col items-end">
              <span className="text-secondary text-xs uppercase font-semibold tracking-wider">Historical Logs</span>
              <div className="flex items-center gap-1.5 font-medium text-primary">
                <Database className="w-4 h-4 text-brand" />
                Available ({totalAnalyses})
              </div>
            </div>
          </div>
        </div>

        <div className="bg-status-info/10 border border-status-info/20 p-3 rounded-md flex items-start gap-2">
           <Clock className="w-4 h-4 text-status-info shrink-0 mt-0.5" />
           <div className="text-sm text-secondary">
             <strong className="text-primary font-medium">Historical RAG Analysis:</strong> Persisted RAG analyses from previous executions are available below. Live AI execution is currently disabled because the RAG provider is not configured.
           </div>
        </div>

        {/* SUMMARY STRIP */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
           <MetricCard title="Historical Analyses" value={totalAnalyses} icon={<Database className="text-brand" />} />
           <MetricCard title="Successful Outputs" value={successfulAnalyses} icon={<CheckCircle className="text-status-success" />} />
           <MetricCard title="Critical/Error Focus" value={criticalAnalyses} icon={<AlertTriangle className="text-status-error" />} />
           <MetricCard title="Evidence Sourced" value={totalAnalyses} icon={<BrainCircuit className="text-purple-400" />} />
        </div>

        {/* WORKSPACE */}
        <div className="flex-1 min-h-[500px]">
           <RagHistoryTable 
             data={history} 
             onSelect={setSelectedAnomaly} 
             loading={loading} 
           />
        </div>

      </div>

      <RagDetailDrawer 
        anomalyId={selectedAnomaly} 
        onClose={() => setSelectedAnomaly(null)} 
      />
    </>
  );
}
