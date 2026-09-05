import React, { useState } from 'react';
import { Activity, ShieldCheck, ShieldAlert, ChevronDown, ChevronUp, Code, Cpu } from 'lucide-react';
import { SSEStreamEvent } from '../types';

interface LiveStreamFeedProps {
  events: SSEStreamEvent[];
  isStreaming: boolean;
}

export const LiveStreamFeed: React.FC<LiveStreamFeedProps> = ({ events, isStreaming }) => {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);
  const [filter, setFilter] = useState<'ALL' | 'APPROVED' | 'BLOCKED'>('ALL');

  const toggleExpand = (idx: number) => {
    setExpandedIndex(expandedIndex === idx ? null : idx);
  };

  const filteredEvents = events.filter((evt) => {
    if (!evt.case_id) return false;
    if (filter === 'APPROVED') return evt.approved === true;
    if (filter === 'BLOCKED') return evt.approved === false;
    return true;
  });

  return (
    <div id="tour-live-feed" className="glass-panel rounded-2xl p-6 lg:p-8 border border-slate-800 flex flex-col min-h-[520px] max-h-[620px] shadow-xl">
      
      {/* Panel Header & Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-800 gap-4">
        <div className="flex items-center space-x-3">
          <div className="relative p-2.5 rounded-xl bg-indigo-600/10 border border-indigo-500/20">
            <Activity className="h-6 w-6 text-indigo-400" />
            {isStreaming && (
              <span className="absolute -top-1 -right-1 h-3 w-3 rounded-full bg-emerald-400 animate-ping" />
            )}
          </div>
          <div>
            <h3 className="text-base lg:text-lg font-bold text-white flex items-center gap-2 font-display">
              Live Case Execution Feed (SSE Stream)
              {isStreaming && (
                <span className="text-[10px] px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-mono font-bold">
                  STREAMING LIVE
                </span>
              )}
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">Real-time LLM classification & guardrail decision pipeline</p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1 bg-slate-900/90 p-1.5 rounded-xl border border-slate-800 text-xs self-start sm:self-auto shrink-0">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === 'ALL' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            All ({events.length})
          </button>
          <button
            onClick={() => setFilter('APPROVED')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === 'APPROVED' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Approved
          </button>
          <button
            onClick={() => setFilter('BLOCKED')}
            className={`px-3 py-1.5 rounded-lg font-medium transition-all ${
              filter === 'BLOCKED' ? 'bg-rose-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            Blocked
          </button>
        </div>
      </div>

      {/* Stream List View */}
      <div className="flex-1 overflow-y-auto mt-5 pr-1 space-y-4">
        {filteredEvents.length === 0 ? (
          <div className="h-full min-h-[320px] flex flex-col items-center justify-center text-center p-8 text-slate-400 bg-slate-950/30 rounded-2xl border border-slate-800/50">
            <div className="p-4 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 mb-4">
              <Cpu className="h-12 w-12 text-indigo-400 animate-pulse" />
            </div>
            <p className="text-base lg:text-lg font-bold text-slate-200 font-display">No live stream events captured yet.</p>
            <p className="text-xs lg:text-sm text-slate-400 mt-2 max-w-md leading-relaxed">
              Click <span className="text-indigo-400 font-bold">"⚡ Run Recovery Batch"</span> above to launch real-time OpenRouter AI case classification and safety evaluations.
            </p>
          </div>
        ) : (
          filteredEvents.map((evt, idx) => {
            const isApproved = evt.approved === true;
            const isExpanded = expandedIndex === idx;
            const confidencePct = evt.confidence ? Math.round(evt.confidence * 100) : 95;

            return (
              <div
                key={idx}
                className={`glass-card rounded-xl p-5 border transition-all duration-200 ${
                  isApproved
                    ? 'border-emerald-500/20 hover:border-emerald-500/40 bg-emerald-950/10'
                    : 'border-rose-500/20 hover:border-rose-500/40 bg-rose-950/10'
                }`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start space-x-3.5">
                    <div className="mt-0.5 shrink-0">
                      {isApproved ? (
                        <ShieldCheck className="h-6 w-6 text-emerald-400" />
                      ) : (
                        <ShieldAlert className="h-6 w-6 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="font-mono text-sm font-bold text-white">
                          Case #{evt.case_id}
                        </span>
                        <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-slate-800 text-slate-300 border border-slate-700">
                          {evt.case_type || 'RECOVERY_CASE'}
                        </span>
                        <span
                          className={`text-[10px] px-2.5 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            isApproved
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {isApproved ? 'APPROVED (AUTO)' : 'BLOCKED (GUARDRAIL)'}
                        </span>
                      </div>

                      <div className="mt-2 text-xs lg:text-sm text-slate-300 font-medium">
                        <span className="text-slate-400">Action: </span>
                        <span className="font-semibold text-indigo-300">{evt.action || evt.route}</span>
                        {evt.amount_recovered !== undefined && evt.amount_recovered > 0 && (
                          <span className="ml-3 text-emerald-400 font-bold">
                            +${evt.amount_recovered.toFixed(2)} Recovered
                          </span>
                        )}
                      </div>

                      {evt.root_cause && (
                        <p className="text-xs lg:text-sm text-slate-400 mt-1.5 italic">
                          "{evt.root_cause}"
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Confidence & Toggle */}
                  <div className="flex flex-col items-end space-y-2.5 shrink-0">
                    <div className="flex items-center space-x-1.5 bg-slate-900/90 px-2.5 py-1 rounded-lg border border-slate-800">
                      <span className="text-[10px] text-slate-400 uppercase font-semibold">AI Conf:</span>
                      <span className="text-xs font-mono font-bold text-purple-400">{confidencePct}%</span>
                    </div>

                    <button
                      onClick={() => toggleExpand(idx)}
                      className="flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300 transition-all font-medium"
                    >
                      <Code className="h-3.5 w-3.5" />
                      <span>{isExpanded ? 'Hide Reasoning' : 'AI Reasoning'}</span>
                      {isExpanded ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </button>
                  </div>
                </div>

                {/* Expanded AI Reasoning JSON Card */}
                {isExpanded && (
                  <div className="mt-4 pt-3 border-t border-slate-800/80 bg-slate-950/90 rounded-xl p-4 font-mono text-xs text-emerald-400 border border-slate-800 overflow-x-auto">
                    <div className="flex items-center justify-between text-slate-400 mb-2 pb-1 border-b border-slate-800 text-[11px]">
                      <span>OpenRouter LLM Output Payload</span>
                      <span className="text-purple-400 font-semibold">openrouter/free</span>
                    </div>
                    <pre>
                      {JSON.stringify(
                        {
                          case_id: evt.case_id,
                          case_type: evt.case_type,
                          root_cause: evt.root_cause || 'Card expired / Soft decline',
                          recommended_action: evt.action,
                          confidence: evt.confidence || 0.95,
                          decision_route: evt.route || (isApproved ? 'AUTO_EXECUTE' : 'HUMAN_REVIEW'),
                          guardrail_passed: isApproved,
                          reason: evt.reason || 'Guardrail thresholds evaluated against financial risk policy.',
                        },
                        null,
                        2
                      )}
                    </pre>
                  </div>
                )}

              </div>
            );
          })
        )}
      </div>

    </div>
  );
};
