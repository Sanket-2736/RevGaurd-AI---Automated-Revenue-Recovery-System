import React from 'react';
import { Database, Search, Cpu, ShieldCheck, RefreshCw, CheckCircle2, ChevronRight } from 'lucide-react';

interface PipelineStepperProps {
  isRunningBatch: boolean;
  progressPct: number;
  hasProcessedCases: boolean;
}

export const PipelineStepper: React.FC<PipelineStepperProps> = ({
  isRunningBatch,
  progressPct,
  hasProcessedCases,
}) => {

  // Determine stage states
  const getStageState = (stageIndex: number) => {
    // Stage 0: Ingest (Always complete)
    // Stage 1: Detect (Always complete)
    if (stageIndex <= 1) {
      return { status: 'COMPLETED', label: 'Completed' };
    }

    if (isRunningBatch) {
      if (progressPct <= 35) {
        if (stageIndex === 2) return { status: 'ACTIVE', label: 'Processing...' };
        return { status: 'PENDING', label: 'Queued' };
      } else if (progressPct <= 75) {
        if (stageIndex === 2) return { status: 'COMPLETED', label: 'Passed' };
        if (stageIndex === 3) return { status: 'ACTIVE', label: 'Evaluating...' };
        return { status: 'PENDING', label: 'Queued' };
      } else {
        if (stageIndex <= 3) return { status: 'COMPLETED', label: 'Passed' };
        if (stageIndex === 4) return { status: 'ACTIVE', label: 'Executing...' };
        return { status: 'PENDING', label: 'Queued' };
      }
    }

    if (hasProcessedCases || progressPct >= 100) {
      return { status: 'COMPLETED', label: 'Passed' };
    }

    return { status: 'PENDING', label: 'Ready' };
  };

  const stages = [
    {
      id: 0,
      name: '1. Ingest Data',
      desc: 'Synthetic Datasets Loaded',
      icon: Database,
    },
    {
      id: 1,
      name: '2. Risk Detection',
      desc: '381 Cases Identified',
      icon: Search,
    },
    {
      id: 2,
      name: '3. AI Classification',
      desc: 'Cerebras Root Cause',
      icon: Cpu,
    },
    {
      id: 3,
      name: '4. Guardrails Check',
      desc: '5 Safety Rules Policy',
      icon: ShieldCheck,
    },
    {
      id: 4,
      name: '5. Recovery Action',
      desc: 'Ledger Update & Simulation',
      icon: RefreshCw,
    },
  ];

  return (
    <div className="w-full glass-panel rounded-2xl p-4 mb-6 border border-gray-800 bg-gray-950/80 shadow-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[11px] font-extrabold uppercase tracking-widest text-indigo-400 flex items-center gap-1.5">
          <span className="h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
          Autonomous System Execution Pipeline
        </span>
        <span className="text-xs text-gray-400 font-medium">
          {isRunningBatch ? (
            <span className="text-emerald-400 font-mono font-bold animate-pulse">
              ⚡ Batch Active ({progressPct.toFixed(0)}%)
            </span>
          ) : hasProcessedCases ? (
            <span className="text-emerald-400 font-bold flex items-center gap-1">
              <CheckCircle2 className="h-3.5 w-3.5" /> Pipeline Verified
            </span>
          ) : (
            <span className="text-gray-500 font-medium">Ready for Batch Trigger</span>
          )}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-5 gap-2 lg:gap-3">
        {stages.map((stg, idx) => {
          const { status, label } = getStageState(stg.id);
          const IconComp = stg.icon;

          const isCompleted = status === 'COMPLETED';
          const isActive = status === 'ACTIVE';

          return (
            <div key={stg.id} className="relative flex items-center">
              <div
                className={`w-full rounded-xl p-3 border transition-all duration-300 flex items-center space-x-3 ${
                  isActive
                    ? 'border-indigo-500 bg-indigo-950/40 text-white shadow-lg shadow-indigo-500/20 animate-pulse-ring'
                    : isCompleted
                    ? 'border-emerald-500/30 bg-emerald-950/10 text-gray-200'
                    : 'border-gray-800 bg-gray-900/40 text-gray-500'
                }`}
              >
                <div
                  className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 font-bold text-xs ${
                    isActive
                      ? 'bg-indigo-600 text-white animate-spin'
                      : isCompleted
                      ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                      : 'bg-gray-800 text-gray-500'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-400" />
                  ) : (
                    <IconComp className="h-4 w-4" />
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold truncate text-gray-200">{stg.name}</span>
                  </div>
                  <div className="flex items-center justify-between text-[10px] text-gray-400 mt-0.5">
                    <span className="truncate">{stg.desc}</span>
                    <span
                      className={`font-mono text-[9px] px-1.5 py-0.2 rounded font-semibold ${
                        isActive
                          ? 'text-indigo-300 bg-indigo-500/20'
                          : isCompleted
                          ? 'text-emerald-400'
                          : 'text-gray-600'
                      }`}
                    >
                      {label}
                    </span>
                  </div>
                </div>
              </div>

              {idx < stages.length - 1 && (
                <ChevronRight className="hidden sm:block absolute -right-2 z-10 h-4 w-4 text-gray-700 pointer-events-none" />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
