import { useState, useEffect, useRef } from 'react';
import { Routes, Route, useLocation } from 'react-router-dom';
import { driver } from 'driver.js';

import { Sidebar } from './components/Sidebar';
import { TopHeader } from './components/TopHeader';
import { DemoGuideModal } from './components/DemoGuideModal';

import { OverviewPage } from './pages/OverviewPage';
import { LiveStreamPage } from './pages/LiveStreamPage';
import { GuardrailsPage } from './pages/GuardrailsPage';
import { CasesPage } from './pages/CasesPage';
import { AnalyticsPage } from './pages/AnalyticsPage';

import {
  fetchHealth,
  fetchMetrics,
  fetchCases,
  fetchGuardrailEvents,
  runBatch,
  resetDemoState,
  triggerIngest,
  triggerDetection,
  getSSEStreamUrl,
  getBatchStatus,
} from './api';

import { MetricsResponse, RecoveryCase, GuardrailEvent, SSEStreamEvent } from './types';

export default function App() {
  const location = useLocation();

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [cases, setCases] = useState<RecoveryCase[]>([]);
  const [events, setEvents] = useState<GuardrailEvent[]>([]);
  const [streamEvents, setStreamEvents] = useState<SSEStreamEvent[]>([]);

  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(true);
  const [loadingCases, setLoadingCases] = useState<boolean>(true);
  const [loadingEvents, setLoadingEvents] = useState<boolean>(true);
  const [isResetting, setIsResetting] = useState<boolean>(false);

  // Batch execution state
  const [isRunningBatch, setIsRunningBatch] = useState<boolean>(false);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [batchProgress, setBatchProgress] = useState<number>(0);
  const [totalEnqueued, setTotalEnqueued] = useState<number>(0);
  const [batchMode, setBatchMode] = useState<string | undefined>(undefined);

  const [isGuideOpen, setIsGuideOpen] = useState<boolean>(false);

  const sseRef = useRef<EventSource | null>(null);

  // Derive current page title from route
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/live':
        return 'Live Case Execution Stream (SSE)';
      case '/guardrails':
        return 'Safety Guardrails Audit Ledger';
      case '/cases':
        return 'Detected Cases Database';
      case '/analytics':
        return 'Risk Category Accuracy & Benchmarks';
      default:
        return 'Overview — Autonomous Recovery Pitch';
    }
  };

  // Fetch metrics & database state
  const refreshAllData = async () => {
    try {
      setLoadingMetrics(true);
      const [h, m, c, e] = await Promise.allSettled([
        fetchHealth(),
        fetchMetrics(),
        fetchCases(),
        fetchGuardrailEvents(),
      ]);

      if (h.status === 'fulfilled') setIsConnected(true);
      else setIsConnected(false);

      if (m.status === 'fulfilled') setMetrics(m.value);
      if (c.status === 'fulfilled') setCases(c.value);
      if (e.status === 'fulfilled') setEvents(e.value);
    } catch (err) {
      console.error('Error fetching data:', err);
      setIsConnected(false);
    } finally {
      setLoadingMetrics(false);
      setLoadingCases(false);
      setLoadingEvents(false);
    }
  };

  useEffect(() => {
    refreshAllData();
    const interval = setInterval(refreshAllData, 10000);
    return () => clearInterval(interval);
  }, []);

  // Authoritative Batch Status Polling Effect
  useEffect(() => {
    if (!activeBatchId || !isRunningBatch) {
      return;
    }

    const pollBatchStatus = async () => {
      try {
        const status = await getBatchStatus(activeBatchId);
        console.log(`[BATCH STATUS POLL] ${activeBatchId}`, status);

        if (typeof status.progress_pct === 'number') {
          setBatchProgress(status.progress_pct);
        }

        if (status.is_finished) {
          console.log(`[BATCH COMPLETED] Batch ${activeBatchId} reported is_finished=true`);
          setBatchProgress(100);
          setIsRunningBatch(false);

          if (sseRef.current) {
            sseRef.current.close();
            sseRef.current = null;
          }

          await refreshAllData();
        }
      } catch (err) {
        console.warn(`[BATCH STATUS POLL ERROR] Failed to poll ${activeBatchId}:`, err);
      }
    };

    pollBatchStatus();
    const interval = setInterval(pollBatchStatus, 1000);
    return () => clearInterval(interval);
  }, [activeBatchId, isRunningBatch]);

  // Guided Tour Launcher using driver.js
  const startGuidedTour = () => {
    const driverObj = driver({
      showProgress: true,
      animate: true,
      steps: [
        {
          element: '#tour-framing-banner',
          popover: {
            title: '1. One-Sentence System Pitch',
            description:
              'This agent finds money businesses are about to lose, decides why using OpenRouter LLMs, and safely tries to get it back — every number below updates live as it runs.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '#tour-kpi-cards',
          popover: {
            title: '2. Real-Time Financial Metrics Bar',
            description:
              'Tracks total revenue at risk ($376,590.00), cash successfully recovered ($269,435.19 / 71.5%), 96.1% AI ground truth accuracy, and 80 safety guardrail intercepts.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '#tour-batch-controls',
          popover: {
            title: '3. Autonomous Recovery Controls',
            description:
              'Defaults to 381 cases (the complete dataset). Click "⚡ Run Recovery Batch" to launch real-time OpenRouter LLM classification and Guardrail evaluations.',
            side: 'bottom',
            align: 'start',
          },
        },
        {
          element: '#tour-live-feed',
          popover: {
            title: '4. Live Case Execution Feed (SSE Stream)',
            description:
              'Streams real-time case evaluations as workers process them. Click "AI Reasoning" on any card to view full OpenRouter LLM JSON output cards.',
            side: 'top',
            align: 'start',
          },
        },
        {
          element: '#tour-guardrails-ledger',
          popover: {
            title: '5. Zero-Trust Safety Guardrail Intercepts',
            description:
              'Every case is checked against 5 safety rules. Red blocks are a safety feature (protecting high-value transactions > $500 from unauthorized automated retries).',
            side: 'left',
            align: 'start',
          },
        },
      ],
      onDestroyed: () => {
        localStorage.setItem('revguard_tour_seen', 'true');
      },
    });

    driverObj.drive();
  };

  // Trigger tour on first load
  useEffect(() => {
    const hasSeen = localStorage.getItem('revguard_tour_seen');
    if (!hasSeen) {
      const timer = setTimeout(() => {
        startGuidedTour();
      }, 800);
      return () => clearTimeout(timer);
    }
  }, []);

  // Handle batch run trigger
  const handleRunBatch = async (limit: number) => {
    try {
      console.log(`[App handleRunBatch] Initiating batch run with limit=${limit}`);
      setIsRunningBatch(true);
      setBatchProgress(0);
      setStreamEvents([]);

      const res = await runBatch(limit);
      console.log(`[App handleRunBatch] Response from backend: batch_id=${res.batch_id}, total_enqueued=${res.total_enqueued}, mode=${res.mode}`);

      if (!res.batch_id || res.total_enqueued === 0) {
        console.warn(`[App handleRunBatch] 0 cases enqueued for batch; triggering demo state reset and retrying limit=${limit}...`);
        await resetDemoState();
        const retryRes = await runBatch(limit);
        console.log(`[App handleRunBatch Retry] Response: batch_id=${retryRes.batch_id}, total_enqueued=${retryRes.total_enqueued}`);
        if (retryRes.batch_id) {
          setActiveBatchId(retryRes.batch_id);
          setTotalEnqueued(retryRes.total_enqueued);
          setBatchMode(retryRes.mode);
          startSSEStream(retryRes.batch_id, retryRes.total_enqueued);
        } else {
          setIsRunningBatch(false);
        }
        return;
      }

      setActiveBatchId(res.batch_id);
      setTotalEnqueued(res.total_enqueued);
      setBatchMode(res.mode);

      startSSEStream(res.batch_id, res.total_enqueued);
    } catch (err) {
      console.error('[App handleRunBatch Error] Error starting batch:', err);
      setIsRunningBatch(false);
    }
  };

  // SSE Stream handler
  const startSSEStream = (batchId: string, batchTotal: number) => {
    if (sseRef.current) {
      sseRef.current.close();
    }

    const streamUrl = getSSEStreamUrl(batchId);
    const es = new EventSource(streamUrl);
    sseRef.current = es;

    es.onopen = () => {
      console.log('[SSE OPEN]', batchId);
    };

    es.onmessage = (event) => {
      console.log('[SSE RAW MESSAGE]', event.data);
      try {
        const data: SSEStreamEvent = JSON.parse(event.data);
        console.log('[SSE PARSED DATA]', data);

        if (data.is_finished) {
          console.log('[SSE FINISHED]', batchId);
          setBatchProgress(100);
          setIsRunningBatch(false);
          refreshAllData();
          es.close();
          return;
        }

        if (data.case_id) {
          setStreamEvents((prev) => [data, ...prev]);
          setBatchProgress((prev) =>
            Math.min(prev + (100 / (batchTotal || 381)), 99.9)
          );
          refreshAllData();
        }
      } catch (err) {
        console.error('[SSE PARSE ERROR]', err);
      }
    };

    es.onerror = (err) => {
      console.warn('[SSE ERROR]', batchId, err);
      // EventSource automatically attempts reconnection on transient network issues.
      // Connection is closed cleanly when data.is_finished is received.
    };
  };

  // Handle Reset Demo State
  const handleReset = async () => {
    try {
      setIsResetting(true);
      await resetDemoState();
      setStreamEvents([]);
      setActiveBatchId(null);
      setBatchProgress(0);
      await refreshAllData();
    } catch (err) {
      console.error('Failed to reset demo:', err);
    } finally {
      setIsResetting(false);
    }
  };

  const hasProcessedCases = streamEvents.length > 0 || (metrics?.total_recovered ?? 0) > 0;

  return (
    <div className="flex min-h-screen bg-[#090D16] text-slate-100 font-sans selection:bg-indigo-600 selection:text-white">
      
      {/* Persistent Left Navigation Sidebar */}
      <Sidebar
        isConnected={isConnected}
        isRunningBatch={isRunningBatch}
        progressPct={batchProgress}
        hasProcessedCases={hasProcessedCases}
      />

      {/* Main Workspace Layout */}
      <div className="flex-1 flex flex-col min-w-0">
        
        {/* Top Command Header */}
        <TopHeader
          pageTitle={getPageTitle()}
          isResetting={isResetting}
          onReset={handleReset}
          onIngest={triggerIngest}
          onDetect={triggerDetection}
          onOpenGuide={() => setIsGuideOpen(true)}
          onStartTour={startGuidedTour}
        />

        {/* Page Content View Router */}
        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto">
          <Routes>
            <Route
              path="/"
              element={
                <OverviewPage
                  metrics={metrics}
                  cases={cases}
                  events={events}
                  streamEvents={streamEvents}
                  loadingMetrics={loadingMetrics}
                  loadingCases={loadingCases}
                  loadingEvents={loadingEvents}
                  isRunningBatch={isRunningBatch}
                  activeBatchId={activeBatchId}
                  batchProgress={batchProgress}
                  totalEnqueued={totalEnqueued}
                  batchMode={batchMode}
                  onRunBatch={handleRunBatch}
                />
              }
            />
            <Route
              path="/live"
              element={
                <LiveStreamPage
                  streamEvents={streamEvents}
                  isRunningBatch={isRunningBatch}
                  activeBatchId={activeBatchId}
                  batchProgress={batchProgress}
                  totalEnqueued={totalEnqueued}
                  batchMode={batchMode}
                  onRunBatch={handleRunBatch}
                />
              }
            />
            <Route
              path="/guardrails"
              element={
                <GuardrailsPage events={events} loadingEvents={loadingEvents} />
              }
            />
            <Route
              path="/cases"
              element={
                <CasesPage cases={cases} loadingCases={loadingCases} onRefresh={refreshAllData} />
              }
            />
            <Route
              path="/analytics"
              element={
                <AnalyticsPage metrics={metrics} />
              }
            />
          </Routes>
        </main>

      </div>

      {/* Presenter Guide Cheat-Sheet Modal */}
      <DemoGuideModal isOpen={isGuideOpen} onClose={() => setIsGuideOpen(false)} />

    </div>
  );
}
