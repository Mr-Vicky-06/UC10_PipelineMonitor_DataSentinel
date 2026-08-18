'use client';

import { useMemo } from 'react';
import { 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer 
} from 'recharts';
import { format } from 'date-fns';
import { PipelineRun } from '@/lib/types';

interface VolumeChartProps {
  data: PipelineRun[];
}

export function VolumeChart({ data }: VolumeChartProps) {
  const chartData = useMemo(() => {
    if (!data || data.length === 0) return [];
    
    // Group runs by hour (or whatever bucket makes sense)
    // For this example, let's just show records_in for the last N runs to keep it simple and live
    return data.slice().reverse().map(run => ({
      name: run.run_id.split('-')[0], // Short ID
      records: run.records_in || 0,
      errors: run.errors || 0,
      violations: run.dq_violations || 0
    })).slice(-20); // Last 20 runs
  }, [data]);

  if (chartData.length === 0) {
    return <div className="h-full w-full flex items-center justify-center text-secondary text-sm">No volume data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height="100%">
      <AreaChart
        data={chartData}
        margin={{ top: 10, right: 10, left: 0, bottom: 0 }}
      >
        <defs>
          <linearGradient id="colorRecords" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
          </linearGradient>
          <linearGradient id="colorErrors" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#334155" opacity={0.2} />
        <XAxis 
          dataKey="name" 
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 10, fill: '#64748b' }}
          dy={10}
        />
        <YAxis 
          axisLine={false}
          tickLine={false}
          tick={{ fontSize: 10, fill: '#64748b' }}
          tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(1)}k` : val.toString()}
        />
        <Tooltip 
          contentStyle={{ backgroundColor: '#ffffff', borderRadius: '6px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
          labelStyle={{ color: '#0f172a', fontWeight: 600, marginBottom: '4px' }}
        />
        <Area 
          type="monotone" 
          dataKey="records" 
          stroke="#3b82f6" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorRecords)" 
          name="Records Processed"
        />
        <Area 
          type="monotone" 
          dataKey="errors" 
          stroke="#ef4444" 
          strokeWidth={2}
          fillOpacity={1} 
          fill="url(#colorErrors)" 
          name="Errors"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
