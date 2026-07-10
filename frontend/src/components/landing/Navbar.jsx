import { Link } from 'react-router-dom';
import { MoonIcon, SunIcon } from '@heroicons/react/24/outline';
import { useTheme } from '../../context/ThemeContext';
import BrandName from '../BrandName';
import HaliteLogo from '../HaliteLogo';

const navLinks = [
  { label: 'About', href: '#about' },
  { label: 'Features', href: '#features' },
  { label: 'Decisions', to: '/app/decisions' },
  { label: 'Graph', to: '/app/graph' },
  { label: 'Docs', href: '#how-it-works' },
];

export default function Navbar() {
  const { isDark, toggleTheme } = useTheme();

  return (
    <nav
      className={`fixed top-0 z-50 flex h-14 w-full items-center border-b px-6 backdrop-blur-[12px] ${
        isDark
          ? 'border-border-dark bg-black/85'
          : 'border-[#DDDDDD] bg-white/85'
      }`}
    >
      <Link to="/" className="flex items-center gap-3">
        <HaliteLogo className="h-9 w-9" />
        <BrandName className="text-2xl text-accent" />
      </Link>

      <div className="absolute left-1/2 hidden -translate-x-1/2 items-center gap-8 md:flex">
        {navLinks.map((link) =>
          link.to ? (
            <Link
              key={link.label}
              to={link.to}
              className="font-sans text-sm text-[#888888] transition hover:text-primary"
            >
              {link.label}
            </Link>
          ) : (
            <a
              key={link.label}
              href={link.href}
              className="font-sans text-sm text-[#888888] transition hover:text-primary"
            >
              {link.label}
            </a>
          )
        )}
      </div>

      <div className="ml-auto flex items-center gap-3">
        <button
          onClick={toggleTheme}
          className="rounded-md p-2 text-[#888888] transition hover:text-accent"
          aria-label="Toggle theme"
        >
          {isDark ? <SunIcon className="h-5 w-5" /> : <MoonIcon className="h-5 w-5" />}
        </button>
        <Link to="/app/chat" className="halite-btn-outline text-sm">
          Get Demo
        </Link>
      </div>
    </nav>
  );
}
