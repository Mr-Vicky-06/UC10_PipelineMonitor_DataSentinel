import React from 'react';
import { AlertEvent } from '@/lib/types';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/states';
import { formatDistanceToNow } from 'date-fns';
import { ChevronRight } from 'lucide-react';
import Link from 'next/link';

interface IncidentPanelProps {
  activeIncidents: AlertEvent[];
}

export function IncidentPanel({ activeIncidents }: IncidentPanelProps) {
  if (activeIncidents.length === 0) {
    return <EmptyState title="No active incidents" description="System is operating normally." />;
  }

  // Sort by severity
  const severityWeight: Record<string, number> = {
    'CRITICAL': 4,
    'ERROR': 3,
    'WARNING': 2,
    'INFO': 1,
    'UNKNOWN': 0
  };

  const sortedIncidents = [...activeIncidents].sort((a, b) => {
    return severityWeight[b.severity] - severityWeight[a.severity];
  });

  return (
    <div className="h-full overflow-auto">
      <div className="divide-y divide-border-default">
        {sortedIncidents.map((incident) => (
          <Link href={`/incidents/${incident.incident_id}`} key={incident.incident_id} className="block p-4 hover:bg-surface-hover transition-colors group cursor-pointer">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0 pr-4">
                <div className="flex items-center gap-3 mb-1.5">
                  <StatusBadge severity={incident.severity} />
                  <span className="text-xs text-secondary tabular-nums whitespace-nowrap">
                    {incident.detected_at ? formatDistanceToNow(new Date(incident.detected_at), { addSuffix: true }) : 'Unknown'}
                  </span>
                  <Badge variant="outline" className="text-[10px] uppercase font-mono tracking-wider ml-auto">
                    {incident.status}
                  </Badge>
                </div>
                
                <h4 className="text-sm font-semibold text-primary leading-tight truncate group-hover:text-interactive transition-colors">
                  {incident.summary}
                </h4>
                
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-secondary">
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">Alert ID:</span>
                    <span className="font-mono">{incident.incident_id}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">Run:</span>
                    <span className="font-mono">{incident.run_id !== 'UNKNOWN' ? incident.run_id.split('-')[0] : 'SYSTEM'}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className="font-medium">Hospital:</span>
                    <span>{incident.hospital_id}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-tertiary">
                    <span className="font-medium">Occurrences:</span>
                    <span className="tabular-nums font-mono">{(incident as any).occurrence_count || 1}</span>
                  </div>
                </div>
              </div>
              
              <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full border border-border-default text-tertiary group-hover:bg-interactive group-hover:text-inverse group-hover:border-interactive transition-colors">
                <ChevronRight className="w-4 h-4" />
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
