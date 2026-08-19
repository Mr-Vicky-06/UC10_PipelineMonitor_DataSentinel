import { NextResponse } from 'next/server';

export async function GET(request: Request, context: { params: Promise<{ id: string }> }) {
  const params = await context.params;
  // Try to resolve RCA from the RAG engine.
  // Currently, Gemini credentials are not configured and we cannot deterministically
  // map alert_id to an anomaly_id for historical parquet lookups.
  // As per DataSentinel architecture requirements, we return 503 so the UI
  // gracefully degrades to "RAG Analysis Unavailable" while keeping Evidence visible.
  
  return NextResponse.json(
    { 
      available: false, 
      reason: 'RAG provider is not configured for this environment'
    },
    { status: 503 }
  );
}
