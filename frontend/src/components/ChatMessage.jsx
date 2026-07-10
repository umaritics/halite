import { useState } from 'react';
import { ChevronDownIcon, ChevronUpIcon } from '@heroicons/react/24/outline';
import BrandName from './BrandName';

function SourceBadge({ status }) {
  if (status === 'needs_review') {
    return (
      <span className="status-needs_review ml-2" title="This decision may be outdated">
        ⚠ Outdated
      </span>
    );
  }
  if (status === 'invalidated') {
    return (
      <span className="status-invalidated ml-2" title="This decision has been invalidated">
        ✗ Invalidated
      </span>
    );
  }
  return null;
}

export default function ChatMessage({ message }) {
  const isUser = message.role === 'user';
  const [sourcesOpen, setSourcesOpen] = useState(false);
  const sources = message.sources || [];

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser ? 'bg-accent text-black' : 'halite-card text-primary'
        }`}
      >
        {!isUser && (
          <div className="mb-1 flex items-center gap-2 font-sans text-xs font-medium text-accent">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-accent" />
            <BrandName className="text-xs text-accent" />
          </div>
        )}
        <div className="whitespace-pre-wrap font-sans text-sm leading-relaxed">{message.content}</div>

        {!isUser && sources.length > 0 && (
          <div className="mt-3 border-t border-theme pt-2">
            <button
              onClick={() => setSourcesOpen(!sourcesOpen)}
              className="flex w-full items-center justify-between font-sans text-xs text-secondary hover:text-accent"
            >
              <span>Sources ({sources.length})</span>
              {sourcesOpen ? <ChevronUpIcon className="h-4 w-4" /> : <ChevronDownIcon className="h-4 w-4" />}
            </button>
            {sourcesOpen && (
              <ul className="mt-2 space-y-1.5">
                {sources.map((src, i) => (
                  <li
                    key={`${src.type}-${src.id}-${i}`}
                    className="flex flex-wrap items-center gap-1 rounded-md bg-surface px-2 py-1 font-sans text-xs"
                  >
                    <span className="font-medium text-accent">{src.type}</span>
                    <span className="text-primary">{src.title}</span>
                    <SourceBadge status={src.status} />
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
