import { NextResponse } from 'next/server';
import { queryDb } from '@/lib/db';

export async function GET() {
  try {
    // Pipeline telemetry is stored in the 'pipeline_events' table
    const query = `
      WITH LatestRuns AS (
        SELECT 
          run_id,
          MAX(timestamp) as updated_at,
          MIN(timestamp) as started_at,
          MAX(hospital_id) as hospital_id,
          MAX(batch_id) as batch_id,
          MAX(stage) as current_stage,
          MAX(status) as status,
          SUM(duration_ms) / 1000.0 as duration_sec,
          MAX(records_in) as records_in,
          MAX(records_out) as records_out,
          SUM(violations_count) as dq_violations,
          SUM(errors) as errors
        FROM pipeline_events
        GROUP BY run_id
      )
      SELECT * FROM LatestRuns
      ORDER BY updated_at DESC
      LIMIT 50;
    `;
    
    const runs = await queryDb('telemetry', query);
    
    return NextResponse.json(runs);
  } catch (error) {
    console.error("API Error fetching pipelines:", error);
    return NextResponse.json({ error: 'Failed to fetch pipeline data' }, { status: 500 });
  }
}
