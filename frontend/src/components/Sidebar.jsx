import { NavLink, Link } from 'react-router-dom';
import {
  CircleStackIcon,
  DocumentArrowUpIcon,
  Cog6ToothIcon,
  MagnifyingGlassIcon,
  WrenchScrewdriverIcon,
  ClipboardDocumentListIcon,
  InboxStackIcon
} from '@heroicons/react/24/outline';
import HaliteLogo from './HaliteLogo';
import BrandName from './BrandName';
import { useTheme } from '../context/ThemeContext';

// Mid-I: maintenance-only navigation. Software-domain screens (Chat, Decisions,
// Alerts, software Ingest) are intentionally not linked from here.
const NAV_ITEMS = [
  { to: '/app/assets', label: 'Assets', icon: WrenchScrewdriverIcon },
  { to: '/app/records', label: 'Service Records', icon: ClipboardDocumentListIcon },
  { to: '/app/diagnostics', label: 'Diagnostics', icon: MagnifyingGlassIcon },
  { to: '/app/review-queue', label: 'Review Queue', icon: InboxStackIcon, badge: true },
  { to: '/app/maintenance-ingest', label: 'Ingest', icon: DocumentArrowUpIcon },
  { to: '/app/graph', label: 'Knowledge Graph', icon: CircleStackIcon },
  { to: '/app/settings', label: 'Settings', icon: Cog6ToothIcon },
];

export default function Sidebar({ reviewCount = 0 }) {
  const { isDark } = useTheme();

  return (
    <aside
      className={`flex h-full w-64 flex-col border-r ${
        isDark ? 'border-border-dark bg-black' : 'border-[#DDDDDD] bg-surface-light'
      }`}
    >
      <div className="border-b border-theme px-5 py-6">
        <Link to="/app/assets" className="flex items-center gap-3">
          <HaliteLogo className="h-10 w-10" />
          <div>
            <BrandName className="text-xl text-accent" />
            <p className="font-sans text-xs text-secondary">Maintenance Intelligence</p>
          </div>
        </Link>
      </div>

      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon, badge }) => (
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
            {badge && reviewCount > 0 && (
              <span
                aria-label={`${reviewCount} records awaiting review`}
                className="flex h-5 min-w-5 items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40"
              >
                {reviewCount}
              </span>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-theme p-4">
        <p className="font-sans text-xs text-[#555555]">
          Service history intelligence for maintenance teams
        </p>
      </div>
    </aside>
  );
}
