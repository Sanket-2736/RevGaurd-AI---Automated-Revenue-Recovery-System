import React from 'react';
import { Database, Search, BookOpen, RotateCcw, HelpCircle } from 'lucide-react';

interface TopHeaderProps {
  pageTitle: string;
  isResetting: boolean;
  onReset: () => void;
  onIngest: () => void;
  onDetect: () => void;
  onOpenGuide: () => void;
  onStartTour: () => void;
}

export const TopHeader: React.FC<TopHeaderProps> = ({
  pageTitle,
  isResetting,
  onReset,
  onIngest,
  onDetect,
  onOpenGuide,
  onStartTour,
}) => {
  return (
    <header className="glass-panel border-b border-slate-800/80 px-6 py-4 sticky top-0 z-20 transition-all">
      <div className="flex items-center justify-between">
        
        {/* Page Context Title */}
        <div>
          <h2 className="text-xl font-bold tracking-tight text-white font-display flex items-center gap-2">
            {pageTitle}
          </h2>
          <p className="text-xs text-slate-400 font-medium mt-0.5">
            Autonomous Revenue Recovery Monorepo System
          </p>
        </div>

        {/* Global Action Bar */}
        <div className="flex items-center space-x-2.5">
          
          <button
            onClick={onStartTour}
            id="tour-help-button"
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-all text-xs font-semibold"
            title="Start Interactive Guided Tour (?)"
          >
            <HelpCircle className="h-4 w-4" />
            <span className="hidden sm:inline">Guided Tour</span>
          </button>

          <button
            onClick={onIngest}
            className="hidden md:flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all text-xs font-medium"
            title="Ingest CSV Datasets"
          >
            <Database className="h-4 w-4 text-indigo-400" />
            <span>Ingest Data</span>
          </button>

          <button
            onClick={onDetect}
            className="hidden md:flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all text-xs font-medium"
            title="Detect Revenue at Risk"
          >
            <Search className="h-4 w-4 text-emerald-400" />
            <span>Detect Risk</span>
          </button>

          <button
            onClick={onOpenGuide}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-all text-xs font-bold shadow-lg shadow-indigo-600/20"
            title="Open Demo Script & Presenter Guide"
          >
            <BookOpen className="h-4 w-4" />
            <span className="hidden sm:inline">Presenter Script</span>
          </button>

          <button
            onClick={onReset}
            disabled={isResetting}
            className="flex items-center space-x-1.5 px-3 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-all text-xs font-medium disabled:opacity-50"
            title="Reset DB & Re-ingest CSV datasets"
          >
            <RotateCcw className={`h-4 w-4 ${isResetting ? 'animate-spin text-amber-400' : 'text-slate-400'}`} />
            <span className="hidden sm:inline">Reset Demo</span>
          </button>

        </div>

      </div>
    </header>
  );
};
