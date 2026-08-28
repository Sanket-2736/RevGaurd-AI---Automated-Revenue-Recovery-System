import { MetricsResponse, RecoveryCase, GuardrailEvent, BatchRunResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  if (!res.ok) throw new Error('Backend health check failed');
  return res.json();
}

export async function fetchMetrics(): Promise<MetricsResponse> {
  const res = await fetch(`${API_BASE_URL}/api/metrics`);
  if (!res.ok) throw new Error('Failed to fetch live metrics');
  return res.json();
}

export async function fetchCases(status?: string, limit = 100): Promise<RecoveryCase[]> {
  const url = new URL(`${API_BASE_URL}/api/cases`);
  url.searchParams.append('limit', limit.toString());
  if (status) url.searchParams.append('status', status);

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch recovery cases');
  return res.json();
}

export async function fetchGuardrailEvents(limit = 100): Promise<GuardrailEvent[]> {
  const url = new URL(`${API_BASE_URL}/api/events`);
  url.searchParams.append('limit', limit.toString());

  const res = await fetch(url.toString());
  if (!res.ok) throw new Error('Failed to fetch guardrail events');
  return res.json();
}

export async function runBatch(limit: number): Promise<BatchRunResponse> {
  const res = await fetch(`${API_BASE_URL}/api/batch/run?limit=${limit}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to initiate batch run');
  return res.json();
}

export async function triggerIngest(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/ingest/all`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to ingest synthetic data');
  return res.json();
}

export async function triggerDetection(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/detection/run`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to run risk detection');
  return res.json();
}

export async function resetDemoState(): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/api/reset`, { method: 'POST' });
  if (!res.ok) {
    // Fallback: try sequential calls
    await triggerIngest();
    return await triggerDetection();
  }
  return res.json();
}

export function getSSEStreamUrl(batchId: string): string {
  return `${API_BASE_URL}/api/batch/${batchId}/stream`;
}
