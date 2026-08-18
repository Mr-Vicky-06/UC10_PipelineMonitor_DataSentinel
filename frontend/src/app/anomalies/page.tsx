'use client';

import { useAnomalies } from '@/lib/hooks';
import { StatusBadge } from '@/components/ui/status-badge';
import { Badge } from '@/components/ui/badge';
import { LoadingState, ErrorState, EmptyState } from '@/components/ui/states';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { formatDistanceToNow } from 'date-fns';
import { Search, Filter, LineChart } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function MLAnomalies() {
  const { data: anomalies, isLoading, error } = useAnomalies();

  if (isLoading) return <LoadingState message="Loading ML Anomalies..." />;
  if (error) return <ErrorState message="Failed to load anomalies data." />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">ML Anomalies</h1>
          <p className="text-sm text-secondary mt-1">Statistical and AI-driven anomaly detections</p>
        </div>
      </div>
      
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 bg-surface p-4 border border-border-default rounded-md">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-tertiary" />
          <input 
            type="text" 
            placeholder="Search by feature, domain, or model..." 
            className="w-full pl-9 pr-4 py-2 bg-canvas border border-border-default rounded-md text-sm text-primary focus:outline-none focus:ring-2 focus:ring-border-focus"
          />
        </div>
        <div className="flex gap-2 overflow-x-auto">
          <Button variant="outline" className="gap-2">
            <Filter className="h-4 w-4" />
            Domain: All
          </Button>
          <Button variant="outline">
            Severity: All
          </Button>
        </div>
      </div>

      {/* Main Table */}
      <div className="bg-surface border border-border-default rounded-md overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          {anomalies?.length === 0 ? (
            <EmptyState title="No anomalies detected" description="ML models report normal behavior across all domains." icon={LineChart} />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Domain / Feature</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Run / Batch</TableHead>
                  <TableHead className="text-right">Observed / Expected</TableHead>
                  <TableHead className="text-right">Score</TableHead>
                  <TableHead>Severity</TableHead>
                  <TableHead>Detected</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {anomalies?.map((anomaly, i) => (
                  <TableRow key={anomaly.anomaly_id || i} className="cursor-pointer group">
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium text-primary text-sm font-mono">{anomaly.domain || 'UNKNOWN'}</span>
                        <span className="text-xs text-secondary">{anomaly.feature || 'unknown_feature'}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant="secondary" className="font-mono">{anomaly.model || 'Unknown Model'}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-mono text-primary text-xs">{anomaly.run_id?.split('-')[0] || '-'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm">
                      <div className="flex flex-col items-end">
                        <span className="font-medium text-primary">{anomaly.observed?.toLocaleString() || '-'}</span>
                        <span className="text-xs text-tertiary">{anomaly.expected?.toLocaleString() || '-'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right tabular-nums text-sm font-mono">
                      {anomaly.anomaly_score?.toFixed(3) || '-'}
                    </TableCell>
                    <TableCell>
                      <StatusBadge severity={anomaly.severity || 'WARNING'} />
                    </TableCell>
                    <TableCell className="text-sm text-secondary">
                      {anomaly.detected_at ? formatDistanceToNow(new Date(anomaly.detected_at), { addSuffix: true }) : '-'}
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
