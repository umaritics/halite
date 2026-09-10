import React, { createContext, useContext, useState, useEffect } from 'react';
import { domainsAPI } from '../api/client';

export const DomainContext = createContext();

const FALLBACK_DOMAINS = [
  { key: 'software', display_name: 'Software Engineering' },
  { key: 'maintenance', display_name: 'Maintenance / Field Service' }
];

export function DomainProvider({ children }) {
  const [domain, setDomainState] = useState(() => {
    return localStorage.getItem('halite.domain') || 'software';
  });
  const [domains, setDomains] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    domainsAPI.list()
      .then(res => {
        setDomains(res.data);
        setError(false);
      })
      .catch(err => {
        console.error('Failed to fetch domains', err);
        setDomains(FALLBACK_DOMAINS);
        setError(true);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const setDomain = (newDomain) => {
    setDomainState(newDomain);
    localStorage.setItem('halite.domain', newDomain);
  };

  return (
    <DomainContext.Provider value={{ domain, setDomain, domains, loading, error }}>
      {children}
    </DomainContext.Provider>
  );
}

export function useDomain() {
  return useContext(DomainContext);
}
