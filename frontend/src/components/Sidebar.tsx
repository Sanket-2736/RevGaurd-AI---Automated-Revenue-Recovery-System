import React from 'react';
import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Activity, Shield, Database, BarChart3, Zap, Cpu, CheckCircle2, Search, RefreshCw } from 'lucide-react';

interface SidebarProps {
  isConnected: boolean;
  isRunningBatch: boolean;
  progressPct: number;
  hasProcessedCases: boolean;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isConnected,
  isRunningBatch,
  progressPct,
  hasProcessedCases,
}) => {

  const navItems = [
    { path: '/', label: 'Overview', icon: LayoutDashboard, badge: 'Pitch Page' },
    { path: '/live', label: 'Live Case Stream', icon: Activity, badge: 'SSE Feed' },
    { path: '/guardrails', label: 'Safety Guardrails', icon: Shield, badge: '5 Rules' },
    { path: '/cases', label: 'Cases Database', icon: Database, badge: '381 Cases' },
    { path: '/analytics', label: 'Category Benchmarks', icon: BarChart3, badge: 'Accuracy' },
  ];

  // Pipeline stages for sidebar condensed stepper
  const pipelineStages = [
    { name: '1. Ingest Data', icon: Database, done: true },
    { name: '2. Risk Detection', icon: Search, done: true },
    { name: '3. AI Classify', icon: Cpu, done: isRunningBatch ? progressPct > 10 : hasProcessedCases },
    { name: '4. Guardrails', icon: Shield, done: isRunningBatch ? progressPct > 50 : hasProcessedCases },
    { name: '5. Recovered', icon: RefreshCw, done: isRunningBatch ? progressPct >= 100 : hasProcessedCases },
  ];

  return (
    <aside className="w-64 bg-[#0F172A] border-r border-slate-800/80 flex flex-col justify-between h-screen sticky top-0 shrink-0 select-none z-30">
      
      {/* Brand Header */}
      <div>
        <div className="p-5 border-b border-slate-800/80">
          <div className="flex items-center space-x-3">
            <div className="h-11 w-11 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-emerald-500 flex items-center justify-center shadow-lg shadow-indigo-500/25">
              <Zap className="h-6 w-6 text-white fill-current" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tight text-white font-display flex items-center gap-1.5">
                RevGuard AI
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono border border-indigo-500/30">
                  v1.0
                </span>
              </h1>
              <p className="text-[11px] text-slate-400 font-medium">Revenue Recovery Console</p>
            </div>
          </div>

          {/* Connection Badge */}
          <div className="mt-3 flex items-center justify-between px-3 py-1.5 rounded-lg bg-slate-900/90 border border-slate-800 text-xs">
            <div className="flex items-center space-x-2">
              <span className={`h-2 w-2 rounded-full ${isConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
              <span className="text-slate-300 font-semibold">{isConnected ? 'Backend Active' : 'Offline'}</span>
            </div>
            <span className="text-[10px] font-mono text-indigo-400">FastAPI</span>
          </div>
        </div>

        {/* Main Navigation Links */}
        <nav className="p-3 space-y-1.5">
          <div className="px-3 py-1 text-[11px] font-extrabold uppercase tracking-wider text-slate-500">
            System Workspace
          </div>
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `flex items-center justify-between px-3.5 py-2.5 rounded-xl font-semibold text-xs transition-all ${
                    isActive
                      ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30 border border-indigo-500/40'
                      : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/60'
                  }`
                }
              >
                <div className="flex items-center space-x-3">
                  <Icon className="h-4 w-4" />
                  <span>{item.label}</span>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-900 text-slate-400 border border-slate-800 font-mono">
                  {item.badge}
                </span>
              </NavLink>
            );
          })}
        </nav>
      </div>

      {/* Bottom Section: Condensed 5-Stage Pipeline Stepper */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/60">
        <div className="flex items-center justify-between text-[11px] font-bold text-slate-400 mb-2">
          <span>Execution Pipeline</span>
          <span className="font-mono text-indigo-400">{isRunningBatch ? `${progressPct.toFixed(0)}%` : 'Ready'}</span>
        </div>

        <div className="space-y-1.5">
          {pipelineStages.map((stg, idx) => {
            const Icon = stg.icon;
            return (
              <div
                key={idx}
                className={`flex items-center justify-between px-2.5 py-1.5 rounded-lg text-[11px] transition-all ${
                  stg.done
                    ? 'bg-emerald-950/20 text-emerald-300 border border-emerald-500/20'
                    : isRunningBatch && idx === 2
                    ? 'bg-indigo-950/40 text-indigo-300 border border-indigo-500/30 animate-pulse'
                    : 'bg-slate-900/40 text-slate-500 border border-slate-800/40'
                }`}
              >
                <div className="flex items-center space-x-2">
                  <Icon className="h-3 w-3" />
                  <span className="font-medium truncate">{stg.name}</span>
                </div>
                {stg.done ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400 shrink-0" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-slate-700 shrink-0" />
                )}
              </div>
            );
          })}
        </div>
      </div>

    </aside>
  );
};
