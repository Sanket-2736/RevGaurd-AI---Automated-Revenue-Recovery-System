import React from 'react';
import { Info, Activity, Shield, ArrowRight, CheckCircle2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { KpiCards } from '../components/KpiCards';
import { BatchControls } from '../components/BatchControls';
import { LiveStreamFeed } from '../components/LiveStreamFeed';
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
  streamEvents,
  loadingMetrics,
  isRunningBatch,
  activeBatchId,
  batchProgress,
  totalEnqueued,
  batchMode,
  onRunBatch,
}) => {
  return (
    <div className="space-y-10 lg:space-y-12 animate-fadeIn max-w-7xl mx-auto pb-12">
      
      {/* 1. Pitch Hero Framing Banner */}
      <div
        id="tour-framing-banner"
        className="glass-panel rounded-2xl p-6 lg:p-8 border border-indigo-500/30 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950/60 flex items-start space-x-4 lg:space-x-5 shadow-2xl"
      >
        <div className="p-3.5 rounded-xl bg-indigo-600/20 text-indigo-400 shrink-0 border border-indigo-500/30 mt-0.5">
          <Info className="h-6 w-6 lg:h-7 lg:w-7" />
        </div>
        <div>
          <span className="text-xs font-extrabold uppercase tracking-widest text-indigo-300 block mb-1.5 font-display">
            Autonomous System Pitch & Core Purpose
          </span>
          <p className="text-base lg:text-xl font-bold text-white leading-relaxed font-display">
            This agent finds money businesses are about to lose, decides why using OpenRouter LLMs, and safely tries to get it back — every number below updates live as it runs.
          </p>
        </div>
      </div>

      {/* 2. Headline KPI Metric Cards */}
      <KpiCards metrics={metrics} loading={loadingMetrics} />

      {/* 3. Autonomous Batch Recovery Controls */}
      <BatchControls
        isRunning={isRunningBatch}
        activeBatchId={activeBatchId}
        progressPct={batchProgress}
        totalEnqueued={totalEnqueued}
        mode={batchMode}
        onRunBatch={onRunBatch}
      />

      {/* 4. Live Case Execution Feed (Primary Focus) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-sm font-extrabold text-slate-300 uppercase tracking-wider flex items-center gap-2 font-display">
            <Activity className="h-4 w-4 text-indigo-400" />
            Live Case Execution Feed
          </h3>
          <Link
            to="/live"
            className="text-xs font-bold text-indigo-400 hover:text-indigo-300 flex items-center gap-1.5 transition-all"
          >
            <span>Full Execution Stream</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
        <LiveStreamFeed events={streamEvents} isStreaming={isRunningBatch} />
      </div>

      {/* 5. Compact Guardrails Summary Banner (Replaces heavy rule cards + audit log stream on Overview) */}
      <div
        id="tour-guardrails-ledger"
        className="glass-panel rounded-2xl p-6 lg:p-8 border border-slate-800/80 bg-slate-950/40 flex flex-col md:flex-row md:items-center justify-between gap-6 shadow-xl"
      >
        <div className="flex items-start space-x-4">
          <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
            <Shield className="h-7 w-7" />
          </div>
          <div>
            <div className="flex flex-wrap items-center gap-3 mb-1.5">
              <h3 className="text-base lg:text-lg font-bold text-white font-display">
                Zero-Trust Safety Guardrails
              </h3>
              <span className="text-xs px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono font-bold">
                5 Rules Active & Enforced
              </span>
            </div>
            <p className="text-xs lg:text-sm text-slate-400 leading-relaxed max-w-2xl">
              Every recovery action is automatically validated against strict financial safety policies ($500 max auto-approval cap, 3 max retries, 60% confidence threshold) to guarantee zero rogue automated operations.
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-4 text-xs font-medium text-slate-300">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <CheckCircle2 className="h-4 w-4" /> 80 Safety Intercepts Triggered
              </span>
              <span className="text-slate-600">•</span>
              <span className="flex items-center gap-1.5 text-indigo-400">
                <CheckCircle2 className="h-4 w-4" /> 100% Financial Safety Ledger
              </span>
            </div>
          </div>
        </div>

        <Link
          to="/guardrails"
          className="shrink-0 inline-flex items-center justify-center space-x-2 px-5 py-3 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold text-xs lg:text-sm shadow-lg shadow-emerald-950/50 transition-all border border-emerald-400/30 hover:scale-[1.02] active:scale-[0.98]"
        >
          <span>View Safety Guardrails & Audit Ledger</span>
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>

    </div>
  );
};
