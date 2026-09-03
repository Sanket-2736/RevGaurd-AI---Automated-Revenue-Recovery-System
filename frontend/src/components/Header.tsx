import React from 'react';
import { Shield, Zap, RotateCcw, Cpu, BookOpen, Database, Search, HelpCircle } from 'lucide-react';

interface HeaderProps {
  isConnected: boolean;
  isResetting: boolean;
  onReset: () => void;
  onIngest: () => void;
  onDetect: () => void;
  onOpenGuide: () => void;
  onStartTour: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  isConnected,
  isResetting,
  onReset,
  onIngest,
  onDetect,
  onOpenGuide,
  onStartTour,
}) => {
  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-gray-800 px-4 lg:px-8 py-3 transition-all">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        {/* Brand & System Status */}
        <div className="flex items-center space-x-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <Zap className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                RevGuard AI
                <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 font-medium">
                  v1.0 MONOREPO
                </span>
              </h1>
            </div>
            <p className="text-xs text-gray-400 font-medium">
              Autonomous Revenue Recovery System • Powered by OpenRouter LLM
            </p>
          </div>
        </div>

        {/* System Health Indicators */}
        <div className="flex flex-wrap items-center gap-2 lg:gap-3">
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs">
            <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
            <span className="text-gray-300 font-medium">
              {isConnected ? 'Backend Connected' : 'Disconnected'}
            </span>
          </div>

          <div className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs text-purple-300">
            <Cpu className="h-3.5 w-3.5 text-purple-400" />
            <span>OpenRouter LLM Active</span>
          </div>

          <div className="hidden md:flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-900/80 border border-gray-800 text-xs text-emerald-300">
            <Shield className="h-3.5 w-3.5 text-emerald-400" />
            <span>5-Rule Guardrails</span>
          </div>
        </div>

        {/* Action Controls */}
        <div className="flex items-center space-x-2">
          {/* Help Tour Icon Button */}
          <button
            onClick={onStartTour}
            id="tour-help-button"
            className="flex items-center justify-center p-2 rounded-lg bg-indigo-500/20 hover:bg-indigo-500/30 text-indigo-300 border border-indigo-500/30 transition-all"
            title="Start Interactive Guided Tour (?)"
          >
            <HelpCircle className="h-4 w-4" />
          </button>

          <button
            onClick={onIngest}
            className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition-all text-xs font-medium"
            title="Ingest CSV Datasets"
          >
            <Database className="h-3.5 w-3.5 text-indigo-400" />
            <span>Ingest Data</span>
          </button>

          <button
            onClick={onDetect}
            className="hidden lg:flex items-center space-x-1.5 px-2.5 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 transition-all text-xs font-medium"
            title="Detect Revenue at Risk"
          >
            <Search className="h-3.5 w-3.5 text-emerald-400" />
            <span>Detect Risk</span>
          </button>

          <button
            onClick={onOpenGuide}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 hover:bg-indigo-600/30 transition-all text-xs font-semibold"
            title="Open Demo Script & Presenter Guide"
          >
            <BookOpen className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Presenter Guide</span>
          </button>

          <button
            onClick={onReset}
            disabled={isResetting}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 transition-all text-xs font-medium disabled:opacity-50"
            title="Reset DB & Re-ingest CSV datasets"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin text-amber-400' : 'text-gray-400'}`} />
            <span>Reset Demo</span>
          </button>
        </div>

      </div>
    </header>
  );
};
