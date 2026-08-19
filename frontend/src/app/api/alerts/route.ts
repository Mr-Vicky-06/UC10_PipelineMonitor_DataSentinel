import { NextResponse } from 'next/server';
import { AlertEvent, SLAStatus } from '@/lib/types';
// @ts-ignore
import Database from 'better-sqlite3';
import path from 'path';

export async function GET() {
  try {
    // Fetch from the real Alert Engine
    const response = await fetch('http://localhost:8000/api/v1/alerts', {
      cache: 'no-store', // ensures we get fresh alerts
    });

    if (!response.ok) {
      console.error('Failed to fetch from Alert Engine:', response.status, response.statusText);
      return NextResponse.json(
        { error: 'Alert service unavailable' },
        { status: 503 }
      );
    }

    const backendAlerts = await response.json();

    // Map AlertResponse to AlertEvent frontend schema
    const alerts: AlertEvent[] = backendAlerts.map((alert: any) => {
      let slaStatus: SLAStatus = 'UNKNOWN';
      let eta: string | undefined;
      let deadline: string | undefined;

      // Direct SQLite query to extract details_json for SLA events, bypassing frozen FastAPI layer
      if (alert.event_type === 'SLA') {
        slaStatus = alert.severity === 'CRITICAL' ? 'BREACHED' : 'AT_RISK';
        try {
          const dbPath = path.resolve(process.cwd(), '../alert-engine/alertdb.sqlite3');
          const db = new Database(dbPath, { readonly: true });
          const row = db.prepare('SELECT details_json FROM alert_details WHERE alert_id = ?').get(alert.alert_id) as any;
          if (row && row.details_json) {
            const parsed = JSON.parse(row.details_json);
            eta = parsed.estimated_completion;
            deadline = parsed.deadline;
          }
          db.close();
        } catch (e) {
          console.warn(`Failed to read SLA details directly from SQLite for ${alert.alert_id}`, e);
        }
      }

      return {
        incident_id: alert.alert_id,
        alert_id: alert.alert_id,
        severity: alert.severity,
        status: alert.status,
        summary: alert.summary,
        alert_type: alert.event_type,
        hospital_id: alert.hospital || 'UNKNOWN',
        batch_id: 'UNKNOWN',
        run_id: alert.pipeline || 'UNKNOWN',
        stage: 'UNKNOWN',
        sla_status: slaStatus,
        detected_at: alert.created_at,
        eta: eta,
        deadline: deadline
      };
    });

    // Sort most recent first
    alerts.sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime());

    return NextResponse.json(alerts);
  } catch (error) {
    console.error('API Error fetching alerts:', error);
    return NextResponse.json(
      { error: 'Failed to fetch alerts' },
      { status: 500 }
    );
  }
}
