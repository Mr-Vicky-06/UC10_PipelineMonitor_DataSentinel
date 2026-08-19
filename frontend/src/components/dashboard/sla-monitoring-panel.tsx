import React from 'react';
import { AlertEvent } from '@/lib/types';
import { SLABadge } from '@/components/ui/sla-badge';
import { StatusBadge } from '@/components/ui/status-badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/ui/states';

interface SlaMonitoringPanelProps {
  slaAlerts: AlertEvent[];
}

export function SlaMonitoringPanel({ slaAlerts }: SlaMonitoringPanelProps) {
  if (slaAlerts.length === 0) {
    return <EmptyState title="No SLA events" description="No SLAs are currently being monitored." />;
  }

  return (
    <div className="h-full overflow-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-surface shadow-[0_1px_0_var(--color-border-default)]">
          <TableRow>
            <TableHead>Run ID</TableHead>
            <TableHead>Stage</TableHead>
            <TableHead>ETA / Deadline</TableHead>
            <TableHead>Throughput</TableHead>
            <TableHead>Pipeline</TableHead>
            <TableHead>SLA Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {slaAlerts.map((alert) => (
            <TableRow key={alert.alert_id} className="hover:bg-surface-hover cursor-pointer">
              <TableCell className="font-mono text-xs">{alert.run_id ? alert.run_id.split('-')[0] + '...' : 'UNKNOWN'}</TableCell>
              <TableCell className="text-xs uppercase">{alert.stage || 'UNKNOWN'}</TableCell>
              <TableCell>
                <div className="flex flex-col gap-0.5 text-xs">
                  <div className="flex justify-between w-32">
                    <span className="text-secondary">ETA:</span>
                    <span className="font-mono font-medium">{alert.eta || 'UNAVAILABLE'}</span>
                  </div>
                  <div className="flex justify-between w-32">
                    <span className="text-secondary">Deadline:</span>
                    <span className="font-mono">{alert.deadline || 'UNAVAILABLE'}</span>
                  </div>
                </div>
              </TableCell>
              <TableCell className="text-xs text-secondary font-mono">
                UNAVAILABLE
              </TableCell>
              <TableCell>
                <StatusBadge severity={alert.severity === 'CRITICAL' ? 'CRITICAL' : 'INFO'} label={alert.status} />
              </TableCell>
              <TableCell>
                <SLABadge status={alert.sla_status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
