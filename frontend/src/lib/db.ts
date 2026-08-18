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

const dbs: Record<string, duckdb.Database> = {};

function getDb(name: keyof typeof dbPaths): duckdb.Database {
  if (!dbs[name]) {
    dbs[name] = new duckdb.Database(dbPaths[name], {
      'access_mode': 'READ_ONLY',
    });
  }
  return dbs[name];
}

export function queryDb<T>(dbName: keyof typeof dbPaths, query: string, params: any[] = []): Promise<T[]> {
  return new Promise((resolve, reject) => {
    const db = getDb(dbName);
    const connection = db.connect();
    
    connection.all(query, ...params, (err: any, res: any) => {
      connection.close();
      if (err) {
        reject(err);
      } else {
        resolve(res as T[]);
      }
    });
  });
}


