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
    const parquetPath = path.resolve(process.cwd(), '../outputs/anomaly/dq_results.parquet');
    const db = new duckdb.Database(':memory:');
    
    return new Promise<NextResponse>((resolve, reject) => {
      const connection = db.connect();
      
      const query = `
        SELECT * FROM read_parquet('${parquetPath}')
        ORDER BY timestamp DESC
        LIMIT 100;
      `;
      
      connection.all(query, (err: any, res: any) => {
        connection.close();
        if (err) {
          // If the file doesn't exist or is invalid, just return empty array
          console.warn("Failed to read parquet:", err.message);
          resolve(NextResponse.json([]));
        } else {
          resolve(NextResponse.json(res));
        }
      });
    });
  } catch (error) {
    console.error("API Error fetching data quality:", error);
    return NextResponse.json({ error: 'Failed to fetch data quality data' }, { status: 500 });
  }
}
