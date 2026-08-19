import { NextResponse } from 'next/server';
import duckdb from 'duckdb';
import path from 'path';

if (!(BigInt.prototype as any).toJSON) {
  (BigInt.prototype as any).toJSON = function () {
    return Number(this);
  };
}

export async function GET() {
  try {
    const parquetPath = path.resolve(process.cwd(), '../outputs/anomaly/anomaly_events.parquet');
    const db = new duckdb.Database(':memory:');
    
    return new Promise<NextResponse>((resolve, reject) => {
      const connection = db.connect();
      
      const query = `
        SELECT * FROM read_parquet('${parquetPath}')
        ORDER BY window_date DESC
        LIMIT 100;
      `;
      
      connection.all(query, (err: any, res: any) => {
        connection.close();
        if (err) {
          console.warn("Failed to read anomaly parquet:", err.message);
          resolve(NextResponse.json([]));
        } else {
          // Map backend parquet schema to frontend AnomalyEvent interface
          const mapped = res.map((row: any) => {
            let domain = "OPERATIONAL";
            if (row.anomaly_type === "VOLUME_ANOMALY") domain = "VOLUME";
            
            let model = "MULTIVARIATE";
            if (row.isolation_forest_flag) model = "Isolation Forest";
            if (row.statistical_flag) model = "Statistical / CUSUM";

            return {
              anomaly_id: row.anomaly_id,
              domain: domain,
              model: model,
              feature: row.dataset || "Unknown",
              observed: row.affected_records || 0,
              expected: 0,
              anomaly_score: row.evidence_score || 0,
              severity: row.severity || "UNKNOWN",
              hospital_id: "UNKNOWN", // Parquet doesn't contain hospital_id natively in this old schema
              batch_id: "UNKNOWN",
              run_id: "UNKNOWN",
              detected_at: row.window_date,
              evidence: row.explanation || "No explanation provided"
            };
          });

          resolve(NextResponse.json(mapped));
        }
      });
    });
  } catch (error) {
    console.error("API Error fetching anomalies:", error);
    return NextResponse.json({ error: 'Failed to fetch anomaly data' }, { status: 500 });
  }
}
