import { InboxStackIcon } from '@heroicons/react/24/outline';
import ReviewQueue from '../../pages/ReviewQueue';
import useReviewBadge from './useReviewBadge';

export const routes = [{ path: '/app/review-queue', element: <ReviewQueue /> }];

export const nav = [
  {
    to: '/app/review-queue',
    label: 'Review Queue',
    icon: InboxStackIcon,
    order: 40,
    useBadge: useReviewBadge,
  },
];
