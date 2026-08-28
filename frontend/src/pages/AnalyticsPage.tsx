import React from 'react';
import { CategoryBreakdown } from '../components/CategoryBreakdown';
import { MetricsResponse } from '../types';

interface AnalyticsPageProps {
  metrics: MetricsResponse | null;
}

export const AnalyticsPage: React.FC<AnalyticsPageProps> = ({ metrics }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="w-full">
        <CategoryBreakdown metrics={metrics} />
      </div>
    </div>
  );
};
