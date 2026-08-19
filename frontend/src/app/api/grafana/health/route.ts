import { NextResponse } from 'next/server';

export async function GET() {
  const grafanaUrl = process.env.GRAFANA_INTERNAL_URL || process.env.NEXT_PUBLIC_GRAFANA_BASE_URL || 'http://localhost:3002';
  try {
    const res = await fetch(`${grafanaUrl}/api/health`, { method: 'GET', cache: 'no-store' });
    if (res.ok) {
      return NextResponse.json({ status: 'ok' });
    }
    return NextResponse.json({ status: 'unavailable' }, { status: 503 });
  } catch (err) {
    return NextResponse.json({ status: 'unavailable' }, { status: 503 });
  }
}
