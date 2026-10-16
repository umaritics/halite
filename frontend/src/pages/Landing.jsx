import { Link } from 'react-router-dom';
import BackgroundGraph from '../components/landing/BackgroundGraph';
import CrystalMount from '../components/landing/CrystalMount';
import Footer from '../components/landing/Footer';
import BrandName from '../components/BrandName';
import Navbar from '../components/landing/Navbar';
import { useTheme } from '../context/ThemeContext';

const features = [
  {
    title: 'Asset Knowledge Graph',
    body: 'Assets, service records and components are nodes. Every record keeps its date and its original report ID.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8" aria-hidden="true">
        <circle cx="6" cy="6" r="2.5" stroke="#E8650A" strokeWidth="1.5" />
        <circle cx="18" cy="6" r="2.5" stroke="#E8650A" strokeWidth="1.5" />
        <circle cx="12" cy="18" r="2.5" stroke="#E8650A" strokeWidth="1.5" />
        <line x1="8" y1="7" x2="16" y2="7" stroke="#E8650A" strokeWidth="1" opacity="0.6" />
        <line x1="7" y1="8" x2="11" y2="16" stroke="#E8650A" strokeWidth="1" opacity="0.6" />
        <line x1="17" y1="8" x2="13" y2="16" stroke="#E8650A" strokeWidth="1" opacity="0.6" />
      </svg>
    ),
  },
  {
    title: 'Evidence-Linked Diagnostics',
    body: 'Describe a symptom and get ranked investigation checks, each tied to the historical records that support it.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8" aria-hidden="true">
        <path
          d="M4 5h16v10H8l-4 4V5z"
          stroke="#E8650A"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <line x1="8" y1="9" x2="16" y2="9" stroke="#E8650A" strokeWidth="1" opacity="0.6" />
        <line x1="8" y1="12" x2="13" y2="12" stroke="#E8650A" strokeWidth="1" opacity="0.6" />
      </svg>
    ),
  },
  {
    title: 'Correction-Aware Review',
    body: 'When a later report corrects an earlier one, Halite flags it and scores its confidence. Uncertain cases go to a human reviewer.',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-8 w-8" aria-hidden="true">
        <path
          d="M12 3l9 16H3L12 3z"
          stroke="#E8650A"
          strokeWidth="1.5"
          strokeLinejoin="round"
        />
        <line x1="12" y1="9" x2="12" y2="13" stroke="#E8650A" strokeWidth="1.5" />
        <circle cx="12" cy="16.5" r="0.75" fill="#E8650A" />
      </svg>
    ),
  },
];

const steps = [
  {
    num: '1',
    label: 'Ingest',
    desc: 'Load FAA Service Difficulty Reports into the graph.',
  },
  {
    num: '2',
    label: 'Map',
    desc: 'Records link to their asset and component in dated order.',
  },
  {
    num: '3',
    label: 'Diagnose',
    desc: 'Describe a symptom. Get ranked checks with cited source records.',
  },
  {
    num: '4',
    label: 'Review',
    desc: 'Uncertain corrections are routed to a human review queue.',
  },
];

export default function Landing() {
  const { isDark } = useTheme();

  return (
    <div className="relative min-h-screen bg-page">
      <BackgroundGraph />
      <Navbar />

      {/* Hero */}
      <section className="relative z-10 flex min-h-screen items-center px-6 pt-14">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-2">
          <div id="about">
            <p className="eyebrow">MAINTENANCE DIAGNOSTICS AND ASSET INTELLIGENCE</p>
            <h1 className="font-brand mt-4 text-[56px] leading-[1.1] text-primary">
              Years of service records. One traceable place to start.
            </h1>
            <p className="mt-6 font-sans text-base text-secondary">
              Halite links aircraft service reports into a knowledge graph, flags records
              that later reports corrected, and ranks what to investigate next, with every
              suggestion tied back to its source record.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to="/app/assets"
                className="rounded-md bg-accent px-7 py-3 font-sans text-sm font-medium text-black transition hover:bg-accent-hover"
              >
                Open the Workspace
              </Link>
              <Link
                to="/app/diagnostics"
                className={`rounded-md border px-7 py-3 font-sans text-sm font-medium transition hover:border-accent hover:text-accent ${
                  isDark ? 'border-[#333333] text-[#F5F5F5]' : 'border-[#BBBBBB] text-[#0A0A0A]'
                }`}
              >
                Run a Diagnostic
              </Link>
            </div>
            <p className="mt-6 font-sans text-xs text-[#555555]">
              ✦ Built on FAA Service Difficulty Reports · ✦ Cited record IDs verified against the graph · ✦ Decision support, not a repair authority
            </p>
          </div>
          <div className="flex justify-center">
            <CrystalMount />
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="relative z-10 px-6 py-[100px]">
        <div className="mx-auto max-w-6xl">
          <p className="eyebrow">WHAT HALITE DOES</p>
          <h2 className="font-brand mt-3 text-[40px] text-primary">
            Every suggestion. Every source. Always traceable.
          </h2>
          <div className="mt-12 grid gap-6 md:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="feature-card">
                <div className="mb-4">{f.icon}</div>
                <h3 className="font-brand text-lg text-primary">{f.title}</h3>
                <p className="mt-2 font-sans text-sm text-secondary">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* About anchor + How it works */}
      <section
        id="how-it-works"
        className={`relative z-10 px-6 py-20 ${
          isDark ? 'bg-section-dark' : 'bg-section-light'
        }`}
      >
        <div id="how-it-works" className="mx-auto max-w-6xl">
          <h2 className="font-brand text-[36px] text-primary">
            From service report to traceable evidence.
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {steps.map((step) => (
              <div key={step.num} className="relative">
                <span
                  className="font-brand pointer-events-none absolute -top-4 left-0 text-[64px] leading-none text-accent opacity-15"
                  aria-hidden="true"
                >
                  {step.num}
                </span>
                <div className="relative pt-10">
                  <h3 className="font-sans text-lg font-semibold text-primary">{step.label}</h3>
                  <p className="mt-2 font-sans text-sm text-secondary">{step.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="relative z-10 bg-page px-6 py-[120px] text-center">
        <h2 className="font-brand text-[48px] text-primary">
          See <BrandName className="text-accent" /> in action.
        </h2>
        <p className="mx-auto mt-4 max-w-lg font-sans text-base text-secondary">
          Open an asset, describe a symptom, and follow each citation back to its source record.
          Approved maintenance documentation and qualified personnel remain authoritative.
        </p>
        <Link
          to="/app/assets"
          className="mt-8 inline-block rounded-lg bg-accent px-10 py-4 font-sans text-lg font-medium text-black transition hover:bg-accent-hover"
        >
          Open the Workspace →
        </Link>
      </section>

      <Footer />
    </div>
  );
}
