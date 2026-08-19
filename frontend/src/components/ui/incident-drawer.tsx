import * as React from 'react';
import { AlertEvent } from '@/lib/types';
import { X, AlertCircle, Clock, Database, CheckCircle, ChevronRight, BrainCircuit } from 'lucide-react';
import { Badge } from './badge';
import { Card, CardHeader, CardTitle, CardContent } from './card';

interface EvidenceItem {
  type: string;
  title: string;
  value: string;
  description: string;
}

export interface IncidentDetail {
  incident_id: string;
  alert_id: string;
  severity: string;
  status: string;
  summary: string;
  alert_type: string;
  hospital_id: string;
  run_id: string;
  stage: string;
  detected_at: string;
  evidence: EvidenceItem[];
}

interface IncidentDrawerProps {
  incidentId: string | null;
  onClose: () => void;
}

export function IncidentDrawer({ incidentId, onClose }: IncidentDrawerProps) {
  const [incident, setIncident] = React.useState<IncidentDetail | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [rcaLoading, setRcaLoading] = React.useState(false);
  const [rcaError, setRcaError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!incidentId) {
      setIncident(null);
      setRcaError(null);
      return;
    }

    const fetchIncident = async () => {
      setLoading(true);
      try {
        const res = await fetch(`/api/alerts/${incidentId}`);
        if (res.ok) {
          const data = await res.json();
          setIncident(data);
        }
      } catch (err) {
        console.error("Failed to fetch incident", err);
      } finally {
        setLoading(false);
      }
    };

    fetchIncident();
  }, [incidentId]);

  if (!incidentId) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-background/80 backdrop-blur-sm z-40 transition-all"
        onClick={onClose}
      />
      
      {/* Drawer */}
      <div className="fixed inset-y-0 right-0 z-50 w-full max-w-xl bg-surface border-l border-border shadow-2xl overflow-y-auto transform transition-transform duration-300 ease-in-out flex flex-col">
        <div className="flex items-center justify-between p-6 border-b border-border sticky top-0 bg-surface z-10">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-md ${
              incident?.severity === 'CRITICAL' ? 'bg-status-critical/10 text-status-critical' :
              incident?.severity === 'ERROR' ? 'bg-status-error/10 text-status-error' :
              incident?.severity === 'WARNING' ? 'bg-status-warning/10 text-status-warning' :
              'bg-status-info/10 text-status-info'
            }`}>
              <AlertCircle className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-primary">{incident?.incident_id || 'Loading...'}</h2>
              <div className="flex items-center gap-2 text-sm text-secondary">
                <span>{incident?.alert_type || 'Unknown Type'}</span>
                <span>•</span>
                <span className="opacity-70">{incident ? new Date(incident.detected_at).toLocaleString() : ''}</span>
              </div>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 text-secondary hover:text-primary hover:bg-surface-elevated rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {loading ? (
          <div className="p-6 flex items-center justify-center text-secondary h-40">
            <div className="animate-pulse flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-current"></div>
              <div className="w-2 h-2 rounded-full bg-current animation-delay-200"></div>
              <div className="w-2 h-2 rounded-full bg-current animation-delay-400"></div>
            </div>
          </div>
        ) : incident ? (
          <div className="p-6 space-y-8 flex-1">
            
            {/* WHAT HAPPENED */}
            <div>
               <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">What Happened</h3>
               <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                  <div className="text-sm text-primary leading-relaxed">{incident.summary}</div>
               </div>
            </div>

            {/* EVIDENCE */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xs font-bold text-secondary uppercase tracking-wider flex items-center gap-2">
                  <Database className="w-4 h-4 text-brand" />
                  Deterministic Evidence Pack
                </h3>
                {incident.evidence && incident.evidence.length > 0 && (
                   <Badge variant="outline" className="text-[10px] bg-status-success/10 text-status-success border-status-success/20">
                     Evidence Coverage: {incident.evidence.length} items captured
                   </Badge>
                )}
              </div>
              
              {incident.evidence && incident.evidence.length > 0 ? (
                <div className="space-y-3">
                  {incident.evidence.map((ev, i) => (
                    <Card key={i} className="bg-background border-border shadow-none">
                      <CardHeader className="py-3 px-4 flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-xs font-medium text-primary tracking-wide">
                          {ev.type}
                        </CardTitle>
                        <Badge variant="outline" className="text-[10px] font-mono text-secondary">{ev.title}</Badge>
                      </CardHeader>
                      <CardContent className="px-4 pb-4">
                        <div className="font-mono text-sm text-primary mb-1 break-all">{ev.value}</div>
                        <div className="text-xs text-secondary">{ev.description}</div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-sm text-secondary p-4 border border-border border-dashed rounded-lg text-center">
                  No structured evidence captured for this incident.
                </div>
              )}
            </div>

            {/* IMPACT */}
            <div>
               <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-3">Impact</h3>
               <div className="grid grid-cols-2 gap-4">
                 <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                   <div className="text-xs font-medium text-secondary mb-1">Pipeline Status</div>
                   <div className="font-medium text-primary">{incident.status}</div>
                 </div>
                 <div className="bg-surface-elevated p-4 rounded-lg border border-border">
                   <div className="text-xs font-medium text-secondary mb-1">Affected Run</div>
                   <div className="font-medium text-primary font-mono text-sm">{incident.run_id}</div>
                 </div>
               </div>
            </div>

            {/* RAG / RCA Section */}
            <div>
              <h3 className="text-xs font-bold text-secondary uppercase tracking-wider mb-4 flex items-center gap-2">
                <BrainCircuit className="w-4 h-4 text-purple-400" />
                AI Root Cause Analysis
              </h3>
              
              <div className="bg-surface-elevated rounded-lg border border-border overflow-hidden">
                <div className="p-6 flex flex-col items-center justify-center text-center space-y-3 bg-background/50">
                  <div className="w-10 h-10 rounded-full bg-surface border border-border flex items-center justify-center text-secondary mb-2">
                    <BrainCircuit className="w-5 h-5 opacity-40" />
                  </div>
                  <div className="text-sm font-medium text-primary">RAG correlation unavailable</div>
                  <div className="text-xs text-secondary max-w-[280px]">
                    No authoritative relationship exists between this incident alert and backend anomalies. Deterministic evidence is available above for manual investigation.
                  </div>
                </div>
              </div>
            </div>

          </div>
        ) : (
          <div className="p-6 text-center text-secondary text-sm">
            Incident not found.
          </div>
        )}
      </div>
    </>
  );
}
