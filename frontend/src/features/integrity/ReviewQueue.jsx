import { useState } from 'react';
import { Badge, PageHeader, Tabs } from '../../components/ui';
import CorrectionsTab from './CorrectionsTab';
import QueueView from './QueueView';
import useAnalysisStatus from './useAnalysisStatus';
import useAssetIds from './useAssetIds';
import useReviewQueue from './useReviewQueue';

export default function ReviewQueue() {
  const [tab, setTab] = useState('review');
  const review = useReviewQueue();
  const assets = useAssetIds();
  const analysisStatus = useAnalysisStatus();
  const waiting = review.queue.length;

  const tabs = [
    {
      id: 'review',
      label: 'Needs review',
      content: <QueueView review={review} analysisStatus={analysisStatus} assets={assets} />,
    },
    { id: 'corrections', label: 'Detected corrections', content: <CorrectionsTab /> },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="px-6 pt-4">
        <PageHeader
          title="Review Queue"
          description="Records the system could not resolve confidently"
          actions={
            !review.loading && waiting > 0 ? (
              <Badge tone="accent">{waiting} awaiting review</Badge>
            ) : null
          }
        />
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <Tabs tabs={tabs} value={tab} onChange={setTab} label="Review queue sections" />
      </div>
    </div>
  );
}
