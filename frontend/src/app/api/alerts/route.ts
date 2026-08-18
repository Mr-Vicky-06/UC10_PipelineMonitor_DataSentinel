import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import readline from 'readline';

export async function GET() {
  try {
    const alertsPath = path.resolve(process.cwd(), '../outputs/action/alerts.jsonl');
    
    if (!fs.existsSync(alertsPath)) {
      return NextResponse.json([]);
    }

    const alerts = [];
    const fileStream = fs.createReadStream(alertsPath);
    const rl = readline.createInterface({
      input: fileStream,
      crlfDelay: Infinity
    });

    for await (const line of rl) {
      if (line.trim()) {
        try {
          const parsed = JSON.parse(line);
          if (parsed.created_at) {
            // Convert seconds to ISO string
            parsed.detected_at = new Date(parsed.created_at * 1000).toISOString();
          }
          alerts.push(parsed);
        } catch (e) {
          // ignore malformed lines
        }
      }
    }
    
    // Sort by most recent first
    alerts.sort((a, b) => new Date(b.detected_at).getTime() - new Date(a.detected_at).getTime());

    return NextResponse.json(alerts.slice(0, 50));
  } catch (error) {
    console.error("API Error fetching alerts:", error);
    return NextResponse.json({ error: 'Failed to fetch alerts data' }, { status: 500 });
  }
}
