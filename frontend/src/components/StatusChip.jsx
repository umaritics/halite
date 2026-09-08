import React from 'react';

export default function StatusChip({ status }) {
  const baseClasses = "inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border";

  switch (status) {
    case 'auto_accepted':
      return <span className={`${baseClasses} bg-accent/10 border-accent/20 text-accent`}>Auto Accepted</span>;
    case 'needs_review':
      return <span className={`${baseClasses} bg-amber-500/10 border-amber-500/20 text-amber-600 dark:text-amber-400`}>Needs Review</span>;
    case 'accepted':
      return <span className={`${baseClasses} bg-green-500/10 border-green-500/20 text-green-600 dark:text-green-400`}>Accepted</span>;
    case 'rejected':
      return <span className={`${baseClasses} bg-gray-500/10 border-gray-500/20 text-gray-600 dark:text-gray-400`}>Rejected</span>;
    case 'superseded':
      return <span className={`${baseClasses} bg-gray-500/10 border-gray-500/20 text-gray-500 line-through opacity-70`}>Superseded</span>;
    default:
      return <span className={`${baseClasses} bg-gray-100 border-gray-200 text-gray-800`}>{status}</span>;
  }
}
