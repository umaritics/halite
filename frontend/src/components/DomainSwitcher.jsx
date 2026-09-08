import React from 'react';
import { useDomain } from '../context/DomainContext';

export default function DomainSwitcher() {
  const { domain, setDomain, domains } = useDomain();

  if (!domains || domains.length === 0) return null;

  return (
    <div className="mt-4 flex w-full rounded-md border border-theme p-0.5 bg-surface-dark/10">
      {domains.map((d) => {
        const isActive = d.key === domain;
        return (
          <button
            key={d.key}
            onClick={() => setDomain(d.key)}
            className={`flex-1 rounded-md py-1.5 font-sans text-xs font-medium transition-colors ${
              isActive
                ? 'bg-accent text-black'
                : 'text-[#888888] hover:text-accent'
            }`}
          >
            {d.display_name.includes('Software') ? 'Software' : 'Maintenance'}
          </button>
        );
      })}
    </div>
  );
}
