import { Link } from 'react-router-dom';
import BackgroundGraph from '../components/landing/BackgroundGraph';
import CrystalMount from '../components/landing/CrystalMount';
import Footer from '../components/landing/Footer';
import BrandName from '../components/BrandName';
import Navbar from '../components/landing/Navbar';
import { useTheme } from '../context/ThemeContext';

const features = [
  {
    title: 'Knowledge Graph',
    body: 'Every component, decision, and file is a node. Relationships are first-class citizens.',
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
    title: 'Ask Your Codebase',
    body: 'Chat interface grounded in your project\'s actual architecture, not generic AI guesses.',
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
    title: 'Decision Invalidation',
    body: 'When code changes, Halite flags every architectural decision that may no longer hold.',
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
    desc: 'Connect your repo, docs, and meeting transcripts.',
  },
  {
    num: '2',
    label: 'Map',
    desc: 'Halite builds a live knowledge graph of all components and decisions.',
  },
  {
    num: '3',
    label: 'Query',
    desc: 'Ask questions in plain language. Get answers with citations.',
  },
  {
    num: '4',
    label: 'Monitor',
    desc: 'Receive alerts when decisions become stale after code changes.',
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
            <p className="eyebrow">INSTITUTIONAL MEMORY FOR SOFTWARE TEAMS</p>
            <h1 className="font-brand mt-4 text-[56px] leading-[1.1] text-primary">
              Your codebase has a memory. Now it speaks.
            </h1>
            <p className="mt-6 font-sans text-base text-secondary">
              Halite captures every architectural decision, component dependency, and
              reasoning thread — and surfaces them the moment your team needs them.
            </p>
            <div className="mt-8 flex flex-wrap gap-4">
              <Link
                to="/app/chat"
                className="rounded-md bg-accent px-7 py-3 font-sans text-sm font-medium text-black transition hover:bg-accent-hover"
              >
                Request Demo
              </Link>
              <Link
                to="/app/graph"
                className={`rounded-md border px-7 py-3 font-sans text-sm font-medium transition hover:border-accent hover:text-accent ${
                  isDark ? 'border-[#333333] text-[#F5F5F5]' : 'border-[#BBBBBB] text-[#0A0A0A]'
                }`}
              >
                Explore the Graph
              </Link>
            </div>
            <p className="mt-6 font-sans text-xs text-[#555555]">
              ✦ No setup required · ✦ Works with any repo · ✦ AI-native from day one
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
            Every decision. Every reason. Always findable.
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
            From commit to institutional memory in seconds.
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
          Upload a document or connect your repo to try a live demo.
        </p>
        <Link
          to="/app/chat"
          className="mt-8 inline-block rounded-lg bg-accent px-10 py-4 font-sans text-lg font-medium text-black transition hover:bg-accent-hover"
        >
          Start Free Demo →
        </Link>
      </section>

      <Footer />
    </div>
  );
}
