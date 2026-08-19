import React from 'react';
import { PipelineRun, AnomalyEvent, AlertEvent } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { ArrowRight, CheckCircle2, AlertCircle, Clock, Activity, ShieldAlert, Cpu, AlertTriangle, DatabaseIcon, FilterIcon, SearchIcon, FileSearchIcon } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface PipelineTopologyProps {
  pipelines: PipelineRun[];
  anomalies: AnomalyEvent[];
  alerts: AlertEvent[];
}

type NodeStatus = 'HEALTHY' | 'RUNNING' | 'WARNING' | 'ERROR' | 'CRITICAL' | 'STALE' | 'UNKNOWN';

interface TopologyNode {
  id: string;
  label: string;
  icon: React.ElementType;
  status: NodeStatus;
  detail?: string;
  subtext?: string;
}

const STAGES = [
  { id: 'INGEST', label: 'INGEST', icon: DatabaseIcon },
  { id: 'CLEAN', label: 'CLEAN', icon: FilterIcon },
  { id: 'VALIDATE', label: 'VALIDATE', icon: CheckCircle2 },
  { id: 'DQ', label: 'DATA QUALITY', icon: ShieldAlert },
  { id: 'TRANSFORM', label: 'TRANSFORM', icon: Cpu },
  { id: 'ML', label: 'ML DETECTION', icon: Activity },
  { id: 'SLA', label: 'SLA', icon: Clock },
  { id: 'RAG', label: 'RAG / EVIDENCE', icon: FileSearchIcon },
  { id: 'RCA', label: 'RCA', icon: SearchIcon },
  { id: 'ALERT', label: 'ACTION / ALERT', icon: AlertTriangle },
];

export function PipelineTopology({ pipelines, anomalies, alerts }: PipelineTopologyProps) {
  
  // Calculate states based on real data
  const getNodeState = (stageId: string): TopologyNode => {
    const baseNode = STAGES.find(s => s.id === stageId)!;
    let status: NodeStatus = 'HEALTHY';
    let detail = '';
    let subtext = '';

    // 1. Pipeline execution mapping
    const activeRunsInStage = pipelines.filter(p => p.current_stage === stageId && p.status === 'RUNNING');
    const failedRunsInStage = pipelines.filter(p => p.current_stage === stageId && p.status === 'FAILED');
    
    if (activeRunsInStage.length > 0) {
      status = 'RUNNING';
      subtext = `${activeRunsInStage.length} Active`;
    }
    
    if (failedRunsInStage.length > 0) {
      status = 'ERROR';
      detail = `Failed: ${failedRunsInStage[0].run_id}`;
      subtext = `${failedRunsInStage.length} Failed`;
    }

    // 2. Specific stage overrides based on intelligence layers
    if (stageId === 'ML') {
      // Are there anomalies?
      if (anomalies.length > 0) {
        status = 'WARNING';
        subtext = `${anomalies.length} Anomalies`;
        detail = 'Recent anomalies detected';
      }
    }

    if (stageId === 'DQ') {
      const dqAlerts = alerts.filter(a => a.alert_type === 'DATA_QUALITY');
      if (dqAlerts.length > 0) {
        status = 'WARNING';
        subtext = `${dqAlerts.length} Violations`;
      }
    }

    if (stageId === 'SLA') {
      const slaAlerts = alerts.filter(a => a.alert_type === 'SLA');
      if (slaAlerts.some(a => a.sla_status === 'BREACHED')) {
        status = 'ERROR';
        subtext = 'SLA Breached';
      } else if (slaAlerts.some(a => a.sla_status === 'AT_RISK')) {
        status = 'WARNING';
        subtext = 'SLA At Risk';
      }
    }

    if (stageId === 'ALERT') {
      const activeIncidents = alerts.filter(a => a.status !== 'RESOLVED');
      if (activeIncidents.some(a => a.severity === 'CRITICAL')) {
        status = 'CRITICAL';
        subtext = 'Critical Incidents';
      } else if (activeIncidents.some(a => a.severity === 'ERROR')) {
        status = 'ERROR';
        subtext = 'Open Incidents';
      } else if (activeIncidents.length > 0) {
        status = 'WARNING';
        subtext = 'Active Alerts';
      }
    }

    return { ...baseNode, status, detail, subtext };
  };

  const nodes = STAGES.map(s => getNodeState(s.id));

  const statusColors: Record<NodeStatus, string> = {
    HEALTHY: 'border-status-success text-status-success bg-status-success/10',
    RUNNING: 'border-status-info text-status-info bg-status-info/10 animate-pulse-slow',
    WARNING: 'border-status-warning text-status-warning bg-status-warning/10',
    ERROR: 'border-status-error text-status-error bg-status-error/10',
    CRITICAL: 'border-status-critical text-status-critical bg-status-critical/10 shadow-[0_0_15px_rgba(220,38,38,0.3)]',
    STALE: 'border-status-unknown text-status-unknown bg-muted',
    UNKNOWN: 'border-status-unknown text-status-unknown bg-muted',
  };

  const textColors: Record<NodeStatus, string> = {
    HEALTHY: 'text-status-success',
    RUNNING: 'text-status-info',
    WARNING: 'text-status-warning',
    ERROR: 'text-status-error',
    CRITICAL: 'text-status-critical',
    STALE: 'text-secondary',
    UNKNOWN: 'text-secondary',
  };

  return (
    <div className="w-full bg-surface border border-border-default rounded-lg p-6 shadow-sm overflow-x-auto">
      <div className="flex items-center justify-between mb-8">
        <h2 className="text-lg font-semibold tracking-tight text-primary">Live Pipeline Topology</h2>
        <div className="flex items-center gap-4 text-xs font-medium text-secondary">
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-status-success"></div> Healthy</div>
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-status-info animate-pulse"></div> Running</div>
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-status-warning"></div> Warning</div>
          <div className="flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-status-error"></div> Error</div>
        </div>
      </div>
      
      <div className="flex items-start justify-between min-w-[1000px] py-4 relative">
        {/* Connecting Line background */}
        <div className="absolute top-8 left-12 right-12 h-0.5 bg-border-default z-0"></div>

        {nodes.map((node, i) => {
          const Icon = node.icon;
          return (
            <div key={node.id} className="relative z-10 flex flex-col items-center group w-24">
              <div 
                className={cn(
                  "w-16 h-16 rounded-xl flex items-center justify-center border-2 bg-surface transition-all duration-200 cursor-default",
                  statusColors[node.status]
                )}
                title={node.detail || `${node.label} is ${node.status}`}
              >
                <Icon className={cn("w-7 h-7", textColors[node.status])} />
              </div>
              <div className="mt-3 text-center">
                <div className="text-xs font-semibold text-primary mb-1 leading-tight">{node.label}</div>
                {node.subtext && (
                  <div className={cn("text-[10px] font-semibold px-2 py-0.5 rounded-sm whitespace-nowrap", statusColors[node.status])}>
                    {node.subtext}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
