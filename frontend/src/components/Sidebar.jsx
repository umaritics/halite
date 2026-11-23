import { NavLink, Link, useNavigate } from 'react-router-dom';
import { ArrowRightOnRectangleIcon } from '@heroicons/react/24/outline';
import HaliteLogo from './HaliteLogo';
import BrandName from './BrandName';
import { useTheme } from '../context/ThemeContext';
import { useAuth } from '../context/AuthContext';
import { featureNav } from '../app/registry';

// Navigation comes from the feature manifests (see src/app/README.md).
function NavBadge({ useBadge }) {
  const count = useBadge();
  if (!count || count <= 0) return null;
  return (
    <span
      aria-label={`${count} records awaiting review`}
      className="absolute right-0 top-0 flex h-5 min-w-5 md:static items-center justify-center rounded-full bg-accent/20 px-1.5 text-xs font-semibold text-accent ring-1 ring-accent/40"
    >
      {count}
    </span>
  );
}

function NavItem({ item, isDark }) {
  const { to, label, icon: Icon, useBadge } = item;
  return (
    <NavLink
      to={to}
      aria-label={label}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-md px-3 py-2.5 font-sans text-sm font-medium transition ${
          isActive
            ? `border-l-[3px] border-accent pl-[9px] ${isDark ? 'text-[#F5F5F5]' : 'text-[#0A0A0A]'}`
            : 'border-l-[3px] border-transparent text-[#888888] hover:text-primary'
        }`
      }
    >
      <Icon className="h-5 w-5 shrink-0" />
      <span className="sr-only md:not-sr-only md:flex-1">{label}</span>
      {useBadge && <NavBadge useBadge={useBadge} label={label} />}
    </NavLink>
  );
}

export default function Sidebar() {
  const { isDark } = useTheme();
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const visibleItems = featureNav.filter(
    item => !item.roles?.length || item.roles.includes(user?.role),
  );

  const handleSignOut = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside
      className={`flex h-full w-16 shrink-0 flex-col border-r md:w-64 ${
        isDark ? 'border-border-dark bg-black' : 'border-[#DDDDDD] bg-surface-light'
      }`}
    >
      <div className="border-b border-theme px-3 py-4 md:px-5 md:py-6">
        <Link to="/app/home" className="flex items-center gap-3">
          <HaliteLogo className="h-10 w-10" />
          <div className="hidden md:block">
            <BrandName className="text-xl text-accent" />
            <p className="font-sans text-xs text-secondary">Maintenance Intelligence</p>
          </div>
        </Link>
      </div>

      <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2 md:p-3">
        {visibleItems.map(item => (
          <NavItem key={item.to} item={item} isDark={isDark} />
        ))}
      </nav>

      <div className="border-t border-theme p-2 space-y-3 md:p-4">
        {isAuthenticated && user ? (
          <div className="space-y-2.5">
            <div className="hidden items-center justify-between gap-2 md:flex">
              <span className="truncate font-sans text-xs font-medium text-primary">
                {user.full_name}
              </span>
              <span className="rounded bg-accent/15 px-1.5 py-0.5 font-mono text-[10px] font-medium text-accent">
                {user.role}
              </span>
            </div>
            <p className="hidden truncate font-mono text-[11px] text-secondary md:block">{user.email}</p>
            <button
              type="button"
              onClick={handleSignOut}
              className="halite-btn-ghost w-full py-1.5 text-xs justify-center"
            >
              <ArrowRightOnRectangleIcon className="h-4 w-4" />
              <span className="sr-only md:not-sr-only">Sign out</span>
            </button>
          </div>
        ) : (
          <p className="sr-only font-sans text-xs text-[#555555] md:not-sr-only">
            Service history intelligence for maintenance teams
          </p>
        )}
      </div>
    </aside>
  );
}
