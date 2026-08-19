export const GRAFANA_CONFIG = {
  baseUrl: process.env.NEXT_PUBLIC_GRAFANA_BASE_URL || 'http://localhost:3002',
  dashboards: {
    pipelinePerformance: {
      uid: 'pipeline_performance_d0',
      panels: {
        runsOverTime: 1,
        completedVsFailed: 2,
        runsByStage: 3,
        failureRate: 4,
        stageDuration: 5,
        recentEvents: 6,
      },
    },
  },
};

export type GrafanaTimeRange = 'now-1h' | 'now-6h' | 'now-24h' | 'now-7d' | 'now-30d';

export function buildGrafanaPanelUrl(dashboardUid: string, panelId: number, timeRange: GrafanaTimeRange): string {
  const { baseUrl } = GRAFANA_CONFIG;
  // Grafana embedding URL format: /d-solo/<uid>?panelId=<id>&from=<range>&to=now&theme=light
  return `${baseUrl}/d-solo/${dashboardUid}?panelId=${panelId}&from=${timeRange}&to=now&theme=light&kiosk`;
}

export function buildGrafanaDashboardUrl(dashboardUid: string, timeRange: GrafanaTimeRange): string {
  const { baseUrl } = GRAFANA_CONFIG;
  return `${baseUrl}/d/${dashboardUid}?from=${timeRange}&to=now&theme=light`;
}
