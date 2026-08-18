'use client';

import { usePipelines, useAnomalies } from '@/lib/hooks';
import { VolumeChart } from '@/components/ui/volume-chart';
import { LoadingState } from '@/components/ui/states';
import { ExternalLink, BarChart3 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function Analytics() {
  const { data: pipelines, isLoading: isLoadingPipelines } = usePipelines();
  const { data: anomalies, isLoading: isLoadingAnomalies } = useAnomalies();

  if (isLoadingPipelines || isLoadingAnomalies) {
    return <LoadingState message="Loading advanced analytics..." />;
  }

  return (
    <div className="flex flex-col gap-6 h-full">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 shrink-0">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-primary">Advanced Analytics</h1>
          <p className="text-sm text-secondary mt-1">Live deep-dive visualizations across the pipeline</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" className="gap-2" onClick={() => window.open('http://localhost:3000', '_blank')}>
            <ExternalLink className="h-4 w-4" />
            Open Grafana Workspace
          </Button>
        </div>
      </div>
      
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="h-96 bg-surface border border-border-default rounded-md shadow-sm p-4 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium tracking-tight text-primary">Pipeline Throughput</h2>
            <Badge variant="outline" className="text-xs bg-muted text-secondary border-border-default font-mono">
              LIVE DATA
            </Badge>
          </div>
          <div className="flex-1 min-h-0">
            <VolumeChart data={pipelines || []} />
          </div>
        </div>
        
        <div className="h-96 bg-surface border border-border-default rounded-md shadow-sm p-8 flex flex-col items-center justify-center text-center">
            <div className="mx-auto w-16 h-16 bg-muted rounded-2xl flex items-center justify-center border border-border-default shadow-sm mb-6">
              <BarChart3 className="h-8 w-8 text-interactive" />
            </div>
            <h3 className="text-lg font-medium text-primary">Grafana Advanced Metrics</h3>
            <p className="mt-2 text-sm text-secondary leading-relaxed max-w-sm">
              For complex visualizations, historical trending, and multi-dimensional analysis spanning beyond the immediate active window, open the dedicated Grafana workspace.
            </p>
            <Button variant="default" className="mt-6 gap-2" onClick={() => window.open('http://localhost:3000', '_blank')}>
              Launch Grafana
            </Button>

      </div>
    </div>
  );
}
