import React, { useState } from 'react';
import { Search, Database, RefreshCw } from 'lucide-react';
import { RecoveryCase } from '../types';

interface CasesTableProps {
  cases: RecoveryCase[];
  loading: boolean;
  onRefresh: () => void;
}

export const CasesTable: React.FC<CasesTableProps> = ({ cases, loading, onRefresh }) => {
  const [search, setSearch] = useState('');
  const [selectedStatus, setSelectedStatus] = useState<string>('ALL');

  const filteredCases = cases.filter((c) => {
    const matchesSearch =
      c.id.toString().includes(search) ||
      c.customer_name.toLowerCase().includes(search.toLowerCase()) ||
      c.customer_email.toLowerCase().includes(search.toLowerCase()) ||
      (c.root_cause && c.root_cause.toLowerCase().includes(search.toLowerCase())) ||
      c.case_type.toLowerCase().includes(search.toLowerCase());

    const matchesStatus = selectedStatus === 'ALL' || c.status === selectedStatus;

    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'RECOVERED':
        return 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30';
      case 'APPROVED':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
      case 'BLOCKED':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/30';
      case 'ESCALATED':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/30';
      default:
        return 'bg-gray-800 text-gray-300 border-gray-700';
    }
  };

  const getSourceBadge = (source?: string | null) => {
    switch (source) {
      case 'AI_SECONDARY':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">AI Secondary</span>;
      case 'FALLBACK_RULE':
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">Fallback Rule</span>;
      case 'AI_PRIMARY':
      default:
        return <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">AI Primary</span>;
    }
  };

  return (
    <div className="glass-panel rounded-2xl p-5 border border-gray-800 flex flex-col h-[520px]">
      
      {/* Table Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pb-4 border-b border-gray-800">
        
        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Database className="h-5 w-5 text-indigo-400" />
          <h3 className="text-sm font-bold text-white">Detected Revenue Cases ({cases.length})</h3>
          <button
            onClick={onRefresh}
            className="p-1 rounded-lg text-gray-400 hover:text-white transition-all"
            title="Refresh Cases"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2 w-full sm:w-auto">
          
          {/* Search Box */}
          <div className="relative flex-1 sm:w-64">
            <Search className="h-3.5 w-3.5 absolute left-3 top-2.5 text-gray-500" />
            <input
              type="text"
              placeholder="Search case #, customer, root cause..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-gray-900 text-xs text-white placeholder-gray-500 rounded-xl pl-8 pr-3 py-2 border border-gray-800 focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Status Filter */}
          <div className="flex items-center space-x-1 bg-gray-900 p-1 rounded-xl border border-gray-800 text-xs">
            {['ALL', 'DETECTED', 'APPROVED', 'RECOVERED', 'BLOCKED'].map((st) => (
              <button
                key={st}
                onClick={() => setSelectedStatus(st)}
                className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                  selectedStatus === st ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-gray-200'
                }`}
              >
                {st}
              </button>
            ))}
          </div>

        </div>

      </div>

      {/* Datatable */}
      <div className="flex-1 overflow-auto mt-3">
        <table className="w-full text-left text-xs text-gray-300">
          <thead className="bg-gray-900/90 text-gray-400 uppercase font-semibold text-[10px] tracking-wider sticky top-0 z-10 border-b border-gray-800">
            <tr>
              <th className="py-2.5 px-3">Case ID</th>
              <th className="py-2.5 px-3">Customer</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Amount At Risk</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-3">AI Recommendation</th>
              <th className="py-2.5 px-3">Decision Source</th>
              <th className="py-2.5 px-3">Confidence</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800/60 font-medium">
            {loading ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-500">
                  Loading cases from database...
                </td>
              </tr>
            ) : filteredCases.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-8 text-center text-gray-500">
                  No revenue cases matching filters.
                </td>
              </tr>
            ) : (
              filteredCases.map((c) => (
                <tr key={c.id} className="hover:bg-gray-800/40 transition-colors">
                  <td className="py-3 px-3 font-mono font-bold text-white">#{c.id}</td>
                  <td className="py-3 px-3">
                    <div className="font-semibold text-gray-200">{c.customer_name}</div>
                    <div className="text-[10px] text-gray-500">{c.customer_email}</div>
                  </td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded bg-gray-800 text-gray-300 text-[10px] font-mono border border-gray-700">
                      {c.case_type}
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono font-bold text-amber-400">
                    ${c.amount_at_risk.toFixed(2)}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${getStatusBadge(
                        c.status
                      )}`}
                    >
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3 px-3">
                    {c.recommended_action ? (
                      <div>
                        <div className="font-semibold text-indigo-300">{c.recommended_action}</div>
                        {c.root_cause && (
                          <div className="text-[10px] text-gray-400 italic truncate max-w-xs">
                            {c.root_cause}
                          </div>
                        )}
                      </div>
                    ) : (
                      <span className="text-gray-500 text-[11px]">Pending AI Evaluation</span>
                    )}
                  </td>
                  <td className="py-3 px-3">
                    {c.recommended_action ? getSourceBadge(c.decision_source) : '-'}
                  </td>
                  <td className="py-3 px-3 font-mono text-purple-400 font-bold">
                    {c.ai_confidence ? `${Math.round(c.ai_confidence * 100)}%` : '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

    </div>
  );
};
