import { MetricsResponse, RecoveryCase, GuardrailEvent, BatchRunResponse } from './types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Universal fetch wrapper with detailed request/response/error logging.
 */
async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`;
  const method = options?.method || 'GET';
  const body = options?.body ? options.body.toString() : '';

  console.log(`[API Request] ${method} ${url}`, body ? `Payload: ${body}` : '');

  try {
    const res = await fetch(url, options);
    const contentType = res.headers.get('content-type') || '';
    let responseData: any;

    if (contentType.includes('application/json')) {
      responseData = await res.json();
    } else {
      responseData = await res.text();
    }

    if (!res.ok) {
      const errorMsg = `[API Error] ${method} ${url} failed with status ${res.status}: ${
        typeof responseData === 'object' ? JSON.stringify(responseData) : responseData
      }`;
      console.error(errorMsg);
      throw new Error(errorMsg);
    }

    console.log(`[API Response] ${method} ${url} (Status ${res.status})`, responseData);
    return responseData as T;
  } catch (err: any) {
    console.error(`[API Network/Execution Error] ${method} ${url}:`, err.message || err);
    throw err;
  }
}

export async function fetchHealth(): Promise<{ status: string }> {
  return apiFetch<{ status: string }>('/health');
}

export async function fetchMetrics(): Promise<MetricsResponse> {
  return apiFetch<MetricsResponse>('/api/metrics');
}

export async function fetchCases(status?: string, limit = 100): Promise<RecoveryCase[]> {
  const url = new URL(`${API_BASE_URL}/api/cases`);
  url.searchParams.append('limit', limit.toString());
  if (status) url.searchParams.append('status', status);

  return apiFetch<RecoveryCase[]>(url.toString());
}

export async function fetchGuardrailEvents(limit = 100): Promise<GuardrailEvent[]> {
  const url = new URL(`${API_BASE_URL}/api/events`);
  url.searchParams.append('limit', limit.toString());

  return apiFetch<GuardrailEvent[]>(url.toString());
}

export async function runBatch(limit: number): Promise<BatchRunResponse> {
  console.log(`[API runBatch Trigger] Incoming limit parameter: ${limit} (type: ${typeof limit})`);
  return apiFetch<BatchRunResponse>(`/api/batch/run?limit=${limit}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
}

export async function triggerIngest(): Promise<any> {
  return apiFetch<any>('/api/ingest/all', { method: 'POST' });
}

export async function triggerDetection(): Promise<any> {
  return apiFetch<any>('/api/detection/run', { method: 'POST' });
}

export async function resetDemoState(): Promise<any> {
  try {
    return await apiFetch<any>('/api/reset', { method: 'POST' });
  } catch (err) {
    console.warn('[API resetDemoState Fallback] /api/reset endpoint failed, executing sequential fallback calls...');
    await triggerIngest();
    return await triggerDetection();
  }
}

export function getSSEStreamUrl(batchId: string): string {
  const streamUrl = `${API_BASE_URL}/api/batch/${batchId}/stream`;
  console.log(`[API getSSEStreamUrl] Derived SSE stream URL: ${streamUrl}`);
  return streamUrl;
}
