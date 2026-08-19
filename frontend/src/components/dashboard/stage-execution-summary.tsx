import React from 'react';
import { PipelineRun } from '@/lib/types';

interface StageExecutionSummaryProps {
  pipelines: PipelineRun[];
}

const STAGES = [
  { id: 'INGEST', label: 'INGEST' },
  { id: 'CLEAN', label: 'CLEAN' },
  { id: 'VALIDATE', label: 'VALIDATE' },
  { id: 'TRANSFORM', label: 'TRANSFORM' },
  { id: 'ML', label: 'ML / RAG' },
  { id: 'ALERT', label: 'ALERT / RCA' }
];

export function StageExecutionSummary({ pipelines }: StageExecutionSummaryProps) {
  
  // Calculate stats for each stage based on the current pipelines
  const stageStats = STAGES.map(stageObj => {
    // A run is considered to have 'passed' this stage if current_stage is past it, or if it is currently in it.
    // For simplicity, we just count how many pipelines are currently IN this stage, or if we had historical stage data, we would use it.
    // Since we only have current_stage per run, we'll aggregate current state:
    const runsInStage = pipelines.filter(p => p.current_stage === stageObj.id);
    const count = runsInStage.length;
    const errors = runsInStage.filter(p => p.status === 'FAILED').length;
    const warnings = runsInStage.filter(p => p.status === 'WARNING' || p.status === 'COMPLETED_WITH_VIOLATIONS').length;
    const avgDuration = count > 0 ? Math.round(runsInStage.reduce((acc, r) => acc + (r.duration_sec || 0), 0) / count) : 0;

    let statusColor = 'bg-slate-200';
    let textColor = 'text-slate-500';
    if (errors > 0) {
      statusColor = 'bg-status-error';
      textColor = 'text-status-error';
    } else if (warnings > 0) {
      statusColor = 'bg-status-warning';
      textColor = 'text-status-warning';
    } else if (count > 0) {
      statusColor = 'bg-status-info';
      textColor = 'text-status-info';
    }

    return {
      ...stageObj,
      count,
      errors,
      warnings,
      avgDuration,
      statusColor,
      textColor
    };
  });

  return (
    <div className="flex flex-col gap-3 mt-4">
      <h4 className="text-xs font-semibold text-secondary uppercase tracking-widest mb-1">Stage Execution Strip</h4>
      <div className="grid grid-cols-2 md:grid-cols-6 gap-2">
        {stageStats.map(stat => (
          <div key={stat.id} className="bg-slate-50 border border-slate-200 rounded-md p-3 flex flex-col justify-between">
            <div className="flex items-center justify-between mb-2">
              <span className={`text-xs font-bold ${stat.count > 0 ? 'text-slate-800' : 'text-slate-400'}`}>{stat.label}</span>
              <div className={`w-2 h-2 rounded-full ${stat.statusColor} ${stat.count > 0 && stat.errors === 0 && stat.warnings === 0 ? 'animate-pulse' : ''}`}></div>
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Active</span>
                <span className="font-mono font-medium text-slate-700">{stat.count}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500">Avg (s)</span>
                <span className="font-mono font-medium text-slate-700">{stat.avgDuration > 0 ? stat.avgDuration : '--'}</span>
              </div>
            </div>
            
            {/* Status bar */}
            <div className="mt-3 h-1.5 w-full bg-slate-200 rounded-full overflow-hidden flex">
               {stat.errors > 0 ? (
                  <div className="h-full bg-status-error w-full"></div>
               ) : stat.warnings > 0 ? (
                  <div className="h-full bg-status-warning w-full"></div>
               ) : stat.count > 0 ? (
                  <div className="h-full bg-status-info w-full"></div>
               ) : null}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
