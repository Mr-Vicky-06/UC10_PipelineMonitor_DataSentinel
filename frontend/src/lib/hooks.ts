import { useQuery } from '@tanstack/react-query';
import { PipelineRun, AlertEvent } from './types';

export function usePipelines() {
  return useQuery<PipelineRun[]>({
    queryKey: ['pipelines'],
    queryFn: async () => {
      const response = await fetch('/api/pipelines');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    refetchInterval: 5000,
  });
}

export function useAlerts() {
  return useQuery<AlertEvent[]>({
    queryKey: ['alerts'],
    queryFn: async () => {
      const response = await fetch('/api/alerts');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    refetchInterval: 5000,
  });
}

export function useDataQuality() {
  return useQuery<any[]>({
    queryKey: ['data-quality'],
    queryFn: async () => {
      const response = await fetch('/api/data-quality');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    refetchInterval: 5000,
  });
}

export function useAnomalies() {
  return useQuery<any[]>({
    queryKey: ['anomalies'],
    queryFn: async () => {
      const response = await fetch('/api/anomalies');
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      return response.json();
    },
    refetchInterval: 5000,
  });
}
