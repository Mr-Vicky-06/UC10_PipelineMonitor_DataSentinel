'use client';

import React, { useMemo } from 'react';
import { usePipelines, useAnomalies, useAlerts } from '@/lib/hooks';
import { LoadingState } from '@/components/ui/states';
import { ExternalLink, Activity, Clock, AlertTriangle, ShieldAlert } from 'lucide-react';
import { format, parseISO } from 'date-fns';
import { 
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, 
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer 
} from 'recharts';
import { buildGrafanaDashboardUrl } from '@/lib/grafana';

const COLORS = {
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
  muted: '#cbd5e1',
};

export default function Analytics() {
  const { data: pipelines, isLoading: isLoadingPipelines } = usePipelines();
  const { data: anomalies, isLoading: isLoadingAnomalies } = useAnomalies();
  const { data: alerts, isLoading: isLoadingAlerts } = useAlerts();

  const isLoading = isLoadingPipelines || isLoadingAnomalies || isLoadingAlerts;

  const chartData = useMemo(() => {
    if (isLoading) return null;
    
    const activeAnomalies = anomalies || [];
    const activePipelines = pipelines || [];
    const activeAlerts = alerts || [];

    // Trend by hour (simulated from started_at for demonstration of trends if small window, else by day)
    // We group runs by the hour they started
    const runsByHour = activePipelines.reduce((acc: any, run) => {
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
    
    const runTrend = Object.values(runsByHour).slice(-24); // Last 24 entries

    // Stage duration / performance
    // Derived from run current_stage and duration.
    const stageAgg = activePipelines.reduce((acc: any, run) => {
      const st = run.current_stage || 'UNKNOWN';
      if (!acc[st]) acc[st] = { stage: st, duration: 0, count: 0 };
      acc[st].duration += run.duration_sec || 0;
      acc[st].count += 1;
      return acc;
    }, {});
    const stagePerformance = Object.values(stageAgg).map((s: any) => ({
      stage: s.stage,
      avg_duration: s.count > 0 ? Math.round(s.duration / s.count) : 0,
      count: s.count
    }));

    // Anomaly Distribution
    const anomalyDist = activeAnomalies.reduce((acc: any, a) => {
      const d = a.domain || 'UNKNOWN';
      acc[d] = (acc[d] || 0) + 1;
      return acc;
    }, {});
    const anomalyPie = Object.keys(anomalyDist).map(k => ({ name: k, value: anomalyDist[k] }));

    // Incident Severity
    const severityDist = activeAlerts.reduce((acc: any, a) => {
      const s = a.severity || 'UNKNOWN';
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    }, {});
    const severityPie = Object.keys(severityDist).map(k => ({ name: k, value: severityDist[k] }));

    // SLA State
    const slaDist = activeAlerts.filter(a => a.alert_type === 'SLA').reduce((acc: any, a) => {
      const s = a.sla_status || 'UNKNOWN';
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    }, {});
    const slaPie = Object.keys(slaDist).map(k => ({ name: k, value: slaDist[k] }));

    return {
      runTrend,
      stagePerformance,
      anomalyPie,
      severityPie,
      slaPie,
      activePipelines,
      activeAnomalies,
      activeAlerts
    };
  }, [pipelines, anomalies, alerts, isLoading]);

  if (isLoading || !chartData) {
    return <LoadingState message="Loading DataSentinel Native Analytics..." />;
  }

  return (
    <div className="flex flex-col gap-6 h-full pb-10">
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-6 shrink-0 border-b border-border-default pb-6">
        <div className="flex-1">
          <h1 className="text-2xl font-bold tracking-tight text-primary mb-2">Native Analytics Workspace</h1>
          <p className="text-sm text-secondary mb-6">Live operational aggregations (Grafana iframe disabled due to container unreliability).</p>
          
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
             <div className="bg-surface border border-border-default rounded-md p-4 shadow-sm">
               <div className="text-xs font-semibold text-secondary mb-1 uppercase tracking-wider flex items-center gap-1.5"><Activity size={14}/> Active Runs</div>
               <div className="text-2xl font-bold text-primary tabular-nums">{chartData.activePipelines.filter(p => p.status === 'RUNNING').length}</div>
             </div>
             <div className="bg-surface border border-border-default rounded-md p-4 shadow-sm">
               <div className="text-xs font-semibold text-secondary mb-1 uppercase tracking-wider flex items-center gap-1.5"><AlertTriangle size={14}/> Active Anomalies</div>
               <div className="text-2xl font-bold text-status-warning tabular-nums">{chartData.activeAnomalies.length}</div>
             </div>
             <div className="bg-surface border border-border-default rounded-md p-4 shadow-sm">
               <div className="text-xs font-semibold text-secondary mb-1 uppercase tracking-wider flex items-center gap-1.5"><ShieldAlert size={14}/> Open Incidents</div>
               <div className="text-2xl font-bold text-status-critical tabular-nums">{chartData.activeAlerts.filter(a => a.severity === 'CRITICAL' || a.severity === 'ERROR').length}</div>
             </div>
             <div className="bg-surface border border-border-default rounded-md p-4 shadow-sm">
               <div className="text-xs font-semibold text-secondary mb-1 uppercase tracking-wider flex items-center gap-1.5"><Clock size={14}/> SLA Breached</div>
               <div className="text-2xl font-bold text-status-error tabular-nums">{chartData.activeAlerts.filter(a => a.alert_type === 'SLA' && a.sla_status === 'BREACHED').length}</div>
             </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-surface border border-border-default rounded-md text-xs font-medium text-secondary shadow-sm">
            <div className="w-2 h-2 rounded-full bg-status-success animate-pulse"></div>
            Live Sync: {format(new Date(), 'HH:mm:ss')}
          </div>

          <a 
            href={buildGrafanaDashboardUrl("pipeline_performance_d0", "now-7d")}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 rounded-md text-sm font-medium transition-colors shadow-sm"
          >
            Deep Analytics (Grafana) <ExternalLink className="h-4 w-4" />
          </a>
        </div>
      </div>
      
      {/* Native React Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Runs Over Time */}
        <div className="bg-surface border border-border-default rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-4 text-primary">Pipeline Execution Trend</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData.runTrend}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                <XAxis dataKey="time" tick={{fontSize: 12}} tickMargin={10} stroke="#94a3b8" />
                <YAxis tick={{fontSize: 12}} stroke="#94a3b8" />
                <Tooltip contentStyle={{ borderRadius: '6px', border: '1px solid #e2e8f0', boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)' }} />
                <Legend iconType="circle" wrapperStyle={{ fontSize: '12px' }} />
                <Line type="monotone" dataKey="COMPLETED" stroke={COLORS.success} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                <Line type="monotone" dataKey="FAILED" stroke={COLORS.error} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="RUNNING" stroke={COLORS.info} strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stage Performance */}
        <div className="bg-surface border border-border-default rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-4 text-primary">Stage Average Duration (Sec)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData.stagePerformance} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
                <XAxis type="number" tick={{fontSize: 12}} stroke="#94a3b8" />
                <YAxis dataKey="stage" type="category" width={100} tick={{fontSize: 12}} stroke="#94a3b8" />
                <Tooltip cursor={{fill: '#f1f5f9'}} contentStyle={{ borderRadius: '6px' }} />
                <Bar dataKey="avg_duration" fill={COLORS.info} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Anomaly Distribution */}
        <div className="bg-surface border border-border-default rounded-lg p-4 shadow-sm">
          <h3 className="text-sm font-semibold mb-4 text-primary">Anomaly Distribution by Domain</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={chartData.anomalyPie} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                  {chartData.anomalyPie.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={[COLORS.warning, COLORS.info, COLORS.error, COLORS.muted][index % 4]} />
                  ))}
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={36} wrapperStyle={{ fontSize: '12px' }} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Incident Severity */}
        <div className="bg-surface border border-border-default rounded-lg p-4 shadow-sm flex flex-col md:flex-row gap-4">
           <div className="flex-1">
             <h3 className="text-sm font-semibold mb-4 text-primary">Incident Severity</h3>
             <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={chartData.severityPie} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value">
                    {chartData.severityPie.map((entry, index) => {
                      let color = COLORS.muted;
                      if (entry.name === 'CRITICAL') color = COLORS.error;
                      if (entry.name === 'ERROR') color = '#f97316';
                      if (entry.name === 'WARNING') color = COLORS.warning;
                      return <Cell key={`cell-${index}`} fill={color} />;
                    })}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
             </div>
           </div>
           
           <div className="flex-1">
             <h3 className="text-sm font-semibold mb-4 text-primary">SLA Infractions</h3>
             <div className="h-48">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={chartData.slaPie} cx="50%" cy="50%" innerRadius={40} outerRadius={60} dataKey="value">
                    {chartData.slaPie.map((entry, index) => {
                      let color = COLORS.muted;
                      if (entry.name === 'BREACHED') color = COLORS.error;
                      if (entry.name === 'AT_RISK') color = COLORS.warning;
                      return <Cell key={`cell-${index}`} fill={color} />;
                    })}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
             </div>
           </div>
        </div>

      </div>
    </div>
  );
}
