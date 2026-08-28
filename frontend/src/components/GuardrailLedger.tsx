import React from 'react';
import { Shield, ShieldAlert, ShieldCheck, AlertCircle, Lock } from 'lucide-react';
import { GuardrailEvent } from '../types';

interface GuardrailLedgerProps {
  events: GuardrailEvent[];
  loading: boolean;
  isFullPage?: boolean;
}

export const GuardrailLedger: React.FC<GuardrailLedgerProps> = ({ events, loading, isFullPage = false }) => {
  const rulesList = [
    {
      id: 'RULE_1',
      name: 'Rule 1: Case Already Closed',
      condition: 'Case status is RECOVERED / UNRECOVERABLE or resolved_at timestamp is set',
      decision: 'BLOCKED (CLOSED)',
      icon: Lock,
      color: 'text-slate-400',
      bgColor: 'bg-slate-900/80',
    },
    {
      id: 'RULE_2',
      name: 'Rule 2: Max Auto-Approval Cap ($500.00)',
      condition: 'amount_at_risk > $500.00 (MAX_AUTO_APPROVAL_AMOUNT threshold)',
      decision: 'HUMAN_REVIEW (BLOCKED)',
      icon: ShieldAlert,
      color: 'text-amber-400',
      bgColor: 'bg-amber-950/20 border-amber-500/30',
    },
    {
      id: 'RULE_3',
      name: 'Rule 3: Max Retry Limit (3 Retries)',
      condition: 'action == RETRY_PAYMENT and payment attempt_count >= 3',
      decision: 'ESCALATE (BLOCKED)',
      icon: AlertCircle,
      color: 'text-rose-400',
      bgColor: 'bg-rose-950/20 border-rose-500/30',
    },
    {
      id: 'RULE_4',
      name: 'Rule 4: Min AI Confidence Score (0.60)',
      condition: 'Cerebras LLM classification confidence < 0.60 (MIN_CONFIDENCE threshold)',
      decision: 'HUMAN_REVIEW (BLOCKED)',
      icon: ShieldAlert,
      color: 'text-purple-400',
      bgColor: 'bg-purple-950/20 border-purple-500/30',
    },
    {
      id: 'RULE_5',
      name: 'Rule 5: Safety Guardrails Passed',
      condition: 'All 4 safety guardrail policies evaluated and passed cleanly',
      decision: 'APPROVED (AUTO_EXECUTE)',
      icon: ShieldCheck,
      color: 'text-emerald-400',
      bgColor: 'bg-emerald-950/20 border-emerald-500/30',
    },
  ];

  return (
    <div id="tour-guardrails-ledger" className={`glass-panel rounded-2xl p-6 border border-slate-800/80 flex flex-col ${isFullPage ? 'min-h-[680px]' : 'h-[540px]'}`}>
      
      {/* Panel Header */}
      <div className="pb-5 border-b border-slate-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
            <Shield className="h-6 w-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white font-display flex items-center gap-2">
              Zero-Trust Safety Guardrails Audit Ledger
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30 font-medium">
                Shield Feature (Blocks = Safe)
              </span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Persistent database audit trail of policy evaluations from GuardrailEvent table
            </p>
          </div>
        </div>
        <span className="text-xs px-3 py-1.5 rounded-xl bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono font-bold self-start sm:self-auto">
          5 Safety Rules Active
        </span>
      </div>

      {/* Rules Full-Text Display (NO TRUNCATION!) */}
      <div className="py-4 border-b border-slate-800/80">
        <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-3 font-display">
          Active Safety Guardrail Policies (Evaluated Sequentially)
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {rulesList.map((r) => {
            const IconComp = r.icon;
            return (
              <div key={r.id} className={`rounded-xl p-3.5 border ${r.bgColor}`}>
                <div className="flex items-center space-x-2 mb-1.5">
                  <IconComp className={`h-4 w-4 ${r.color} shrink-0`} />
                  <span className="text-xs font-bold text-slate-100">{r.name}</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed font-medium">{r.condition}</p>
                <div className="mt-2 flex items-center justify-between text-[10px]">
                  <span className="text-slate-400 uppercase font-semibold">Route Decision:</span>
                  <span className={`font-mono font-bold ${r.color}`}>{r.decision}</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Events Audit Stream */}
      <div className="mt-4 flex-1 flex flex-col">
        <h4 className="text-xs font-extrabold uppercase tracking-wider text-slate-400 mb-2 font-display">
          Live Database Audit Log Stream ({events.length} Events)
        </h4>

        <div className="flex-1 overflow-y-auto pr-1 space-y-2.5 max-h-[360px]">
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400 font-medium">Loading guardrail audit events...</div>
          ) : events.length === 0 ? (
            <div className="p-8 text-center text-xs text-slate-400 font-medium">
              No guardrail audit events recorded yet. Run a batch to generate audit logs.
            </div>
          ) : (
            events.map((evt, idx) => {
              const isBlocked = evt.decision === 'BLOCKED';

              return (
                <div
                  key={idx}
                  className={`glass-card rounded-xl p-4 border transition-all text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                    isBlocked
                      ? 'border-rose-500/30 bg-rose-950/10'
                      : 'border-emerald-500/30 bg-emerald-950/10'
                  }`}
                >
                  <div className="flex items-start space-x-3">
                    <div className="mt-0.5 shrink-0">
                      {isBlocked ? (
                        <ShieldAlert className="h-5 w-5 text-rose-400" />
                      ) : (
                        <ShieldCheck className="h-5 w-5 text-emerald-400" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-mono font-bold text-white text-xs">Case #{evt.case_id}</span>
                        <span className="font-mono text-xs text-indigo-300 font-bold">
                          {evt.rule_triggered}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 font-medium mt-1">{evt.reason}</p>
                    </div>
                  </div>

                  <div className="flex sm:flex-col items-center sm:items-end justify-between shrink-0 border-t sm:border-0 pt-2 sm:pt-0 border-slate-800">
                    <span
                      className={`text-xs px-2.5 py-1 rounded-lg font-bold uppercase ${
                        isBlocked
                          ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30'
                          : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                      }`}
                    >
                      {evt.decision}
                    </span>
                    {evt.created_at && (
                      <span className="text-[10px] font-mono text-slate-500 mt-1">
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
