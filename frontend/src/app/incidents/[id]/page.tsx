'use client';

import { useAlerts } from '@/lib/hooks';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { SLABadge } from '@/components/ui/sla-badge';
import { LoadingState, ErrorState } from '@/components/ui/states';
import { formatDistanceToNow } from 'date-fns';
import { ArrowLeft, Clock, GitCommit, ShieldAlert, Zap, FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function IncidentDetail({ params }: { params: { id: string } }) {
  const { data: alerts, isLoading, error } = useAlerts();

  if (isLoading) return <LoadingState message="Loading Incident Details..." />;
  if (error) return <ErrorState message="Failed to load incident details." />;

  // Find the exact alert or just pick the first one for prototype purposes
  const alert = alerts?.find(a => a.incident_id.includes(params.id)) || alerts?.[0];

  if (!alert) return <ErrorState message="Incident not found." />;

  return (
    <div className="flex flex-col gap-6">
      {/* Header */}
      <div className="flex flex-col gap-4">
        <Link href="/incidents" className="flex items-center text-sm font-medium text-interactive hover:underline w-fit">
          <ArrowLeft className="mr-1 h-4 w-4" />
          Back to Incidents
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <StatusBadge severity={alert.severity} />
              <span className="font-mono text-sm text-secondary">INC-{alert.incident_id.split('-')[0]}</span>
            </div>
            <h1 className="text-2xl font-semibold tracking-tight text-primary">{alert.summary}</h1>
            <div className="flex flex-wrap items-center gap-4 mt-3 text-sm text-secondary">
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Detected: {alert.detected_at ? formatDistanceToNow(new Date(alert.detected_at), { addSuffix: true }) : 'Unknown time'}
              </div>
              <div className="flex items-center gap-1">
                <GitCommit className="h-4 w-4" />
                Run ID: <span className="font-mono">{alert.run_id ? alert.run_id.split('-')[0] : 'N/A'}</span>
              </div>
              {alert.sla_status && (
                <div className="flex items-center gap-1">
                  <ShieldAlert className="h-4 w-4" />
                  SLA: <SLABadge status={alert.sla_status} />
                </div>
              )}
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline">Acknowledge</Button>
            <Button>Resolve Incident</Button>
          </div>
        </div>
      </div>
      
      {/* Main Content Areas */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* RCA Panel */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          
          <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border-default bg-muted flex items-center gap-2">
              <Zap className="h-5 w-5 text-interactive" />
              <h3 className="font-semibold text-primary">Automated Root Cause Analysis</h3>
            </div>
            <div className="p-6">
              <p className="text-sm text-primary mb-6 leading-relaxed">
                Based on correlation of pipeline telemetry and data quality events over the past hour, the AI engine has formulated the following root cause hypotheses.
              </p>
              
              <div className="space-y-4">
                {/* Simulated RCA Finding 1 */}
                <div className="p-4 border border-status-critical/30 bg-status-critical/5 rounded-md">
                  <div className="flex items-start gap-3">
                    <Badge variant="critical">Primary</Badge>
                    <div>
                      <h4 className="text-sm font-medium text-primary">Upstream schema change dropped critical field</h4>
                      <p className="text-sm text-secondary mt-1">
                        The `provider_npi` field is missing from 100% of records in the current batch. This matches a known deployment pattern from the ingestion service at 14:00 UTC.
                      </p>
                      <div className="mt-3 flex gap-2">
                        <Button variant="outline" size="sm">View Evidence</Button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Simulated RCA Finding 2 */}
                <div className="p-4 border border-border-default rounded-md">
                  <div className="flex items-start gap-3">
                    <Badge variant="secondary">Contributing</Badge>
                    <div>
                      <h4 className="text-sm font-medium text-primary">Volume spike in historical claims</h4>
                      <p className="text-sm text-secondary mt-1">
                        We observed a 45% spike in historical claims processing for Hospital ID {alert.hospital_id || 'HOSP-1'}, causing delayed processing stages.
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border-default flex items-center gap-2">
              <FileText className="h-5 w-5 text-secondary" />
              <h3 className="font-semibold text-primary">Investigation Notes</h3>
            </div>
            <div className="p-4">
              <textarea 
                className="w-full bg-canvas border border-border-default rounded-md p-3 text-sm text-primary focus:outline-none focus:ring-2 focus:ring-border-focus min-h-[120px]" 
                placeholder="Add investigation notes, links to external systems, or remediation steps taken..."
              ></textarea>
              <div className="flex justify-end mt-3">
                <Button size="sm">Save Note</Button>
              </div>
            </div>
          </div>
        </div>

        {/* Sidebar Context */}
        <div className="flex flex-col gap-6">
          <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
            <div className="p-4 border-b border-border-default">
              <h3 className="font-semibold text-primary">Incident Context</h3>
            </div>
            <div className="p-4 space-y-4">
              <div>
                <span className="block text-xs font-medium text-secondary uppercase tracking-wider mb-1">Status</span>
                <span className="text-sm text-primary font-medium">{alert.status}</span>
              </div>
              <div>
                <span className="block text-xs font-medium text-secondary uppercase tracking-wider mb-1">Impacted Hospital</span>
                <span className="text-sm text-primary font-mono">{alert.hospital_id || 'MULTIPLE'}</span>
              </div>
              <div>
                <span className="block text-xs font-medium text-secondary uppercase tracking-wider mb-1">Pipeline Stage</span>
                <Badge variant="outline" className="font-mono mt-1">{alert.stage || 'UNKNOWN'}</Badge>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
