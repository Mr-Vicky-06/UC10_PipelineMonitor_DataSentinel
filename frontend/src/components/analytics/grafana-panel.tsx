'use client';

import React, { useState, useEffect } from 'react';
import { buildGrafanaPanelUrl, buildGrafanaDashboardUrl, GrafanaTimeRange } from '@/lib/grafana';
import { ExternalLink, RefreshCw, AlertCircle } from 'lucide-react';

interface GrafanaPanelProps {
  dashboardUid: string;
  panelId: number;
  timeRange: GrafanaTimeRange;
  title: string;
  height?: string | number;
  className?: string;
}

type PanelStatus = 'loading' | 'connected' | 'unavailable';

export function GrafanaPanel({ dashboardUid, panelId, timeRange, title, height = 300, className = '' }: GrafanaPanelProps) {
  const [status, setStatus] = useState<PanelStatus>('loading');
  const iframeUrl = buildGrafanaPanelUrl(dashboardUid, panelId, timeRange);
  const dashboardUrl = buildGrafanaDashboardUrl(dashboardUid, timeRange);

  const checkHealth = async () => {
    setStatus('loading');
    try {
      const res = await fetch('/api/grafana/health');
      if (res.ok) {
        setStatus('connected');
      } else {
        setStatus('unavailable');
      }
    } catch (err) {
      setStatus('unavailable');
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className={`flex flex-col bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden ${className}`}>
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100 bg-slate-50/50">
        <h3 className="text-sm font-semibold text-slate-800 tracking-tight">{title}</h3>
        <div className="flex items-center space-x-2">
          {status === 'connected' && (
            <a
              href={dashboardUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-blue-600 transition-colors"
              title="Open full Grafana workspace"
              aria-label="Open full Grafana workspace"
            >
              <ExternalLink size={16} />
            </a>
          )}
        </div>
      </div>
      
      <div className="relative w-full" style={{ height }}>
        {status === 'loading' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-500">
            <RefreshCw className="animate-spin mb-2" size={24} />
            <span className="text-sm">Loading historical analytics...</span>
          </div>
        )}

        {status === 'unavailable' && (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 text-slate-600 px-4 text-center">
            <AlertCircle className="text-amber-500 mb-3" size={32} />
            <p className="font-medium text-slate-800 mb-1">Historical analytics unavailable</p>
            <p className="text-sm text-slate-500 mb-4 max-w-sm">Grafana is currently unavailable. Operational telemetry remains available.</p>
            <button 
              onClick={checkHealth}
              className="px-4 py-2 bg-white border border-slate-300 rounded shadow-sm text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Retry Connection
            </button>
          </div>
        )}

        {status === 'connected' && (
          <iframe
            src={iframeUrl}
            width="100%"
            height="100%"
            frameBorder="0"
            className="block"
            title={`Grafana Panel: ${title}`}
            onLoad={() => setStatus('connected')}
          />
        )}
      </div>
    </div>
  );
}
