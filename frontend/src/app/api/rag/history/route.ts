import { NextResponse } from 'next/server';
import { exec } from 'child_process';
import { promisify } from 'util';
import path from 'path';

const execAsync = promisify(exec);

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = parseInt(searchParams.get('limit') || '50');
    const offset = parseInt(searchParams.get('offset') || '0');

    // Resolve path to python script
    const scriptPath = path.resolve(process.cwd(), '../scripts/rag_history_api.py');
    const projectRoot = path.resolve(process.cwd(), '..');

    // We execute the python script in the project root to access 'outputs' folder correctly
    const { stdout, stderr } = await execAsync(`python "${scriptPath}" --action history --limit ${limit} --offset ${offset}`, { cwd: projectRoot });

    if (stderr && !stderr.includes('Warning')) {
      console.warn("Python script stderr:", stderr);
    }

    const data = JSON.parse(stdout);
    
    if (data.status === 'error') {
      return NextResponse.json({ error: data.reason }, { status: 500 });
    }

    return NextResponse.json(data);
  } catch (error) {
    console.error('Failed to load RAG history:', error);
    return NextResponse.json(
      { error: 'Failed to load RAG history' },
      { status: 500 }
    );
  }
}
