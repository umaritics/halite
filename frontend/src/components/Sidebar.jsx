import { NavLink, Link } from 'react-router-dom';
import {
  ChatBubbleLeftRightIcon,
  CircleStackIcon,
  DocumentArrowUpIcon,
  ExclamationTriangleIcon,
  Cog6ToothIcon,
  ScaleIcon,
  WrenchScrewdriverIcon,
  ClipboardDocumentListIcon,
  InboxStackIcon
} from '@heroicons/react/24/outline';
import HaliteLogo from './HaliteLogo';
import BrandName from './BrandName';
import DomainSwitcher from './DomainSwitcher';
import { useTheme } from '../context/ThemeContext';
import { useDomain } from '../context/DomainContext';

const NAV_BY_DOMAIN = {
  software: [
    { to: '/app/chat', label: 'Chat', icon: ChatBubbleLeftRightIcon },
    { to: '/app/graph', label: 'Knowledge Graph', icon: CircleStackIcon },
    { to: '/app/decisions', label: 'Decisions', icon: ScaleIcon },
    { to: '/app/ingest', label: 'Ingest', icon: DocumentArrowUpIcon },
    { to: '/app/alerts', label: 'Alerts', icon: ExclamationTriangleIcon, badge: true },
    { to: '/app/settings', label: 'Settings', icon: Cog6ToothIcon },
  ],
  maintenance: [
    { to: '/app/assets', label: 'Assets', icon: WrenchScrewdriverIcon },
    { to: '/app/records', label: 'Service Records', icon: ClipboardDocumentListIcon },
    { to: '/app/review-queue', label: 'Review Queue', icon: InboxStackIcon, badge: true },
    { to: '/app/maintenance-ingest', label: 'Ingest', icon: DocumentArrowUpIcon },
    { to: '/app/graph', label: 'Knowledge Graph', icon: CircleStackIcon },
    { to: '/app/settings', label: 'Settings', icon: Cog6ToothIcon },
  ],
};

export default function Sidebar({ alertCount = 0 }) {
  const { isDark } = useTheme();
  const { domain } = useDomain();

  const navItems = NAV_BY_DOMAIN[domain] || NAV_BY_DOMAIN.software;

  return (
    <aside
      className={`flex h-full w-64 flex-col border-r ${
        isDark ? 'border-border-dark bg-black' : 'border-[#DDDDDD] bg-surface-light'
      }`}
    >
      <div className="border-b border-theme px-5 py-6">
        <Link to="/" className="flex items-center gap-3">
          <HaliteLogo className="h-10 w-10" />
          <div>
            <BrandName className="text-xl text-accent" />
            <p className="font-sans text-xs text-secondary">Knowledge Graph</p>
          </div>
        </Link>
        <DomainSwitcher />
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {navItems.map(({ to, label, icon: Icon, badge }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-md px-3 py-2.5 font-sans text-sm font-medium transition ${
                isActive
                  ? `border-l-[3px] border-accent pl-[9px] ${isDark ? 'text-[#F5F5F5]' : 'text-[#0A0A0A]'}`
                  : 'border-l-[3px] border-transparent text-[#888888] hover:text-primary'
              }`
            }
          >
            <Icon className="h-5 w-5 shrink-0" />
            <span className="flex-1">{label}</span>
            {badge && alertCount > 0 && (
              <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40">
                {alertCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-theme p-4">
        <p className="font-sans text-xs text-[#555555]">
          {domain === 'maintenance' 
            ? 'Service history intelligence for maintenance teams'
            : 'Institutional memory for software teams'}
        </p>
      </div>
    </aside>
  );
}
