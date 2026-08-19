'use client';

import { useAlerts } from '@/lib/hooks';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { SLABadge } from '@/components/ui/sla-badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatDistanceToNow } from 'date-fns';
import { Search, Filter, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function IncidentCenter() {
  const { data: alerts, isLoading, error } = useAlerts();

  if (isLoading) return <LoadingState message="Loading Incidents..." />;
  if (error) return <ErrorState message="Failed to load incidents." />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Incident Center</h1>
          <p className="text-sm text-secondary mt-1">Manage and investigate system and data alerts</p>
        </div>
        <div className="flex gap-2">
          <Button>
            <ShieldAlert className="mr-2 h-4 w-4" />
            Declare Incident
          </Button>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 bg-surface p-4 border border-border-default rounded-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-tertiary" />
          <input 
            type="text" 
            placeholder="Search incidents by ID, run, or keyword..." 
            className="w-full pl-9 pr-4 py-2 bg-canvas border border-border-default rounded-md text-sm text-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Severity: All
          </Button>
          <Button variant="outline">
            Status: Open
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          {alerts?.length === 0 ? (
            <EmptyState title="No incidents found" description="System is operating normally." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Incident</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Summary</TableHead>
                  <TableHead>SLA</TableHead>
                  <TableHead>Detected</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts?.map((alert) => (
                  <TableRow key={alert.alert_id} className="cursor-pointer group">
                    <TableCell className="font-mono text-xs text-secondary">
                      {alert.incident_id.split('-')[0]}
                    </TableCell>
                    <TableCell>
                      <StatusBadge severity={alert.severity} />
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col max-w-md">
                        <span className="font-medium text-primary text-sm truncate">{alert.summary}</span>
                        <div className="flex gap-2 mt-1 items-center text-xs text-secondary">
                          <span className="font-mono bg-muted px-1 rounded">{alert.alert_type}</span>
                          {alert.run_id && <span>Run: <span className="font-mono">{alert.run_id.split('-')[0]}</span></span>}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {alert.sla_status && <SLABadge status={alert.sla_status} />}
                    </TableCell>
                    <TableCell className="text-sm text-secondary">
                      {alert.detected_at ? formatDistanceToNow(new Date(alert.detected_at), { addSuffix: true }) : 'Unknown time'}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button variant="outline" size="sm" className="opacity-0 group-hover:opacity-100 transition-opacity">
                        Investigate
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </div>
      </div>
    </div>
  );
}
