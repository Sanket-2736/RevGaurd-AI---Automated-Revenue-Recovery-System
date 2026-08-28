import React from 'react';
import { CasesTable } from '../components/CasesTable';
import { RecoveryCase } from '../types';

interface CasesPageProps {
  cases: RecoveryCase[];
  loadingCases: boolean;
  onRefresh: () => void;
}

export const CasesPage: React.FC<CasesPageProps> = ({ cases, loadingCases, onRefresh }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="w-full">
        <CasesTable cases={cases} loading={loadingCases} onRefresh={onRefresh} />
      </div>
    </div>
  );
};
