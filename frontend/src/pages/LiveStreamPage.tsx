import React from 'react';
import { LiveStreamFeed } from '../components/LiveStreamFeed';
import { BatchControls } from '../components/BatchControls';
import { SSEStreamEvent } from '../types';

interface LiveStreamPageProps {
  streamEvents: SSEStreamEvent[];
  isRunningBatch: boolean;
  activeBatchId: string | null;
  batchProgress: number;
  totalEnqueued: number;
  batchMode?: string;
  onRunBatch: (limit: number) => void;
}

export const LiveStreamPage: React.FC<LiveStreamPageProps> = ({
  streamEvents,
  isRunningBatch,
  activeBatchId,
  batchProgress,
  totalEnqueued,
  batchMode,
  onRunBatch,
}) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      
      {/* Batch Control Header */}
      <BatchControls
        isRunning={isRunningBatch}
        activeBatchId={activeBatchId}
        progressPct={batchProgress}
        totalEnqueued={totalEnqueued}
        mode={batchMode}
        onRunBatch={onRunBatch}
      />

      {/* Full Width Live Case Feed */}
      <div className="w-full">
        <LiveStreamFeed events={streamEvents} isStreaming={isRunningBatch} />
      </div>

    </div>
  );
};
