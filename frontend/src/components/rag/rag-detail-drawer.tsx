"use client";

import React from 'react';
import { RagAnalysis } from '@/lib/types';
import { X, Database, BrainCircuit, Activity, FileText, ChevronRight, AlertCircle, GitMerge } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';

interface RagDetailDrawerProps {
  anomalyId: string | null;
  onClose: () => void;
}

export function RagDetailDrawer({ anomalyId, onClose }: RagDetailDrawerProps) {
  const [analysis, setAnalysis] = React.useState<RagAnalysis | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!anomalyId) {
      setAnalysis(null);
      setError(null);
      return;
    }

    const fetchDetail = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`/api/rag/${anomalyId}`);
        const data = await res.json();
        
        if (!res.ok) {
          setError(data.error || "Failed to load analysis details");
        } else {
          setAnalysis(data.data);
        }
      } catch (err) {
        setError("Network error fetching analysis details");
      } finally {
        setLoading(false);
      }
    };

    fetchDetail();
  }, [anomalyId]);

  if (!anomalyId) return null;

  return (
    <>
      <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 transition-all" onClick={onClose} />
      
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-2xl bg-surface border-l border-border shadow-2xl overflow-y-auto transform transition-transform duration-300 ease-in-out flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-border sticky top-0 bg-surface z-10">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-md bg-purple-500/10 text-purple-400">
              <BrainCircuit className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary flex items-center gap-2">
                RAG Investigation
                <Badge variant="outline" className="text-[10px] bg-surface-elevated text-secondary uppercase tracking-widest border-border">
                  Historical
                </Badge>
              </h2>
              <div className="text-sm font-mono text-secondary mt-0.5">{anomalyId}</div>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-secondary hover:text-primary hover:bg-surface-elevated rounded-md transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="p-12 flex items-center justify-center text-secondary">
             <div className="animate-pulse flex items-center gap-2">
               <div className="w-2 h-2 rounded-full bg-current"></div>
               <div className="w-2 h-2 rounded-full bg-current animation-delay-200"></div>
               <div className="w-2 h-2 rounded-full bg-current animation-delay-400"></div>
             </div>
          </div>
        ) : error ? (
           <div className="p-12 flex flex-col items-center justify-center text-center">
              <AlertCircle className="w-8 h-8 text-status-error mb-4 opacity-50" />
              <div className="text-sm text-primary mb-1">Analysis Unavailable</div>
              <div className="text-xs text-secondary">{error}</div>
           </div>
        ) : analysis ? (
          <div className="p-6">
            
            {/* Visual Stepper Container */}
            <div className="relative border-l-2 border-border/50 ml-4 space-y-10 pb-8">
              
              {/* STEP 1: ANOMALY CONTEXT */}
              <div className="relative pl-6">
                <div className="absolute -left-[13px] top-1 bg-surface border-2 border-brand text-brand rounded-full p-1">
                  <Activity className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">01 — Anomaly Context</h3>
                
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                    <div className="text-xs font-medium text-secondary mb-1">Dataset</div>
                    <div className="text-sm font-medium text-primary">{analysis.dataset}</div>
                  </div>
                  <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                    <div className="text-xs font-medium text-secondary mb-1">Anomaly Type</div>
                    <div className="text-sm font-medium text-primary">{analysis.anomaly_type?.replace(/_/g, ' ')}</div>
                  </div>
                </div>
              </div>

              {/* STEP 2: EVIDENCE */}
              <div className="relative pl-6">
                <div className="absolute -left-[13px] top-1 bg-surface border-2 border-status-info text-status-info rounded-full p-1">
                  <Database className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">02 — Retrieved Evidence</h3>
                
                {analysis.sources && analysis.sources !== "None" ? (
                  <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                    <div className="text-sm text-primary font-mono whitespace-pre-wrap">{analysis.sources}</div>
                    <div className="mt-3 text-xs text-secondary border-t border-border pt-2">
                       Retrieval Method: {analysis.retrieval_method}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary p-4 border border-border border-dashed rounded-lg text-center">
                    No specific documents or evidence retrieved for this historical analysis.
                  </div>
                )}
              </div>

              {/* STEP 3: RAG ANALYSIS (ROOT CAUSE) */}
              <div className="relative pl-6">
                <div className="absolute -left-[13px] top-1 bg-surface border-2 border-purple-500 text-purple-500 rounded-full p-1">
                  <BrainCircuit className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-1">03 — Root Cause Analysis</h3>
                <div className="text-[10px] text-purple-400 font-mono uppercase mb-3 flex items-center gap-1 tracking-wider">
                  <GitMerge className="w-3 h-3" /> Historical RAG Response
                </div>
                
                <div className="bg-surface-elevated p-5 rounded-lg border border-border relative overflow-hidden">
                  <div className="absolute top-0 left-0 w-1 h-full bg-purple-500/50"></div>
                  <div className="text-sm text-primary leading-relaxed whitespace-pre-wrap">
                    {analysis.grounded_explanation}
                  </div>
                </div>
              </div>

              {/* STEP 4: RECOMMENDED ACTION */}
              <div className="relative pl-6">
                <div className="absolute -left-[13px] top-1 bg-surface border-2 border-status-success text-status-success rounded-full p-1">
                  <FileText className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">04 — Recommended Action</h3>
                
                {analysis.recommended_action && analysis.recommended_action !== "None" ? (
                  <div className="bg-surface-elevated p-4 rounded-lg border border-status-success/30 bg-status-success/5">
                    <div className="text-sm text-primary font-medium">{analysis.recommended_action}</div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary italic">No recommendation was recorded.</div>
                )}
              </div>

              {/* STEP 5: OPERATOR DECISION */}
              <div className="relative pl-6">
                <div className="absolute -left-[13px] top-1 bg-surface border-2 border-border text-secondary rounded-full p-1">
                  <ChevronRight className="w-3.5 h-3.5" />
                </div>
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">05 — Operator Decision</h3>
                
                <div className="bg-background border border-border border-dashed rounded-lg p-5 text-center opacity-70">
                   <div className="text-sm font-medium text-secondary mb-1">Persistence Not Configured</div>
                   <div className="text-xs text-secondary/70">Operator decision tracking is disabled in this environment.</div>
                </div>
              </div>

            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
