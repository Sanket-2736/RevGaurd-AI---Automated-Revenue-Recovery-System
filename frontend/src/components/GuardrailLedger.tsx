import React, { useState } from 'react';
import { Shield, ShieldAlert, ShieldCheck, AlertCircle, Lock } from 'lucide-react';
import { GuardrailEvent } from '../types';

interface GuardrailLedgerProps {
  events: GuardrailEvent[];
  loading: boolean;
  isFullPage?: boolean;
}

export const GuardrailLedger: React.FC<GuardrailLedgerProps> = ({ events, loading, isFullPage = true }) => {
  const [filter, setFilter] = useState<'ALL' | 'BLOCKED' | 'APPROVED'>('ALL');

  const rulesList = [
    {
      id: 'RULE_1',
      name: 'Rule 1: Case Already Closed',
      condition: 'Case status is RECOVERED / UNRECOVERABLE or resolved_at timestamp is set',
      decision: 'BLOCKED (CLOSED)',
      icon: Lock,
      color: 'text-slate-400',
      badgeBg: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
    },
    {
      id: 'RULE_2',
      name: 'Rule 2: Max Auto-Approval Cap ($500.00)',
      condition: 'amount_at_risk > $500.00 (MAX_AUTO_APPROVAL_AMOUNT threshold)',
      decision: 'HUMAN_REVIEW (BLOCKED)',
      icon: ShieldAlert,
      color: 'text-amber-400',
      badgeBg: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    },
    {
      id: 'RULE_3',
      name: 'Rule 3: Max Retry Limit (3 Retries)',
      condition: 'action == RETRY_PAYMENT and payment attempt_count >= 3',
      decision: 'ESCALATE (BLOCKED)',
      icon: AlertCircle,
      color: 'text-rose-400',
      badgeBg: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    },
    {
      id: 'RULE_4',
      name: 'Rule 4: Min AI Confidence Score (0.60)',
      condition: 'OpenRouter LLM classification confidence < 0.60 (MIN_CONFIDENCE threshold)',
      decision: 'HUMAN_REVIEW (BLOCKED)',
      icon: ShieldAlert,
      color: 'text-purple-400',
      badgeBg: 'bg-purple-500/10 text-purple-300 border-purple-500/30',
    },
    {
      id: 'RULE_5',
      name: 'Rule 5: Safety Guardrails Passed',
      condition: 'All 4 safety guardrail policies evaluated and passed cleanly',
      decision: 'APPROVED (AUTO_EXECUTE)',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      badgeBg: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    },
  ];

  const filteredEvents = events.filter((evt) => {
    if (filter === 'BLOCKED') return evt.decision === 'BLOCKED';
    if (filter === 'APPROVED') return evt.decision === 'APPROVED';
    return true;
  });

  return (
    <div id="tour-guardrails-ledger" className="glass-panel rounded-2xl p-6 lg:p-8 border border-slate-800/80 flex flex-col space-y-8 shadow-xl">
      
      {/* Panel Header */}
      <div className="pb-6 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0">
            <Shield className="h-7 w-7" />
          </div>
          <div>
            <h3 className="text-lg lg:text-xl font-bold text-white font-display flex items-center gap-2">
              Zero-Trust Safety Guardrails Audit Ledger
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium">
                Shield Feature (Blocks = Safe)
              </span>
            </h3>
            <p className="text-xs lg:text-sm text-slate-400 mt-1">
              Persistent database audit trail of policy evaluations from GuardrailEvent table
            </p>
          </div>
        </div>
        <span className="text-xs px-3.5 py-2 rounded-xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono font-bold self-start sm:self-auto shrink-0">
          5 Safety Rules Active
        </span>
      </div>

      {/* Rules Horizontal Rows Display (Clean, No Awkward Wrapping) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 font-display">
            Active Safety Guardrail Policies (Evaluated Sequentially)
          </h4>
          <span className="text-[11px] text-slate-500 font-mono">Sequential Logic • Rule Engine</span>
        </div>

        <div className="space-y-3">
          {rulesList.map((r) => {
            const IconComp = r.icon;
            return (
              <div
                key={r.id}
                className="glass-card rounded-xl p-4 lg:p-5 border border-slate-800/80 bg-slate-900/50 flex flex-col md:flex-row md:items-center justify-between gap-4 transition-all hover:border-slate-700/80"
              >
                {/* Left: Icon & Rule Name */}
                <div className="flex items-center space-x-3.5 min-w-[280px]">
                  <div className={`p-2.5 rounded-xl bg-slate-950 border border-slate-800 ${r.color} shrink-0`}>
                    <IconComp className="h-5 w-5" />
                  </div>
                  <div>
                    <h5 className="text-sm font-bold text-white font-display">{r.name}</h5>
                    <span className="text-[11px] text-slate-500 font-mono">{r.id}</span>
                  </div>
                </div>

                {/* Middle: Condition (Single line, no cramped text wrapping) */}
                <div className="flex-1 font-mono text-xs text-slate-300 bg-slate-950/80 px-3.5 py-2.5 rounded-lg border border-slate-800/60 overflow-x-auto whitespace-nowrap">
                  {r.condition}
                </div>

                {/* Right: Decision Badge */}
                <div className="shrink-0 flex items-center justify-end">
                  <span className={`text-xs px-3.5 py-1.5 rounded-lg font-mono font-bold border ${r.badgeBg}`}>
                    {r.decision}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Events Audit Stream */}
      <div className="pt-6 border-t border-slate-800/80 flex flex-col space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 font-display">
              Live Database Audit Log Stream ({events.length} Events Recorded)
            </h4>
            <p className="text-xs text-slate-500 mt-0.5">Real-time log of executed policy decisions</p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center space-x-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800 text-xs self-start sm:self-auto">
            <button
              onClick={() => setFilter('ALL')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'ALL' ? 'bg-indigo-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All ({events.length})
            </button>
            <button
              onClick={() => setFilter('BLOCKED')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'BLOCKED' ? 'bg-rose-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Blocked ({events.filter((e) => e.decision === 'BLOCKED').length})
            </button>
            <button
              onClick={() => setFilter('APPROVED')}
              className={`px-3 py-1 rounded-lg font-medium transition-all ${
                filter === 'APPROVED' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Approved ({events.filter((e) => e.decision === 'APPROVED').length})
            </button>
          </div>
        </div>

        <div className={`overflow-y-auto pr-1 space-y-3 ${isFullPage ? 'max-h-[500px]' : 'max-h-[380px]'}`}>
          {loading ? (
            <div className="p-12 text-center text-sm text-slate-400 font-medium">Loading guardrail audit events...</div>
          ) : filteredEvents.length === 0 ? (
            <div className="p-12 text-center text-sm text-slate-400 font-medium bg-slate-950/40 rounded-xl border border-slate-800/60">
              No matching guardrail audit events recorded yet. Run a batch to generate audit logs.
            </div>
          ) : (
            filteredEvents.map((evt, idx) => {
              const isBlocked = evt.decision === 'BLOCKED';

              return (
                <div
                  key={idx}
                  className={`glass-card rounded-xl p-4 lg:p-5 border transition-all text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${
                    isBlocked
                      ? 'border-rose-500/30 bg-rose-950/10 hover:border-rose-500/50'
                      : 'border-emerald-500/30 bg-emerald-950/10 hover:border-emerald-500/50'
                  }`}
                >
                  <div className="flex items-start space-x-3.5">
                    <div className="mt-0.5 shrink-0">
                      {isBlocked ? (
                        <ShieldAlert className="h-5 w-5 text-rose-400" />
                      ) : (
                        <ShieldCheck className="h-5 w-5 text-emerald-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2.5">
                        <span className="font-mono font-bold text-white text-xs lg:text-sm">Case #{evt.case_id}</span>
                        <span className="font-mono text-xs text-indigo-300 font-bold px-2 py-0.5 rounded bg-indigo-500/10 border border-indigo-500/20">
                          {evt.rule_triggered}
                        </span>
                      </div>
                      <p className="text-xs lg:text-sm text-slate-300 font-medium mt-1.5">{evt.reason}</p>
                    </div>
                  </div>

                  <div className="flex sm:flex-col items-center sm:items-end justify-between shrink-0 border-t sm:border-0 pt-3 sm:pt-0 border-slate-800">
                    <span
                      className={`text-xs px-3 py-1 rounded-lg font-bold uppercase font-mono ${
                        isBlocked
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {evt.decision}
                    </span>
                    {evt.created_at && (
                      <span className="text-[11px] font-mono text-slate-500 mt-1.5">
                        {new Date(evt.created_at).toLocaleTimeString()}
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

    </div>
  );
};
