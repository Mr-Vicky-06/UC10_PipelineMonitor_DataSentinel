"use client";

import * as React from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { BrainCircuit, AlertCircle, ChevronRight, CheckCircle2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { AlertEvent } from '@/lib/types';

interface IncidentIntelligenceProps {
  onInvestigate: (incidentId: string) => void;
}

export function IncidentIntelligence({ onInvestigate }: IncidentIntelligenceProps) {
  const [incident, setIncident] = React.useState<AlertEvent | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const fetchIncidents = async () => {
      try {
        const res = await fetch('/api/alerts');
        if (res.ok) {
          const alerts: AlertEvent[] = await res.json();
          // Find the highest severity open incident
          const openAlerts = alerts.filter(a => a.status !== 'RESOLVED');
          if (openAlerts.length > 0) {
            // Sort by severity (CRITICAL > ERROR > WARNING > INFO)
            const severityRank = { 'CRITICAL': 4, 'ERROR': 3, 'WARNING': 2, 'INFO': 1, 'UNKNOWN': 0 };
            openAlerts.sort((a, b) => {
              const rankA = severityRank[a.severity as keyof typeof severityRank] || 0;
              const rankB = severityRank[b.severity as keyof typeof severityRank] || 0;
              return rankB - rankA;
            });
            setIncident(openAlerts[0]);
          }
        }
      } catch (err) {
        console.error("Failed to fetch incidents for intelligence panel", err);
      } finally {
        setLoading(false);
      }
    };

    fetchIncidents();
    const interval = setInterval(fetchIncidents, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  return (
    <Card className="flex flex-col h-full bg-surface-elevated border-border">
      <CardHeader className="pb-3 border-b border-border bg-surface flex flex-row items-center justify-between">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-purple-400" />
          <CardTitle className="text-sm font-medium tracking-tight">Incident Intelligence</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 flex flex-col justify-center">
        {loading ? (
          <div className="flex items-center justify-center p-6 text-secondary">
             <div className="animate-pulse flex items-center gap-2">
              <div className="w-1.5 h-1.5 rounded-full bg-current"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-current animation-delay-200"></div>
              <div className="w-1.5 h-1.5 rounded-full bg-current animation-delay-400"></div>
            </div>
          </div>
        ) : incident ? (
          <div className="p-5 flex flex-col h-full justify-between gap-4">
            <div>
              <div className="flex items-start justify-between mb-2">
                 <Badge variant={incident.severity === 'CRITICAL' ? 'critical' : incident.severity === 'ERROR' ? 'critical' : 'warning'}>
                    {incident.severity}
                 </Badge>
                 <span className="text-xs font-mono text-secondary">{incident.incident_id}</span>
              </div>
              <h4 className="text-sm font-semibold text-primary mb-1 mt-3">
                {incident.alert_type === 'DQ' ? 'Data Quality Violation' : 
                 incident.alert_type === 'ANOMALY' ? 'Data Anomaly Detected' : 
                 incident.alert_type === 'SLA' ? 'SLA Breach Risk' : 'Pipeline Execution Failure'}
              </h4>
              <p className="text-xs text-secondary line-clamp-2">
                {incident.summary}
              </p>
              
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
                <div className="bg-surface p-2 rounded border border-border">
                  <span className="block text-secondary mb-0.5">Pipeline Run</span>
                  <span className="font-mono text-primary truncate block">{incident.run_id !== 'UNKNOWN' ? incident.run_id : 'Multiple'}</span>
                </div>
                <div className="bg-surface p-2 rounded border border-border">
                  <span className="block text-secondary mb-0.5">Current Status</span>
                  <span className="text-primary font-medium">{incident.status}</span>
                </div>
              </div>

              <div className="mt-3 bg-status-info/10 border border-status-info/20 rounded p-2 flex items-start gap-2">
                 <AlertCircle className="w-3.5 h-3.5 text-status-info mt-0.5 shrink-0" />
                 <span className="text-xs text-secondary leading-snug">Deterministic evidence has been captured and awaits operator review to resolve the pipeline block.</span>
              </div>
            </div>

            <button 
              onClick={() => onInvestigate(incident.incident_id)}
              className="w-full flex items-center justify-center gap-2 py-2 px-4 bg-brand hover:bg-brand-hover text-brand-foreground text-xs font-medium rounded-md transition-colors mt-2 shadow-sm"
            >
              Investigate Incident
              <ChevronRight className="w-3 h-3" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center p-8 text-center h-full">
            <div className="w-10 h-10 rounded-full bg-status-success/10 flex items-center justify-center mb-3">
               <CheckCircle2 className="w-5 h-5 text-status-success" />
            </div>
            <p className="text-sm font-medium text-primary">System Healthy</p>
            <p className="text-xs text-secondary mt-1">No active incidents require investigation.</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
