import React from 'react';
import { PipelineRun } from '@/lib/types';
import { StatusBadge } from '@/components/ui/status-badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EmptyState } from '@/components/ui/states';

interface ActiveRunsPanelProps {
  pipelines: PipelineRun[];
}

// Stage ordering to compute progression
const STAGES = ['INGEST', 'CLEAN', 'VALIDATE', 'DQ', 'TRANSFORM', 'ML', 'SLA', 'RAG', 'RCA', 'ALERT'];

export function ActiveRunsPanel({ pipelines }: ActiveRunsPanelProps) {
  if (pipelines.length === 0) {
    return <EmptyState title="No active pipeline runs" description="All pipelines have completed successfully." />;
  }

  const getProgression = (stage: string) => {
    const idx = STAGES.indexOf(stage);
    if (idx === -1) return stage;
    return `Stage ${idx + 1} of ${STAGES.length}: ${stage}`;
  };

  return (
    <div className="h-full overflow-auto">
      <Table>
        <TableHeader className="sticky top-0 bg-surface shadow-[0_1px_0_var(--color-border-default)]">
          <TableRow>
            <TableHead>Run ID</TableHead>
            <TableHead>Hospital</TableHead>
            <TableHead>Progression</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right">Elapsed</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {pipelines.map((run) => (
            <TableRow key={run.run_id} className="hover:bg-surface-hover cursor-pointer">
              <TableCell className="font-mono text-xs">{run.run_id.split('-')[0]}...</TableCell>
              <TableCell className="text-sm font-medium">{run.hospital_id}</TableCell>
              <TableCell>
                <div className="text-xs font-medium text-primary">{getProgression(run.current_stage)}</div>
              </TableCell>
              <TableCell>
                <StatusBadge severity={run.status === 'FAILED' ? 'CRITICAL' : run.status === 'WARNING' ? 'WARNING' : 'INFO'} label={run.status} />
              </TableCell>
              <TableCell className="text-right tabular-nums text-sm text-secondary">
                {run.duration_sec}s
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
