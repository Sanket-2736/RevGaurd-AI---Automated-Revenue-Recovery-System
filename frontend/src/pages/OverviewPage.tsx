import React from 'react';
import { Info, Activity, Shield, ArrowRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { KpiCards } from '../components/KpiCards';
import { BatchControls } from '../components/BatchControls';
import { LiveStreamFeed } from '../components/LiveStreamFeed';
import { GuardrailLedger } from '../components/GuardrailLedger';
import { MetricsResponse, RecoveryCase, GuardrailEvent, SSEStreamEvent } from '../types';

interface OverviewPageProps {
  metrics: MetricsResponse | null;
  cases: RecoveryCase[];
  events: GuardrailEvent[];
  streamEvents: SSEStreamEvent[];
  loadingMetrics: boolean;
  loadingCases: boolean;
  loadingEvents: boolean;
  isRunningBatch: boolean;
  activeBatchId: string | null;
  batchProgress: number;
  totalEnqueued: number;
  batchMode?: string;
  onRunBatch: (limit: number) => void;
}

export const OverviewPage: React.FC<OverviewPageProps> = ({
  metrics,
  events,
  streamEvents,
  loadingMetrics,
  loadingEvents,
  isRunningBatch,
  activeBatchId,
  batchProgress,
  totalEnqueued,
  batchMode,
  onRunBatch,
}) => {
  return (
    <div className="space-y-8 animate-fadeIn">
      
      {/* Pitch Hero Framing Banner */}
      <div
        id="tour-framing-banner"
        className="glass-panel rounded-2xl p-6 border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950/60 flex items-start space-x-4 shadow-xl"
      >
        <div className="p-3 rounded-xl bg-indigo-600/20 text-indigo-400 shrink-0 border border-indigo-500/30 mt-0.5">
          <Info className="h-6 w-6" />
        </div>
        <div>
          <span className="text-xs font-extrabold uppercase tracking-widest text-indigo-300 block mb-1 font-display">
            Autonomous System Pitch & Core Purpose
          </span>
          <p className="text-base lg:text-lg font-bold text-white leading-snug font-display">
            This agent finds money businesses are about to lose, decides why using OpenRouter LLMs, and safely tries to get it back — every number below updates live as it runs.
          </p>
        </div>
      </div>

      {/* Headline KPI Metric Cards (Scaled Up to 48px Display Scale) */}
      <KpiCards metrics={metrics} loading={loadingMetrics} />

      {/* Prominent Batch Controls (Defaults to 381 Cases) */}
      <BatchControls
        isRunning={isRunningBatch}
        activeBatchId={activeBatchId}
        progressPct={batchProgress}
        totalEnqueued={totalEnqueued}
        mode={batchMode}
        onRunBatch={onRunBatch}
      />

      {/* Overview Snapshot Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Live Case Stream Preview */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2 font-display">
              <Activity className="h-4 w-4 text-indigo-400" />
              Live Case Execution Feed
            </h3>
            <Link
              to="/live"
              className="text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 transition-all"
            >
              <span>View Full Stream</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <LiveStreamFeed events={streamEvents} isStreaming={isRunningBatch} />
        </div>

        {/* Guardrail Safety Ledger Preview */}
        <div className="lg:col-span-1">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2 font-display">
              <Shield className="h-4 w-4 text-emerald-400" />
              Guardrail Audit Trail
            </h3>
            <Link
              to="/guardrails"
              className="text-xs font-bold text-emerald-400 hover:text-emerald-300 flex items-center gap-1 transition-all"
            >
              <span>View Full Ledger</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <GuardrailLedger events={events} loading={loadingEvents} />
        </div>

      </div>

    </div>
  );
};
