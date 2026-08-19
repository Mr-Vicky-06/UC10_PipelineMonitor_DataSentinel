'use client';

import React, { useMemo } from 'react';
import { usePipelines, useAlerts, useAnomalies } from '@/lib/hooks';
import { MetricCard } from '@/components/ui/metric-card';
import { LoadingState, ErrorState } from '@/components/ui/states';
import { AlertTriangle, Activity, Clock, ServerCrash } from 'lucide-react';
import { format } from 'date-fns';
import { ActiveRunsPanel } from '@/components/dashboard/active-runs-panel';
import { SlaMonitoringPanel } from '@/components/dashboard/sla-monitoring-panel';
import { PipelineExecutionRing } from '@/components/dashboard/pipeline-execution-ring';
import { StageExecutionSummary } from '@/components/dashboard/stage-execution-summary';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';

import { IncidentIntelligence } from '@/components/dashboard/incident-intelligence';
import { IncidentDrawer } from '@/components/ui/incident-drawer';

const COLORS = {
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
  muted: '#cbd5e1',
};

export default function OperationsCenter() {
  const { data: pipelines, isLoading: isLoadingPipelines, error: errorPipelines } = usePipelines();
  const { data: alerts, isLoading: isLoadingAlerts, error: errorAlerts } = useAlerts();
  const { data: anomalies, isLoading: isLoadingAnomalies } = useAnomalies();
  const [investigatingIncident, setInvestigatingIncident] = React.useState<string | null>(null);

  const chartData = useMemo(() => {
    if (!pipelines || !alerts || !anomalies) return null;
    
    // Trend by hour (simulated from started_at)
    const runsByHour = pipelines.reduce((acc: any, run) => {
      const date = new Date(run.started_at);
      const hourStr = isNaN(date.getTime()) ? "Unknown" : format(date, 'MMM dd HH:00');
      if (!acc[hourStr]) {
        acc[hourStr] = { time: hourStr, COMPLETED: 0, FAILED: 0, RUNNING: 0, total: 0 };
      }
      if (run.status === 'HEALTHY' || run.status === 'COMPLETED_WITH_VIOLATIONS') acc[hourStr].COMPLETED++;
      else if (run.status === 'FAILED') acc[hourStr].FAILED++;
      else if (run.status === 'RUNNING') acc[hourStr].RUNNING++;
      acc[hourStr].total++;
      return acc;
    }, {});
    const runTrend = Object.values(runsByHour).slice(-24);

    // Failure Rate
    const failureTrend = Object.values(runsByHour).slice(-24).map((r: any) => ({
      time: r.time,
      rate: r.total > 0 ? Math.round((r.FAILED / r.total) * 100) : 0
    }));

    // Anomaly Distribution
    const anomalyDist = anomalies.reduce((acc: any, a) => {
      const d = a.domain || 'UNKNOWN';
      acc[d] = (acc[d] || 0) + 1;
      return acc;
    }, {});
    const anomalyPie = Object.keys(anomalyDist).map(k => ({ name: k, value: anomalyDist[k] }));

    // Incident Severity
    const severityDist = alerts.reduce((acc: any, a) => {
      const s = a.severity || 'UNKNOWN';
      if (a.status !== 'RESOLVED') {
        acc[s] = (acc[s] || 0) + 1;
      }
      return acc;
    }, {});
    const severityPie = Object.keys(severityDist).map(k => ({ name: k, value: severityDist[k] }));

    return { runTrend, failureTrend, anomalyPie, severityPie };
  }, [pipelines, alerts, anomalies]);

  if (isLoadingPipelines || isLoadingAlerts || isLoadingAnomalies) {
    return <LoadingState message="Connecting to DataSentinel Telemetry..." />;
  }

  if (errorPipelines || errorAlerts) {
    return <ErrorState message="Failed to connect to DataSentinel backend API." />;
  }

  const pData = pipelines || [];
  const aData = alerts || [];
  const anData = anomalies || [];

  const activeIncidents = aData.filter(a => a.status !== 'RESOLVED');
  const activePipelines = pData.filter(p => p.status === 'RUNNING');
  const failedPipelines = pData.filter(p => p.status === 'FAILED');
  
  const slaAlerts = aData.filter(a => a.alert_type === 'SLA');
  const slaAtRisk = slaAlerts.filter(a => a.sla_status === 'AT_RISK').length;
  const slaBreached = slaAlerts.filter(a => a.sla_status === 'BREACHED').length;

  return (
    <>
      <div className="flex flex-col gap-6 pb-10">
        {/* 1. Global Header */}
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 border-b border-border-default pb-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-primary">Operations Center</h1>
            <p className="text-sm text-secondary mt-1">Enterprise Healthcare Data Observability</p>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <div className="flex flex-col items-end">
              <span className="text-secondary text-xs uppercase font-semibold tracking-wider">Environment</span>
              <span className="font-medium text-primary">Production (UC10)</span>
            </div>
            <div className="w-px h-8 bg-border-default"></div>
            <div className="flex flex-col items-end">
              <span className="text-secondary text-xs uppercase font-semibold tracking-wider">Connection</span>
              <div className="flex items-center gap-1.5 font-medium text-status-success">
                <div className="w-2 h-2 rounded-full bg-status-success animate-pulse"></div>
                LIVE
              </div>
            </div>
            <div className="w-px h-8 bg-border-default"></div>
            <div className="flex flex-col items-end">
              <span className="text-secondary text-xs uppercase font-semibold tracking-wider">Last Update</span>
              <span className="font-medium tabular-nums text-primary">{format(new Date(), 'HH:mm:ss')}</span>
            </div>
          </div>
        </div>
        
        {/* 2. System Health Strip */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <MetricCard title="Active Runs" value={activePipelines.length} icon={<Activity className="text-status-info" />} />
          <MetricCard title="Failed Runs" value={failedPipelines.length} icon={<ServerCrash className="text-status-error" />} />
          <MetricCard title="Active Anomalies" value={anData.length} icon={<Activity className="text-status-warning" />} />
          <MetricCard title="Open Incidents" value={activeIncidents.length} icon={<AlertTriangle className={activeIncidents.some(i => i.severity === 'CRITICAL') ? "text-status-critical" : "text-status-warning"} />} />
          <MetricCard title="SLA At Risk" value={slaAtRisk} icon={<Clock className="text-status-warning" />} />
          <MetricCard title="SLA Breached" value={slaBreached} icon={<Clock className="text-status-error" />} />
        </div>

        {/* 3. PRIMARY OPERATIONS SECTION */}
        <section className="bg-surface border border-border-default rounded-lg p-6 shadow-sm">
          <h2 className="text-lg font-bold text-primary mb-6">Pipeline Execution</h2>
          <PipelineExecutionRing pipelines={pData} />
          <StageExecutionSummary pipelines={pData} />
        </section>

        {/* 4. MONITORING SECTION */}
        {chartData && (
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-surface border border-border-default rounded-lg p-5 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold mb-4 text-primary">Pipeline Run Trend</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData.runTrend}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="time" tick={{fontSize: 10}} tickMargin={10} stroke="#94a3b8" />
                    <YAxis tick={{fontSize: 10}} stroke="#94a3b8" width={30} />
                    <Tooltip contentStyle={{ borderRadius: '6px', fontSize: '12px' }} />
                    <Line type="monotone" dataKey="COMPLETED" stroke={COLORS.success} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="FAILED" stroke={COLORS.error} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-surface border border-border-default rounded-lg p-5 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold mb-4 text-primary">Failure Rate (%)</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData.failureTrend}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="time" tick={{fontSize: 10}} tickMargin={10} stroke="#94a3b8" />
                    <YAxis tick={{fontSize: 10}} stroke="#94a3b8" width={30} />
                    <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{ borderRadius: '6px', fontSize: '12px' }} />
                    <Bar dataKey="rate" fill={COLORS.error} radius={[2, 2, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-surface border border-border-default rounded-lg p-5 shadow-sm flex flex-col">
              <h3 className="text-sm font-semibold mb-4 text-primary">Anomaly Distribution</h3>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData.anomalyPie} cx="50%" cy="50%" innerRadius={40} outerRadius={60} paddingAngle={5} dataKey="value">
                      {chartData.anomalyPie.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={[COLORS.warning, COLORS.info, COLORS.error, COLORS.muted][index % 4]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={{ borderRadius: '6px', fontSize: '12px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        )}

        {/* 5. LOWER SECTION */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mt-4">
          <div className="flex flex-col gap-6">
            <div className="h-[250px]">
               <IncidentIntelligence onInvestigate={setInvestigatingIncident} />
            </div>
            
            {chartData && (
              <div className="bg-surface border border-border-default rounded-lg p-5 shadow-sm flex flex-col h-[226px]">
                <h3 className="text-sm font-semibold mb-4 text-primary">Active Incident Severity</h3>
                <div className="flex-1 min-h-0">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={chartData.severityPie} cx="50%" cy="50%" innerRadius={35} outerRadius={55} dataKey="value">
                        {chartData.severityPie.map((entry, index) => {
                          let color = COLORS.muted;
                          if (entry.name === 'CRITICAL') color = COLORS.error;
                          if (entry.name === 'ERROR') color = '#f97316';
                          if (entry.name === 'WARNING') color = COLORS.warning;
                          return <Cell key={`cell-${index}`} fill={color} />;
                        })}
                      </Pie>
                      <Tooltip contentStyle={{ borderRadius: '6px', fontSize: '12px' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>
          
          <div className="bg-surface border border-border-default rounded-lg shadow-sm flex flex-col h-[500px]">
            <div className="p-4 border-b border-border-default shrink-0">
              <h3 className="font-semibold text-primary">Active Pipeline Runs</h3>
            </div>
            <div className="flex-1 min-h-0">
              <ActiveRunsPanel pipelines={activePipelines} />
            </div>
          </div>
          
          <div className="bg-surface border border-border-default rounded-lg shadow-sm flex flex-col h-[500px]">
            <div className="p-4 border-b border-border-default shrink-0">
              <h3 className="font-semibold text-primary">SLA Monitoring</h3>
            </div>
            <div className="flex-1 min-h-0">
              <SlaMonitoringPanel slaAlerts={slaAlerts} />
            </div>
          </div>
        </div>
      </div>

      {/* Detail Drawer */}
      <IncidentDrawer 
        incidentId={investigatingIncident} 
        onClose={() => setInvestigatingIncident(null)} 
      />
    </>
  );
}
