'use client';

import { useDataQuality } from '@/lib/hooks';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatDistanceToNow } from 'date-fns';
import { Search, Filter, ShieldCheck, Download } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DataQuality() {
  const { data: dqResults, isLoading, error } = useDataQuality();

  if (isLoading) return <LoadingState message="Loading Data Quality Results..." />;
  if (error) return <ErrorState message="Failed to load Data Quality data." />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Data Quality Rules</h1>
          <p className="text-sm text-secondary mt-1">Deterministic rule evaluation and violation tracking</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Download className="mr-2 h-4 w-4" />
            Export Report
          </Button>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 bg-surface p-4 border border-border-default rounded-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-tertiary" />
          <input 
            type="text" 
            placeholder="Search by Rule ID, Category, or Run ID..." 
            className="w-full pl-9 pr-4 py-2 bg-canvas border border-border-default rounded-md text-sm text-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Dimension: All
          </Button>
          <Button variant="outline">
            Severity: Critical
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          {dqResults?.length === 0 ? (
            <EmptyState title="No DQ violations found" description="All data passed deterministic checks." icon={ShieldCheck} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Rule ID / Dimension</TableHead>
                  <TableHead>Run / Batch</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead className="text-right">Violations</TableHead>
                  <TableHead className="text-right">Rate</TableHead>
                  <TableHead>Detected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {dqResults?.map((violation, i) => (
                  <TableRow key={violation.event_id || i} className="cursor-pointer group">
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-primary text-sm font-mono">{violation.rule_id || 'UNKNOWN_RULE'}</span>
                        <span className="text-xs text-secondary">{violation.dimension || 'Completeness'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-mono text-primary text-xs">{violation.batch_id}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge severity={violation.severity || 'WARNING'} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm font-medium">
                      {violation.violation_count?.toLocaleString() || '0'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm text-secondary">
                      {violation.violation_rate ? `${(violation.violation_rate * 100).toFixed(2)}%` : '-'}
                    </TableCell>
                    <TableCell className="text-sm text-secondary">
                      {violation.timestamp ? formatDistanceToNow(new Date(violation.timestamp), { addSuffix: true }) : '-'}
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
