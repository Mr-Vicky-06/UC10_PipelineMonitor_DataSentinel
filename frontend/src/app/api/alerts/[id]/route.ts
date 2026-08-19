import { NextResponse } from 'next/server';
import { AlertEvent, SLAStatus } from '@/lib/types';
// @ts-ignore
import Database from 'better-sqlite3';
import path from 'path';

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const params = await context.params;
  const alertId = params.id;
  try {
    
    // First query the fastAPI backend just to get the base alert info to ensure it exists
    const response = await fetch(`http://localhost:8000/api/v1/alerts/${alertId}`, {
      cache: 'no-store'
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json({ error: 'Incident not found' }, { status: 404 });
      }
      return NextResponse.json({ error: 'Alert service unavailable' }, { status: 503 });
    }

    const alert = await response.json();
    
    // Connect to SQLite directly to get the details_json
    const dbPath = path.resolve(process.cwd(), '../alert-engine/alertdb.sqlite3');
    const db = new Database(dbPath, { readonly: true });
    
    const row = db.prepare('SELECT details_json FROM alert_details WHERE alert_id = ?').get(alertId) as any;
    
    db.close();

    let evidence: any[] = [];
    
    if (row && row.details_json) {
      try {
        const parsedDetails = JSON.parse(row.details_json);
        
        // Structure the parsed JSON into evidence items
        if (alert.event_type === 'DQ') {
          evidence.push({
            type: 'Data Quality Evidence',
            title: 'Rule Violation',
            value: parsedDetails.rule_id || parsedDetails.rule_name,
            description: `Affected ${parsedDetails.affected_rows} out of ${parsedDetails.total_rows} records (${parsedDetails.affected_percentage}%).`
          });
          if (parsedDetails.field) {
            evidence.push({
              type: 'Data Quality Evidence',
              title: 'Target Field',
              value: parsedDetails.field,
              description: 'The dataset field that violated the rule.'
            });
          }
        } else if (alert.event_type === 'ANOMALY') {
           evidence.push({
            type: 'Anomaly Evidence',
            title: 'Deviation',
            value: `${parsedDetails.deviation}% deviation`,
            description: `Expected ~${parsedDetails.expected}, but actual was ${parsedDetails.actual}.`
          });
        } else if (alert.event_type === 'SLA') {
           evidence.push({
            type: 'SLA Evidence',
            title: 'Pipeline Delay',
            value: parsedDetails.pipeline_status,
            description: `Deadline: ${parsedDetails.deadline}. Estimated completion: ${parsedDetails.estimated_completion}.`
          });
        } else if (alert.event_type === 'PIPELINE') {
            evidence.push({
            type: 'Pipeline Execution Evidence',
            title: 'Stage Failure',
            value: parsedDetails.stage || parsedDetails.job_name,
            description: `Pipeline stage failed during execution.`
          });
        }
      } catch (e) {
        console.warn(`Failed to parse details JSON for ${alertId}`);
      }
    }
    
    let slaStatus: SLAStatus = 'UNKNOWN';
    if (alert.event_type === 'SLA') {
      slaStatus = alert.severity === 'CRITICAL' ? 'BREACHED' : 'AT_RISK';
    }

    const result = {
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
      evidence: evidence
    };

    return NextResponse.json(result);
  } catch (error) {
    console.error(`API Error fetching alert details for ${alertId}:`, error);
    return NextResponse.json(
      { error: 'Failed to fetch alert details' },
      { status: 500 }
    );
  }
}
