import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import Settings from '../pages/Settings';
import * as client from '../api/client';

vi.mock('../context/ThemeContext', () => ({
  useTheme: () => ({ theme: 'dark', toggleTheme: vi.fn(), isDark: true }),
}));

vi.mock('../api/client', () => ({
  healthAPI: { check: vi.fn() },
  maintenanceAPI: { analysisStatus: vi.fn() },
}));

const baseHealth = {
  graph_mode: 'neo4j',
  llm_mode: 'live',
  model: 'openai/gpt-oss-120b',
  maintenance_record_count: 2079,
  maint_threshold: 0.5,
};

const row = (label) => screen.getByText(label).closest('div');

describe('Settings system status mirrors /api/health', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    client.maintenanceAPI.analysisStatus.mockResolvedValue({
      data: { total: 2079, unscored: 17, scored: 2058, needs_review: 4, reviewed: 0 },
    });
  });

  it('shows the runtime-honesty fields the backend reports', async () => {
    client.healthAPI.check.mockResolvedValue({
      data: {
        ...baseHealth,
        maintenance_corpus_loaded: true,
        using_memory_graph: false,
        neo4j_configured: true,
        groq_configured: true,
        demo_mode: false,
        fallback_invocations: 0,
        git_sha: 'b14c8eca972b69ff42c8fb76a6210a616191f8da',
      },
    });
    render(<Settings />);

    await waitFor(() => screen.getByText('Corpus Loaded'));
    expect(row('Corpus Loaded')).toHaveTextContent('Yes');
    expect(row('In-Memory Graph')).toHaveTextContent('No');
    expect(row('Neo4j Configured')).toHaveTextContent('Yes');
    expect(row('Groq Configured')).toHaveTextContent('Yes');
    expect(row('Demo Mode')).toHaveTextContent('No');
    expect(row('Model Fallbacks Used')).toHaveTextContent('0');
    expect(row('Deployed Version')).toHaveTextContent('b14c8eca');
    expect(row('Deployed Version')).not.toHaveTextContent('b14c8eca9');
  });

  it('flags a degraded runtime instead of presenting it as healthy', async () => {
    client.healthAPI.check.mockResolvedValue({
      data: { ...baseHealth, graph_mode: 'memory', maintenance_corpus_loaded: false, using_memory_graph: true, groq_configured: false, fallback_invocations: 3 },
    });
    render(<Settings />);

    await waitFor(() => screen.getByText('Corpus Loaded'));
    expect(row('Corpus Loaded')).toHaveTextContent('No');
    expect(row('Corpus Loaded').querySelector('dd')).toHaveClass('text-amber-500');
    expect(row('In-Memory Graph').querySelector('dd')).toHaveClass('text-amber-500');
    expect(row('Groq Configured').querySelector('dd')).toHaveClass('text-amber-500');
    expect(row('Model Fallbacks Used').querySelector('dd')).toHaveClass('text-amber-500');
  });

  it('omits fields the backend did not send rather than showing them as "No"', async () => {
    client.healthAPI.check.mockResolvedValue({ data: baseHealth });
    render(<Settings />);

    await waitFor(() => screen.getByText('Graph Mode'));
    ['Corpus Loaded', 'In-Memory Graph', 'Neo4j Configured', 'Groq Configured', 'Demo Mode', 'Model Fallbacks Used', 'Deployed Version']
      .forEach((label) => expect(screen.queryByText(label)).toBeNull());
  });

  it('does not show a version when the backend reports "unknown"', async () => {
    client.healthAPI.check.mockResolvedValue({ data: { ...baseHealth, git_sha: 'unknown' } });
    render(<Settings />);
    await waitFor(() => screen.getByText('Graph Mode'));
    expect(screen.queryByText('Deployed Version')).toBeNull();
  });

  it('exposes no control that can wipe the graph', async () => {
    client.healthAPI.check.mockResolvedValue({ data: baseHealth });
    render(<Settings />);
    await waitFor(() => screen.getByText('Graph Mode'));
    expect(screen.queryByText(/reset knowledge graph/i)).toBeNull();
  });

  it('says plainly when the backend is unreachable', async () => {
    client.healthAPI.check.mockRejectedValue(new Error('Network Error'));
    render(<Settings />);
    await waitFor(() => screen.getByText(/Backend not reachable/));
  });
});
