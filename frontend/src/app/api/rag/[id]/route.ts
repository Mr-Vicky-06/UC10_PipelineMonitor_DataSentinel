import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  try {
    const params = await context.params;
    const anomalyId = params.id;

    if (!anomalyId || !/^[A-Za-z0-9\-]+$/.test(anomalyId)) {
        return NextResponse.json({ error: 'Invalid anomaly ID format' }, { status: 400 });
    }

    const scriptPath = path.resolve(process.cwd(), '../scripts/rag_history_api.py');
    const projectRoot = path.resolve(process.cwd(), '..');

    const { stdout, stderr } = await execAsync(`python "${scriptPath}" --action detail --id ${anomalyId}`, { cwd: projectRoot });

    if (stderr && !stderr.includes('Warning')) {
      console.warn("Python script stderr:", stderr);
    }

    const data = JSON.parse(stdout);
    
    if (data.status === 'error') {
      if (data.reason.includes("not found")) {
         return NextResponse.json({ error: data.reason }, { status: 404 });
      }
      return NextResponse.json({ error: data.reason }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error(`Failed to load RAG detail for ${context.params}:`, error);
    return NextResponse.json(
      { error: 'Failed to load RAG detail' },
      { status: 500 }
    );
  }
}
