"use client";

import React from 'react';
import { RagAnalysisSummary } from '@/lib/types';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Clock, Search, Filter } from 'lucide-react';

interface RagHistoryTableProps {
  data: RagAnalysisSummary[];
  onSelect: (id: string) => void;
  loading: boolean;
}

export function RagHistoryTable({ data, onSelect, loading }: RagHistoryTableProps) {
  if (loading) {
    return (
      <Card className="p-8 text-center text-secondary border-border bg-surface">
        <div className="animate-pulse flex items-center justify-center gap-2">
          <div className="w-2 h-2 rounded-full bg-current"></div>
          <div className="w-2 h-2 rounded-full bg-current animation-delay-200"></div>
          <div className="w-2 h-2 rounded-full bg-current animation-delay-400"></div>
        </div>
      </Card>
    );
  }

  if (!data || data.length === 0) {
    return (
      <Card className="p-8 text-center text-secondary border-border bg-surface text-sm">
        No historical RAG analyses found in the logs.
      </Card>
    );
  }

  return (
    <Card className="border-border bg-surface overflow-hidden flex flex-col h-full">
      <div className="p-4 border-b border-border flex items-center justify-between bg-surface-elevated">
        <div className="flex items-center gap-2 text-sm text-secondary">
          <Filter className="w-4 h-4" />
          <span>Showing {data.length} historical analyses</span>
        </div>
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-secondary" />
          <input 
            type="text" 
            placeholder="Search History..." 
            className="pl-9 pr-4 py-1.5 text-sm bg-background border border-border rounded-md text-primary placeholder:text-secondary/50 focus:outline-none focus:border-brand"
            disabled
          />
        </div>
      </div>
      
      <div className="overflow-x-auto flex-1">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-border bg-surface text-xs uppercase tracking-wider text-secondary font-semibold">
              <th className="p-4">Timestamp</th>
              <th className="p-4">Anomaly ID</th>
              <th className="p-4">Dataset</th>
              <th className="p-4">Type</th>
              <th className="p-4">Severity</th>
            </tr>
          </thead>
          <tbody className="text-sm divide-y divide-border">
            {data.map((row, i) => (
              <tr 
                key={i} 
                className="hover:bg-surface-elevated cursor-pointer transition-colors"
                onClick={() => onSelect(row.anomaly_id)}
              >
                <td className="p-4 text-secondary whitespace-nowrap flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5" />
                  {row.window_date !== "UNKNOWN" ? new Date(row.window_date).toLocaleString() : 'Unknown Date'}
                </td>
                <td className="p-4 font-mono text-xs text-primary">{row.anomaly_id.split('-')[0]}...</td>
                <td className="p-4 text-primary">{row.dataset}</td>
                <td className="p-4 text-secondary">{row.anomaly_type.replace(/_/g, ' ')}</td>
                <td className="p-4">
                  <Badge variant={row.severity === 'CRITICAL' ? 'critical' : row.severity === 'ERROR' ? 'critical' : row.severity === 'WARNING' ? 'warning' : 'outline'}>
                    {row.severity}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
