import React from 'react';
import { GuardrailLedger } from '../components/GuardrailLedger';
import { GuardrailEvent } from '../types';

interface GuardrailsPageProps {
  events: GuardrailEvent[];
  loadingEvents: boolean;
}

export const GuardrailsPage: React.FC<GuardrailsPageProps> = ({ events, loadingEvents }) => {
  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="w-full">
        <GuardrailLedger events={events} loading={loadingEvents} isFullPage={true} />
      </div>
    </div>
  );
};
