import duckdb from 'duckdb';
import path from 'path';

// Fix for BigInt serialization in Next.js JSON responses
if (!(BigInt.prototype as any).toJSON) {
  (BigInt.prototype as any).toJSON = function () {
    return Number(this);
  };
}

const dbPaths = {
  telemetry: path.resolve(process.cwd(), '../outputs/pipeline_workspace/pipeline_telemetry.duckdb'),
  processed_claims: path.resolve(process.cwd(), '../outputs/business_rules/processed_claims.duckdb'),
  metrics: path.resolve(process.cwd(), '../outputs/ml/metrics_repository.duckdb'),
};

export function queryDb<T>(dbName: keyof typeof dbPaths, query: string, params: any[] = []): Promise<T[]> {
  return new Promise((resolve, reject) => {
    // Instantiate a new db connection each time to avoid locking the file from Python writers
    const db = new duckdb.Database(dbPaths[dbName], {
      'access_mode': 'READ_ONLY',
    });
    const connection = db.connect();
    
    connection.all(query, ...params, (err: any, res: any) => {
      // Close both connection and db to release the Windows file handle
      connection.close();
      db.close();
      
      if (err) {
        reject(err);
      } else {
        resolve(res as T[]);
      }
    });
  });
}


