'use client';

import { usePipelines, useAlerts } from '@/lib/hooks';
import { MetricCard } from '@/components/ui/metric-card';
import { StatusBadge } from '@/components/ui/status-badge';
import { SLABadge } from '@/components/ui/sla-badge';
import { Badge } from '@/components/ui/badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { VolumeChart } from '@/components/ui/volume-chart';
import { ShieldCheck, AlertTriangle, Activity, Database } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function OperationsCenter() {
  const { data: pipelines, isLoading: isLoadingPipelines, error: errorPipelines } = usePipelines();
  const { data: alerts, isLoading: isLoadingAlerts, error: errorAlerts } = useAlerts();

  if (isLoadingPipelines || isLoadingAlerts) {
    return <LoadingState message="Loading Operations Center..." />;
  }

  if (errorPipelines || errorAlerts) {
    return <ErrorState message="Failed to load telemetry or alerts. Check backend connections." />;
  }

  const activeIncidents = alerts?.filter(a => a.status !== 'RESOLVED') || [];
  const activePipelines = pipelines?.filter(p => p.status !== 'COMPLETED_WITH_VIOLATIONS' && p.status !== 'HEALTHY') || [];
  
  const systemStatus = activeIncidents.some(i => i.severity === 'CRITICAL') 
    ? { color: 'bg-status-critical', text: 'System Critical - Active Incidents' }
    : activeIncidents.some(i => i.severity === 'ERROR')
    ? { color: 'bg-status-error', text: 'System Degraded - Errors Detected' }
    : { color: 'bg-status-success', text: 'System Healthy' };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Operations Center</h1>
          <p className="text-sm text-secondary mt-1">Real-time system health and active incidents</p>
        </div>
      </div>
      
      {/* System Health Bar */}
      <div className="h-12 w-full bg-surface border border-border-default rounded-md flex items-center px-4 shadow-sm">
        <div className={`h-3 w-3 rounded-full ${systemStatus.color} animate-pulse mr-3`}></div>
        <span className="text-sm font-medium text-primary">{systemStatus.text}</span>
      </div>
      
      {/* KPI Strip */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard 
          title="Active Pipelines" 
          value={activePipelines.length} 
          icon={<Activity />} 
        />
        <MetricCard 
          title="Open Incidents" 
          value={activeIncidents.length} 
          trend={activeIncidents.length > 0 ? "up" : "neutral"}
          icon={<AlertTriangle />} 
        />
        <MetricCard 
          title="Records Processed (24h)" 
          value={pipelines ? pipelines.reduce((sum, p) => sum + (p.records_in || 0), 0).toLocaleString() : "0"} 
          icon={<Database />} 
        />
        <MetricCard 
          title="Data Quality Score" 
          value="99.8%" 
          trend="up" 
          trendValue="vs last week"
          icon={<ShieldCheck />} 
        />
      </div>

      {/* Live Visual Analytics */}
      <div className="h-72 bg-surface border border-border-default rounded-md shadow-sm p-4 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-medium tracking-tight text-primary">Live Pipeline Volume</h2>
          <Badge variant="outline" className="text-xs bg-muted text-secondary border-border-default font-mono">
            LIVE - 30s TICK
          </Badge>
        </div>
        <div className="flex-1 min-h-0">
          <VolumeChart data={pipelines || []} />
        </div>
      </div>
      
      {/* Main Content Areas */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Active Pipeline Runs */}
        <div className="lg:col-span-7 bg-surface border border-border-default rounded-md overflow-hidden shadow-sm flex flex-col h-[500px]">
          <div className="p-4 border-b border-border-default bg-surface flex justify-between items-center shrink-0">
            <h3 className="font-semibold text-primary">Active Pipeline Runs</h3>
            <Badge variant="secondary">{activePipelines.length} Active</Badge>
          </div>
          <div className="flex-1 overflow-auto">
            {activePipelines.length === 0 ? (
              <EmptyState title="No active pipelines" description="All pipelines have completed successfully." />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Run ID</TableHead>
                    <TableHead>Stage</TableHead>
                    <TableHead>Records</TableHead>
                    <TableHead>Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {activePipelines.map((run) => (
                    <TableRow key={run.run_id}>
                      <TableCell className="font-medium text-xs font-mono">{run.run_id.split('-')[0]}</TableCell>
                      <TableCell className="text-xs">{run.current_stage}</TableCell>
                      <TableCell className="text-xs">{run.records_in?.toLocaleString() || '-'}</TableCell>
                      <TableCell>
                         <StatusBadge 
                           severity={run.status === 'FAILED' ? 'CRITICAL' : run.status === 'WARNING' ? 'WARNING' : 'INFO'} 
                           label={run.status} 
                         />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </div>
        </div>

        {/* Critical Incidents */}
        <div className="lg:col-span-5 bg-surface border border-border-default rounded-md overflow-hidden shadow-sm flex flex-col h-[500px]">
          <div className="p-4 border-b border-border-default bg-surface flex justify-between items-center shrink-0">
            <h3 className="font-semibold text-primary">Active Incidents</h3>
            <Badge variant={activeIncidents.length > 0 ? "critical" : "secondary"}>
              {activeIncidents.length} Open
            </Badge>
          </div>
          <div className="flex-1 overflow-auto p-0">
            {activeIncidents.length === 0 ? (
              <EmptyState title="No active incidents" description="System is operating normally." />
            ) : (
              <div className="divide-y divide-border-default">
                {activeIncidents.map((incident) => (
                  <div key={incident.alert_id} className="p-4 hover:bg-surface-hover transition-colors">
                    <div className="flex items-start justify-between">
                      <div className="flex gap-2">
                        <StatusBadge severity={incident.severity} />
                        <h4 className="text-sm font-medium text-primary leading-tight">{incident.summary}</h4>
                      </div>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-secondary">
                      <span className="font-mono bg-muted px-1.5 py-0.5 rounded text-tertiary">
                        {incident.run_id ? incident.run_id.split('-')[0] : 'SYSTEM'}
                      </span>
                      <span>{incident.detected_at ? formatDistanceToNow(new Date(incident.detected_at), { addSuffix: true }) : 'Unknown time'}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
