import React, { createContext, useContext } from 'react';

export const DomainContext = createContext();

// Mid-I scope: Halite is maintenance-only. The software-domain code is kept in the
// repository but is not reachable from the UI, so the active domain is fixed here.
// Any value left in localStorage by the old domain switcher is deliberately ignored.
export const ACTIVE_DOMAIN = 'maintenance';

const NO_DOMAIN_SWITCHING = () => {};

export function DomainProvider({ children }) {
  return (
    <DomainContext.Provider
      value={{
        domain: ACTIVE_DOMAIN,
        setDomain: NO_DOMAIN_SWITCHING,
        domains: [],
        loading: false,
        error: false,
      }}
    >
      {children}
    </DomainContext.Provider>
  );
}

export function useDomain() {
  return useContext(DomainContext);
}
