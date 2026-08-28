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
    <div id="tour-live-feed" className="glass-panel rounded-2xl p-5 border border-gray-800 flex flex-col h-[520px]">
      
      {/* Panel Header & Filters */}
      <div className="flex items-center justify-between pb-4 border-b border-gray-800">
        <div className="flex items-center space-x-2">
          <div className="relative">
            <Activity className="h-5 w-5 text-indigo-400" />
            {isStreaming && (
              <span className="absolute -top-1 -right-1 h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping" />
            )}
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              Live Case Execution Feed (SSE Stream)
              {isStreaming && (
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
                  STREAMING LIVE
                </span>
              )}
            </h3>
            <p className="text-[11px] text-gray-400">Real-time LLM classification & guardrail decision pipeline</p>
          </div>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center space-x-1 bg-gray-900/90 p-1 rounded-xl border border-gray-800 text-xs">
          <button
            onClick={() => setFilter('ALL')}
            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
              filter === 'ALL' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            All ({events.length})
          </button>
          <button
            onClick={() => setFilter('APPROVED')}
            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
              filter === 'APPROVED' ? 'bg-emerald-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Approved
          </button>
          <button
            onClick={() => setFilter('BLOCKED')}
            className={`px-2.5 py-1 rounded-lg font-medium transition-all ${
              filter === 'BLOCKED' ? 'bg-rose-600 text-white' : 'text-gray-400 hover:text-gray-200'
            }`}
          >
            Blocked
          </button>
        </div>
      </div>

      {/* Stream List View */}
      <div className="flex-1 overflow-y-auto mt-4 pr-1 space-y-3">
        {filteredEvents.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-gray-500">
            <Cpu className="h-10 w-10 text-gray-700 mb-2 animate-pulse" />
            <p className="text-sm font-medium">No live stream events captured yet.</p>
            <p className="text-xs text-gray-600 mt-1">
              Click <span className="text-indigo-400 font-semibold">"⚡ Run Recovery Batch"</span> above to trigger real-time case evaluations.
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
                className={`glass-card rounded-xl p-4 border transition-all duration-200 ${
                  isApproved
                    ? 'border-emerald-500/20 hover:border-emerald-500/40 bg-emerald-950/10'
                    : 'border-rose-500/20 hover:border-rose-500/40 bg-rose-950/10'
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5">
                      {isApproved ? (
                        <ShieldCheck className="h-5 w-5 text-emerald-400" />
                      ) : (
                        <ShieldAlert className="h-5 w-5 text-rose-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono text-xs font-bold text-white">
                          Case #{evt.case_id}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold uppercase tracking-wider bg-gray-800 text-gray-300 border border-gray-700">
                          {evt.case_type || 'RECOVERY_CASE'}
                        </span>
                        <span
                          className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${
                            isApproved
                              ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                              : 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          }`}
                        >
                          {isApproved ? 'APPROVED (AUTO)' : 'BLOCKED (GUARDRAIL)'}
                        </span>
                      </div>

                      <div className="mt-1 text-xs text-gray-300 font-medium">
                        <span className="text-gray-400">Action: </span>
                        <span className="font-semibold text-indigo-300">{evt.action || evt.route}</span>
                        {evt.amount_recovered !== undefined && evt.amount_recovered > 0 && (
                          <span className="ml-3 text-emerald-400 font-bold">
                            +${evt.amount_recovered.toFixed(2)} Recovered
                          </span>
                        )}
                      </div>

                      {evt.root_cause && (
                        <p className="text-xs text-gray-400 mt-1 italic">
                          "{evt.root_cause}"
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Confidence & Toggle */}
                  <div className="flex flex-col items-end space-y-2">
                    <div className="flex items-center space-x-1.5 bg-gray-900/90 px-2 py-1 rounded-lg border border-gray-800">
                      <span className="text-[10px] text-gray-400 uppercase font-semibold">AI Conf:</span>
                      <span className="text-xs font-mono font-bold text-purple-400">{confidencePct}%</span>
                    </div>

                    <button
                      onClick={() => toggleExpand(idx)}
                      className="flex items-center space-x-1 text-[11px] text-indigo-400 hover:text-indigo-300 transition-all font-medium"
                    >
                      <Code className="h-3 w-3" />
                      <span>{isExpanded ? 'Hide Reasoning' : 'AI Reasoning'}</span>
                      {isExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                    </button>
                  </div>
                </div>

                {/* Expanded AI Reasoning JSON Card */}
                {isExpanded && (
                  <div className="mt-3 pt-3 border-t border-gray-800/80 bg-gray-950/90 rounded-lg p-3 font-mono text-[11px] text-emerald-400 border border-gray-800 overflow-x-auto">
                    <div className="flex items-center justify-between text-gray-400 mb-2 pb-1 border-b border-gray-800 text-[10px]">
                      <span>Cerebras LLM Output Payload</span>
                      <span className="text-purple-400 font-semibold">gpt-oss-120b</span>
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
