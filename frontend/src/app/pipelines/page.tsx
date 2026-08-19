'use client';

import { usePipelines } from '@/lib/hooks';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatDistanceToNow } from 'date-fns';
import { Search, Filter } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function PipelineRuns() {
  const { data: pipelines, isLoading, error } = usePipelines();

  if (isLoading) return <LoadingState message="Loading Pipeline Runs..." />;
  if (error) return <ErrorState message="Failed to load pipeline runs." />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Pipeline Runs</h1>
          <p className="text-sm text-secondary mt-1">Detailed history and status of all ingestion jobs</p>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 bg-surface p-4 border border-border-default rounded-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-tertiary" />
          <input 
            type="text" 
            placeholder="Search by Run ID, Hospital ID, or Batch ID..." 
            className="w-full pl-9 pr-4 py-2 bg-canvas border border-border-default rounded-md text-sm text-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
          />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Status: All
          </Button>
          <Button variant="outline">
            Stage: All
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          {pipelines?.length === 0 ? (
            <EmptyState title="No pipeline runs found" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Run ID</TableHead>
                  <TableHead>Hospital / Batch</TableHead>
                  <TableHead>Stage</TableHead>
                  <TableHead className="text-right">Records In</TableHead>
                  <TableHead className="text-right">Duration</TableHead>
                  <TableHead>Updated</TableHead>
                  <TableHead>Status</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pipelines?.map((run) => (
                  <TableRow key={run.run_id} className="cursor-pointer">
                    <TableCell className="font-mono text-xs">{run.run_id.split('-')[0]}</TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-primary text-sm">{run.hospital_id}</span>
                        <span className="text-xs text-secondary">{run.batch_id}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-mono">{run.current_stage}</Badge>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      {run.records_in?.toLocaleString() || '-'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-secondary">
                      {run.duration_sec ? `${run.duration_sec.toFixed(1)}s` : '-'}
                    </TableCell>
                    <TableCell className="text-sm text-secondary">
                      {run.updated_at ? formatDistanceToNow(new Date(run.updated_at), { addSuffix: true }) : '-'}
                    </TableCell>
                    <TableCell>
                       <StatusBadge 
                         severity={run.status === 'FAILED' ? 'CRITICAL' : run.status === 'WARNING' ? 'WARNING' : run.status === 'COMPLETED_WITH_VIOLATIONS' ? 'WARNING' : 'INFO'} 
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
    </div>
  );
}
