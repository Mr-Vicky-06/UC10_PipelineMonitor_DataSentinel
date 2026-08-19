import React from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { PipelineRun } from '@/lib/types';

interface PipelineExecutionRingProps {
  pipelines: PipelineRun[];
}

const COLORS = {
  COMPLETED: '#10b981', // green
  FAILED: '#ef4444',    // red
  RUNNING: '#3b82f6',   // blue
  PENDING: '#94a3b8',   // slate
};

export function PipelineExecutionRing({ pipelines }: PipelineExecutionRingProps) {
  const completed = pipelines.filter(p => p.status === 'HEALTHY' || p.status === 'COMPLETED_WITH_VIOLATIONS').length;
  const failed = pipelines.filter(p => p.status === 'FAILED').length;
  const running = pipelines.filter(p => p.status === 'RUNNING').length;
  // Assume everything else pending or running depending on logic, or just 0 if no pending state in data.
  const pending = pipelines.filter(p => p.status === 'BLOCKED').length;

  const total = completed + failed + running + pending;

  const data = [
    { name: 'Completed', value: completed, color: COLORS.COMPLETED },
    { name: 'Failed', value: failed, color: COLORS.FAILED },
    { name: 'Running', value: running, color: COLORS.RUNNING },
    { name: 'Pending', value: pending, color: COLORS.PENDING },
  ].filter(d => d.value > 0);

  const activeRatio = total > 0 ? Math.round(((completed + running) / total) * 100) : 0;

  return (
    <div className="flex flex-col md:flex-row items-center justify-center gap-8 p-6 bg-surface border border-border-default rounded-lg shadow-sm">
      <div className="relative w-48 h-48">
        {total === 0 ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-secondary bg-slate-50 rounded-full border border-slate-200">
             <span className="text-sm font-medium px-4 text-center">No active execution</span>
          </div>
        ) : (
          <>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={70}
                  outerRadius={90}
                  paddingAngle={2}
                  dataKey="value"
                  stroke="none"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip contentStyle={{ borderRadius: '6px', fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
            <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
              <span className="text-xs font-semibold text-secondary uppercase tracking-widest">Execution</span>
              <span className="text-3xl font-bold text-primary tabular-nums">{activeRatio}%</span>
            </div>
          </>
        )}
      </div>

      <div className="flex flex-col gap-3 min-w-[140px]">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.COMPLETED }}></div>
            <span className="text-sm font-medium text-secondary">Completed</span>
          </div>
          <span className="text-sm font-bold text-primary tabular-nums">{completed}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.FAILED }}></div>
            <span className="text-sm font-medium text-secondary">Failed</span>
          </div>
          <span className="text-sm font-bold text-primary tabular-nums">{failed}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.RUNNING }}></div>
            <span className="text-sm font-medium text-secondary">Running</span>
          </div>
          <span className="text-sm font-bold text-primary tabular-nums">{running}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS.PENDING }}></div>
            <span className="text-sm font-medium text-secondary">Pending</span>
          </div>
          <span className="text-sm font-bold text-primary tabular-nums">{pending}</span>
        </div>
      </div>
    </div>
  );
}
