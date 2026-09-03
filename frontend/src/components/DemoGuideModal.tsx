import React from 'react';
import { X, BookOpen } from 'lucide-react';

interface DemoGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const DemoGuideModal: React.FC<DemoGuideModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel w-full max-w-3xl rounded-2xl border border-indigo-500/30 bg-gray-950 p-6 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-gray-800">
          <div className="flex items-center space-x-2">
            <BookOpen className="h-5 w-5 text-indigo-400" />
            <div>
              <h3 className="text-base font-bold text-white">90-Second Presenter Script & Pitch Guide</h3>
              <p className="text-xs text-gray-400">Step-by-step click-by-click instructions for meetings & demos</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-gray-400 hover:text-white bg-gray-900 border border-gray-800 transition-all"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Script Content */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1 text-xs text-gray-300">
          
          {/* Step 1 */}
          <div className="glass-card rounded-xl p-4 border border-indigo-500/20 bg-indigo-950/20">
            <div className="flex items-center justify-between text-indigo-400 font-bold text-xs mb-1">
              <span className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-indigo-500/20 flex items-center justify-center text-[10px]">1</span>
                0:00 - 0:15 | The Hook & Problem
              </span>
              <span className="text-[10px] font-mono text-gray-400">INTRO</span>
            </div>
            <p className="text-gray-200 italic leading-relaxed">
              "Judges, businesses lose up to 15% of ARR to silent revenue leakage—expired credit cards, abandoned checkouts, and overdue invoices. Existing tools are rigid retry loops that spam customers. We built RevGuard AI—an autonomous revenue recovery agent powered by OpenRouter."
            </p>
          </div>

          {/* Step 2 */}
          <div className="glass-card rounded-xl p-4 border border-emerald-500/20 bg-emerald-950/20">
            <div className="flex items-center justify-between text-emerald-400 font-bold text-xs mb-1">
              <span className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-emerald-500/20 flex items-center justify-center text-[10px]">2</span>
                0:15 - 0:35 | Live Trigger (Clicking 'Run Batch')
              </span>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">CLICK: ⚡ Run Recovery Batch</span>
            </div>
            <p className="text-gray-200 italic leading-relaxed">
              "Watch our agent in action. Here we have $376,590 tied up across 381 detected risk cases. I’m firing an async batch run now. In real-time via Server-Sent Events, OpenRouter LLM analyzes each case, classifies the root cause, and selects the optimal recovery action."
            </p>
          </div>

          {/* Step 3 */}
          <div className="glass-card rounded-xl p-4 border border-rose-500/20 bg-rose-950/20">
            <div className="flex items-center justify-between text-rose-400 font-bold text-xs mb-1">
              <span className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-rose-500/20 flex items-center justify-center text-[10px]">3</span>
                0:35 - 0:55 | Highlighting Safety Guardrails
              </span>
              <span className="text-[10px] font-mono text-rose-400 font-bold">POINT TO: Guardrail Ledger</span>
            </div>
            <p className="text-gray-200 italic leading-relaxed">
              "Autonomous AI can be dangerous if unconstrained. Our system enforces a Zero-Trust 5-Rule Safety Guardrail architecture. Look at high-value cases over $500—Rule 2 automatically intercepts them, requiring human authorization."
            </p>
          </div>

          {/* Step 4 */}
          <div className="glass-card rounded-xl p-4 border border-purple-500/20 bg-purple-950/20">
            <div className="flex items-center justify-between text-purple-400 font-bold text-xs mb-1">
              <span className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-purple-500/20 flex items-center justify-center text-[10px]">4</span>
                0:55 - 1:15 | Deep Dive into AI Reasoning
              </span>
              <span className="text-[10px] font-mono text-purple-400 font-bold">CLICK: AI Reasoning Toggle</span>
            </div>
            <p className="text-gray-200 italic leading-relaxed">
              "Let's inspect the AI's reasoning. For Case #1, OpenRouter identified 'Card Expired' with 95% confidence and chose 'UPDATE_PAYMENT_METHOD' instead of blindly retrying a dead card. Safe cases execute automatically in our simulator."
            </p>
          </div>

          {/* Step 5 */}
          <div className="glass-card rounded-xl p-4 border border-amber-500/20 bg-amber-950/20">
            <div className="flex items-center justify-between text-amber-400 font-bold text-xs mb-1">
              <span className="flex items-center gap-1.5">
                <span className="h-5 w-5 rounded-full bg-amber-500/20 flex items-center justify-center text-[10px]">5</span>
                1:15 - 1:30 | The Proven Benchmark Results
              </span>
              <span className="text-[10px] font-mono text-amber-400 font-bold">POINT TO: KPI Top Cards</span>
            </div>
            <p className="text-gray-200 italic leading-relaxed">
              "The proof is in the ledger: $269,435 recovered out of $376,590—a 71.5% recovery rate with 96.1% classification accuracy against ground truth benchmarks. RevGuard AI turns lost revenue into recovered cash safely."
            </p>
          </div>

        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-gray-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs transition-all"
          >
            Got it, Let's Demo!
          </button>
        </div>

      </div>
    </div>
  );
};
