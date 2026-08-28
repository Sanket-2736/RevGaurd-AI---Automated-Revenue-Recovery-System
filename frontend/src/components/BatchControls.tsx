import React, { useState } from 'react';
import { Zap, Sliders, RefreshCw, Play } from 'lucide-react';

interface BatchControlsProps {
  isRunning: boolean;
  activeBatchId: string | null;
  progressPct: number;
  totalEnqueued: number;
  mode?: string;
  onRunBatch: (limit: number) => void;
}

export const BatchControls: React.FC<BatchControlsProps> = ({
  isRunning,
  activeBatchId,
  progressPct,
  totalEnqueued,
  mode,
  onRunBatch,
}) => {
  const [limit, setLimit] = useState<number>(381);

  const handleStart = () => {
    onRunBatch(limit);
  };

  return (
    <div id="tour-batch-controls" className="glass-panel rounded-2xl p-5 mb-6 border border-indigo-500/20 bg-gradient-to-r from-gray-900/90 via-gray-900/60 to-indigo-950/30">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        
        {/* Left: Control Instructions */}
        <div>
          <h2 className="text-base font-bold text-white flex items-center gap-2">
            <Zap className="h-5 w-5 text-indigo-400" />
            Autonomous Batch Recovery Controls
          </h2>
          <p className="text-xs text-gray-400 mt-0.5">
            Enqueue detected revenue-at-risk cases for instant Cerebras LLM evaluation & Guardrail filtering.
          </p>
        </div>

        {/* Right: Selectors & Execution Buttons */}
        <div className="flex flex-wrap items-center gap-3">
          
          <div className="flex items-center space-x-2 bg-gray-900/90 px-3 py-1.5 rounded-xl border border-gray-800">
            <Sliders className="h-4 w-4 text-gray-400" />
            <label className="text-xs text-gray-300 font-medium">Batch Limit:</label>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              disabled={isRunning}
              className="bg-gray-800 text-white text-xs font-semibold rounded-lg px-2 py-1 border border-gray-700 focus:outline-none focus:border-indigo-500 disabled:opacity-50"
            >
              <option value={381}>381 Cases (Full Dataset - Recommended)</option>
              <option value={100}>100 Cases</option>
              <option value={50}>50 Cases</option>
              <option value={10}>10 Cases</option>
            </select>
          </div>

          <button
            onClick={handleStart}
            disabled={isRunning}
            className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 via-indigo-500 to-emerald-500 text-white font-bold text-xs shadow-lg shadow-indigo-500/25 hover:shadow-indigo-500/40 hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <RefreshCw className="h-4 w-4 animate-spin text-white" />
                <span>Processing Batch...</span>
              </>
            ) : (
              <>
                <Play className="h-4 w-4 fill-current text-white" />
                <span>⚡ Run Recovery Batch</span>
              </>
            )}
          </button>

        </div>

      </div>

      {/* Progress Bar & Status */}
      {(activeBatchId || isRunning) && (
        <div className="mt-4 pt-4 border-t border-gray-800/80">
          <div className="flex items-center justify-between text-xs mb-1.5">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-indigo-300">
                Batch ID: <span className="font-mono text-gray-200">{activeBatchId}</span>
              </span>
              {totalEnqueued > 0 && (
                <span className="text-[10px] text-gray-400">({totalEnqueued} total)</span>
              )}
              {mode && (
                <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 font-mono text-[10px]">
                  MODE: {mode}
                </span>
              )}
            </div>
            <span className="font-bold text-emerald-400 font-mono">
              {progressPct.toFixed(1)}% Completed
            </span>
          </div>

          <div className="w-full bg-gray-800/80 h-2.5 rounded-full overflow-hidden p-0.5 border border-gray-700">
            <div
              className="bg-gradient-to-r from-indigo-500 via-purple-500 to-emerald-400 h-full rounded-full transition-all duration-300 shadow-sm"
              style={{ width: `${Math.max(progressPct, 2)}%` }}
            />
          </div>
        </div>
      )}

    </div>
  );
};
