import React from 'react';
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import Diagnostics from '../pages/Diagnostics';
import * as client from '../api/client';

vi.mock('../api/client', () => ({
  maintenanceAPI: {
    assets: vi.fn(),
    assetHistory: vi.fn(),
    records: vi.fn(),
    diagnose: vi.fn(),
    copilotTurn: vi.fn(),
  },
}));

const assets = [{ id: '1', tail_number: 'N813SK', record_count: 3 }];
const originalAnimate = HTMLElement.prototype.animate;
const originalMatchMedia = window.matchMedia;
let animateMock;
const baseTurn = {
  session_id: 'session-1',
  reply: 'Inspect the drag angle using SWIA2024010100001.',
  case_state: {
    symptoms: ['drag angle crack'], observations: [], checks_done: [], ruled_out: [], open_questions: [],
  },
  ranked_checks: [{
    rank: 1, part_name: 'DRAG ANGLE', score: 0.42, evidence_count: 1,
    evidence_record_ids: ['SWIA2024010100001'], sources: ['fleet_match'],
  }],
  ranking_delta: { moved_up: [], moved_down: [], new: [{ part_name: 'DRAG ANGLE', rank: 1 }], dropped: [], newly_cited_records: ['SWIA2024010100001'] },
  evidence: [{ record_id: 'SWIA2024010100001', asset_id: 'N813SK', occurred_at: '2024-01-01', part_name: 'DRAG ANGLE', text: 'Crack reported at the drag angle during inspection.', is_superseded: false }],
  citation_validation: { valid_ids: ['SWIA2024010100001'], invalid_ids: [], all_valid: true },
  llm_status: 'available',
  warnings: [],
};

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.hash}</output>;
}

function renderPage(withLocation = false) {
  return render(
    <MemoryRouter initialEntries={['/app/diagnostics']}>
      <Diagnostics />
      {withLocation && <LocationProbe />}
    </MemoryRouter>
  );
}

async function send(text) {
  fireEvent.change(screen.getByLabelText('Message'), { target: { value: text } });
  fireEvent.click(screen.getByRole('button', { name: 'Send' }));
}

function checksFor(...partNames) {
  return partNames.map((partName, index) => ({
    ...baseTurn.ranked_checks[0],
    rank: index + 1,
    part_name: partName,
    score: 0.9 - (index * 0.05),
  }));
}

describe('Diagnostics copilot', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    window.localStorage.clear();
    client.maintenanceAPI.assets.mockResolvedValue({ data: assets });
    client.maintenanceAPI.assetHistory.mockResolvedValue({ data: { records: [] } });
    client.maintenanceAPI.records.mockResolvedValue({ data: { items: [], total: 0, next: null } });
    animateMock = vi.fn(() => ({ cancel: vi.fn() }));
    HTMLElement.prototype.animate = animateMock;
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
  });

  afterEach(() => {
    if (originalAnimate) HTMLElement.prototype.animate = originalAnimate;
    else delete HTMLElement.prototype.animate;
    if (originalMatchMedia) window.matchMedia = originalMatchMedia;
    else delete window.matchMedia;
  });

  it('defaults to All fleet and carries accumulated case state across turns', async () => {
    const secondTurn = {
      ...baseTurn,
      reply: 'The pump moved up after the new observation.',
      case_state: { ...baseTurn.case_state, observations: ['hydraulic leak'] },
      ranking_delta: { moved_up: [{ part_name: 'PUMP', from_rank: 3, to_rank: 1 }], moved_down: [], new: [], dropped: [], newly_cited_records: [] },
      ranked_checks: [{ ...baseTurn.ranked_checks[0], part_name: 'PUMP', rank: 1 }],
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: secondTurn });

    renderPage();
    expect(screen.getByLabelText('Aircraft filter')).toHaveValue('');
    expect(screen.getByRole('option', { name: 'All fleet' })).toBeDefined();

    await send('crack found on drag angle');
    const firstNarrative = await screen.findByText(/Inspect the drag angle/);
    const initialUpdates = screen.getByRole('region', { name: 'Investigation Updates' });
    expect(within(initialUpdates).getByText('Initial ranking established')).toBeDefined();
    expect(within(initialUpdates).getByText(/1 ranked component/)).toBeDefined();
    expect(within(initialUpdates).getByText(/1 displayed below/)).toBeDefined();
    expect(screen.queryByText('Newly introduced')).toBeNull();
    expect(initialUpdates.compareDocumentPosition(firstNarrative) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    await send('hydraulic leak observed');
    await screen.findByText('The pump moved up after the new observation.');
    const updates = screen.getAllByRole('region', { name: 'Investigation Updates' }).at(-1);
    expect(within(updates).getByText('Moved up')).toBeDefined();
    expect(within(updates).getByText('Rank 3 → Rank 1')).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenLastCalledWith(expect.objectContaining({
      session_id: 'session-1',
      message: 'hydraulic leak observed',
      case_state: baseTurn.case_state,
    }));
  });

  it('shows upward, downward, new, and dropped ranking changes with exact positions', async () => {
    const changedTurn = {
      ...baseTurn,
      reply: 'The deterministic ranking changed.',
      ranked_checks: [
        { ...baseTurn.ranked_checks[0], part_name: 'SUPPORT ANGLE', rank: 4 },
        { ...baseTurn.ranked_checks[0], part_name: 'DRAG ANGLE', rank: 5 },
        { ...baseTurn.ranked_checks[0], part_name: 'SEAL', rank: 3 },
      ],
      ranking_delta: {
        moved_up: [{ part_name: 'SUPPORT ANGLE', from_rank: 13, to_rank: 4 }],
        moved_down: [{ part_name: 'DRAG ANGLE', from_rank: 1, to_rank: 5 }],
        new: [{ part_name: 'SEAL', rank: 3 }],
        dropped: [{ part_name: 'STRINGER SPLICE', from_rank: 12 }],
        newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: changedTurn });

    renderPage();
    await send('hydraulic leak changed the ranking');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });

    expect(within(updates).getByText('Moved up')).toBeDefined();
    expect(within(updates).getByText('SUPPORT ANGLE')).toBeDefined();
    expect(within(updates).getByText('Rank 13 → Rank 4')).toBeDefined();
    expect(within(updates).getByText('Moved down')).toBeDefined();
    expect(within(updates).getByText('Rank 1 → Rank 5')).toBeDefined();
    expect(within(updates).getByText('Newly introduced')).toBeDefined();
    expect(within(updates).getByText('Entered at rank 3')).toBeDefined();

    const more = within(updates).getByText('Show 1 more ranking update');
    expect(more.closest('details')).not.toHaveAttribute('open');
    fireEvent.click(more);
    expect(within(updates).getByText('Dropped from ranking')).toBeDefined();
    expect(within(updates).getByText('STRINGER SPLICE')).toBeDefined();
    expect(within(updates).getByText('Previously rank 12 · no longer ranked')).toBeDefined();
  });

  it('summarises an initial 21-component ranking with ten displayed checks and collapsed evidence', async () => {
    const rankedChecks = Array.from({ length: 10 }, (_, index) => ({
      ...baseTurn.ranked_checks[0],
      part_name: `COMPONENT ${index + 1}`,
      rank: index + 1,
    }));
    const introduced = [
      ...rankedChecks.map(check => ({ part_name: check.part_name, rank: check.rank })),
      ...Array.from({ length: 11 }, (_, index) => ({
        part_name: index === 9 ? 'STRINGER SPLICE' : index === 10 ? 'SUPPORT ANGLE' : `COMPONENT ${index + 11}`,
        rank: index + 11,
      })),
    ];
    const evidenceIds = Array.from({ length: 8 }, (_, index) => `SWIA20240101000${index + 10}`);
    const evidence = evidenceIds.map(recordId => ({
      ...baseTurn.evidence[0], record_id: recordId,
    }));
    client.maintenanceAPI.copilotTurn.mockResolvedValue({
      data: {
        ...baseTurn,
        ranked_checks: rankedChecks,
        evidence,
        ranking_delta: { moved_up: [], moved_down: [], new: introduced, dropped: [], newly_cited_records: evidenceIds },
      },
    });

    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('initial visual QA fixture');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });
    expect(within(updates).getByText('Initial ranking established')).toBeDefined();
    expect(within(updates).getByText(/21 ranked components/)).toBeDefined();
    expect(within(updates).getByText(/10 displayed below/)).toBeDefined();
    expect(within(updates).getByText(/8 newly cited evidence records/)).toBeDefined();
    expect(within(updates).getByText('COMPONENT 1')).toBeDefined();
    expect(within(updates).getByText('COMPONENT 2')).toBeDefined();
    expect(within(updates).getByText('COMPONENT 3')).toBeDefined();
    expect(within(updates).queryByText('COMPONENT 4')).toBeNull();
    expect(within(updates).queryByText('Newly introduced')).toBeNull();

    const disclosure = within(updates).getByText('View 8 evidence record IDs');
    const evidenceDetails = disclosure.closest('details');
    expect(evidenceDetails).not.toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[0] })).toBeDefined();
    expect(within(updates).getAllByText(evidenceIds[0])).toHaveLength(1);
    fireEvent.click(disclosure);
    expect(evidenceDetails).toHaveAttribute('open');
    fireEvent.click(within(evidenceDetails).getByRole('button', { name: evidenceIds[0] }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/app/asset-history/1#${evidenceIds[0]}`);
  });

  it('shows three newly cited links and puts additional records in a collapsed disclosure', async () => {
    const evidenceIds = Array.from({ length: 7 }, (_, index) => `SWIA20240202000${index + 10}`);
    const evidenceTurn = {
      ...baseTurn,
      reply: 'Additional supporting evidence was found.',
      evidence: evidenceIds.map(recordId => ({ ...baseTurn.evidence[0], record_id: recordId })),
      ranking_delta: { moved_up: [], moved_down: [], new: [], dropped: [], newly_cited_records: evidenceIds },
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: evidenceTurn });

    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('add the latest supporting record');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });

    expect(within(updates).getByText('Ranking unchanged; new supporting records were added.')).toBeDefined();
    expect(within(updates).getByText(/7 newly cited evidence records/)).toBeDefined();
    const visibleRecords = within(updates).getByLabelText('Newly cited evidence records');
    expect(within(visibleRecords).getAllByRole('button')).toHaveLength(3);
    expect(within(visibleRecords).getByRole('button', { name: evidenceIds[0] })).toBeDefined();
    expect(within(updates).getAllByText(evidenceIds[0])).toHaveLength(1);

    const disclosure = within(updates).getByText('Show 4 more evidence records');
    const evidenceDetails = disclosure.closest('details');
    expect(evidenceDetails).not.toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[3] })).toBeDefined();
    fireEvent.click(disclosure);
    expect(evidenceDetails).toHaveAttribute('open');
    expect(within(evidenceDetails).getByRole('button', { name: evidenceIds[3] })).toBeDefined();
    fireEvent.click(within(visibleRecords).getByRole('button', { name: evidenceIds[0] }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/app/asset-history/1#${evidenceIds[0]}`);
  });

  it('shows a subtle unchanged state when ranking and evidence do not change', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({
      data: {
        ...baseTurn,
        ranking_delta: { moved_up: [], moved_down: [], new: [], dropped: [], newly_cited_records: [] },
      },
    });

    renderPage();
    await send('no new observation');
    const updates = await screen.findByRole('region', { name: 'Investigation Updates' });
    expect(within(updates).getByText('No rank change')).toBeDefined();
    expect(within(updates).getByText('Ranking unchanged after this update.')).toBeDefined();
  });

  it('shows model-unavailable output and retries a network failure without a blank success', async () => {
    client.maintenanceAPI.copilotTurn
      .mockRejectedValueOnce({ code: 'ERR_NETWORK', message: 'Network Error', request: {} })
      .mockResolvedValueOnce({ data: { ...baseTurn, reply: null, llm_status: 'unavailable' } });

    renderPage();
    await send('crack found');
    await screen.findByText('Cannot reach the Halite API');
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await screen.findByText('Language model unavailable');
    expect(screen.getByText(/No narrative was invented/)).toBeDefined();
    expect(screen.getAllByText(/DRAG ANGLE/).length).toBeGreaterThan(0);
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenCalledTimes(2);
  });

  it('saves, resumes, and deletes a local session', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    renderPage();
    await send('crack found on drag angle');
    await screen.findByText(/Inspect the drag angle/);

    fireEvent.click(screen.getByRole('button', { name: 'Save session' }));
    expect(screen.getByRole('button', { name: 'crack found on drag angle' })).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'New investigation' }));
    expect(screen.getByText(/Start an evidence-grounded investigation/)).toBeDefined();

    fireEvent.click(screen.getByRole('button', { name: 'crack found on drag angle' }));
    expect(screen.getByText(/Inspect the drag angle/)).toBeDefined();
    fireEvent.click(screen.getByRole('button', { name: 'Delete crack found on drag angle' }));
    expect(screen.queryByRole('button', { name: 'crack found on drag angle' })).toBeNull();
  });

  it('deep-links evidence to the matching aircraft history record', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    renderPage(true);
    await waitFor(() => expect(client.maintenanceAPI.assets).toHaveBeenCalled());
    await send('crack found');
    await screen.findByText(/Inspect the drag angle/);

    fireEvent.click(screen.getByText('View 1 evidence record ID'));
    fireEvent.click(screen.getAllByRole('button', { name: 'SWIA2024010100001' })[0]);
    expect(screen.getByTestId('location')).toHaveTextContent('/app/asset-history/1#SWIA2024010100001');
  });

  it('shows an empty live-ranking state in a responsive workspace before a completed turn', () => {
    renderPage();
    const layout = screen.getByTestId('copilot-layout');
    const controls = screen.getByRole('region', { name: 'Investigation controls' });
    const workspace = screen.getByTestId('copilot-workspace');
    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    const conversation = screen.getByRole('region', { name: 'Diagnostic conversation' });

    expect(within(liveRanking).getByText('No completed ranking yet')).toBeDefined();
    expect(layout).toHaveClass('flex', 'flex-col', 'gap-4');
    expect(layout).not.toHaveClass('space-y-4', 'xl:space-y-0');
    expect(layout.children[0]).toBe(controls);
    expect(layout.children[1]).toBe(workspace);
    expect(controls).toHaveClass('shrink-0');
    expect(workspace).toHaveClass('grid', 'min-w-0', 'xl:min-h-0', 'xl:flex-1', 'xl:overflow-hidden', 'xl:grid-cols-[minmax(0,1fr)_23rem]');
    expect(workspace).not.toHaveClass('xl:mt-4');
    expect(liveRanking.parentElement).toHaveClass('order-1', 'xl:h-full', 'xl:min-h-0', 'xl:overflow-y-auto');
    expect(screen.getByRole('main')).toHaveClass('order-2', 'min-w-0', 'xl:min-h-0', 'xl:overflow-hidden');
    expect(screen.getByRole('main')).toHaveClass('xl:row-start-1');
    expect(liveRanking.parentElement).toHaveClass('xl:row-start-1');
    expect(conversation.parentElement).toBe(screen.getByRole('main'));
  });

  it('preserves independent scroll positions without moving controls into either scroll container', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    renderPage();
    await send('populate the workspace');
    await screen.findByText(/Inspect the drag angle/);

    const controls = screen.getByRole('region', { name: 'Investigation controls' });
    const workspace = screen.getByTestId('copilot-workspace');
    const history = screen.getByRole('log', { name: 'Conversation history' });
    const investigationRail = screen.getByRole('complementary', { name: 'Investigation workspace panels' });
    history.scrollTop = 48;
    investigationRail.scrollTop = 72;
    fireEvent.scroll(history);
    fireEvent.scroll(investigationRail);

    fireEvent.change(screen.getByLabelText('Message'), { target: { value: 'draft remains visible' } });
    expect(history.scrollTop).toBe(48);
    expect(investigationRail.scrollTop).toBe(72);
    expect(controls.parentElement).toBe(workspace.parentElement);
    expect(controls.contains(history)).toBe(false);
    expect(controls.contains(investigationRail)).toBe(false);
  });

  it('keeps the composer outside the accessible scrolling history and exposes the investigation rail', () => {
    renderPage();
    const history = screen.getByRole('log', { name: 'Conversation history' });
    const composer = screen.getByTestId('copilot-composer');
    const investigationRail = screen.getByRole('complementary', { name: 'Investigation workspace panels' });

    expect(history).toHaveAttribute('tabindex', '0');
    expect(history).toHaveAttribute('aria-live', 'polite');
    expect(history).toHaveClass('xl:overflow-y-auto', 'xl:overscroll-contain');
    expect(history).not.toContainElement(composer);
    expect(screen.getByRole('main')).toContainElement(composer);
    expect(investigationRail).toHaveAttribute('tabindex', '0');
    expect(investigationRail).toHaveClass('xl:overflow-y-auto', 'xl:overscroll-contain');
    expect(within(investigationRail).getByText('Case state')).toBeDefined();
  });

  it('follows successful turns only while the reader remains near the latest message', async () => {
    const secondTurn = {
      ...baseTurn,
      reply: 'Second response remains available without forcing a scroll.',
      ranked_checks: checksFor('SUPPORT ANGLE'),
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: secondTurn });
    const originalScrollTo = HTMLElement.prototype.scrollTo;
    const originalMatchMedia = window.matchMedia;
    const scrollTo = vi.fn();
    HTMLElement.prototype.scrollTo = scrollTo;
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });

    try {
      renderPage();
      const history = screen.getByRole('log', { name: 'Conversation history' });
      Object.defineProperties(history, {
        scrollHeight: { configurable: true, value: 1000 },
        clientHeight: { configurable: true, value: 400 },
        scrollTop: { configurable: true, writable: true, value: 600 },
      });
      fireEvent.scroll(history);
      scrollTo.mockClear();

      await send('first turn');
      await screen.findByText(/Inspect the drag angle/);
      await waitFor(() => expect(scrollTo).toHaveBeenCalledWith({ top: 1000, behavior: 'auto' }));

      history.scrollTop = 0;
      fireEvent.scroll(history);
      scrollTo.mockClear();
      await send('second turn while reading history');
      await screen.findByText(/Second response remains available/);
      expect(scrollTo).not.toHaveBeenCalled();
    } finally {
      if (originalScrollTo) HTMLElement.prototype.scrollTo = originalScrollTo;
      else delete HTMLElement.prototype.scrollTo;
      if (originalMatchMedia) window.matchMedia = originalMatchMedia;
      else delete window.matchMedia;
    }
  });

  it('shows the latest initial ranking, movement, actions, and an expandable remainder', async () => {
    const rankedChecks = checksFor('DRAG ANGLE', 'SUPPORT ANGLE', 'SEAL', 'PUMP', 'RIB', 'FRAME', 'SKIN');
    client.maintenanceAPI.copilotTurn.mockResolvedValue({
      data: {
        ...baseTurn,
        ranked_checks: rankedChecks,
        ranking_delta: {
          moved_up: [], moved_down: [], dropped: [], newly_cited_records: [],
          new: rankedChecks.map(check => ({ part_name: check.part_name, rank: check.rank })),
        },
      },
    });

    renderPage();
    await send('establish ranking');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    const visible = within(liveRanking).getByRole('list', { name: 'Current ranked checks' });

    expect(within(liveRanking).getByText('Latest')).toBeDefined();
    expect(within(visible).getAllByRole('listitem')).toHaveLength(5);
    expect(within(visible).getByText('Heuristic score 0.90')).toBeDefined();
    expect(within(visible).queryByText('Entered at rank 1')).toBeNull();
    expect(within(visible).getByText('DRAG ANGLE').closest('li')).toHaveAttribute('data-ranking-animation', 'none');
    expect(animateMock).not.toHaveBeenCalled();
    expect(within(liveRanking).getByRole('button', { name: 'Mark DRAG ANGLE done' })).toBeDefined();
    expect(within(liveRanking).getByRole('button', { name: 'Rule out DRAG ANGLE' })).toBeDefined();

    const disclosure = within(liveRanking).getByText('Show 2 more current checks');
    expect(disclosure).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(disclosure);
    expect(disclosure).toHaveAttribute('aria-expanded', 'true');
    expect(within(visible).getAllByRole('listitem')).toHaveLength(7);
  });

  it('selects a component independently and shows only its source-grounded evidence', async () => {
    const secondRecordId = 'SWIA2024020200002';
    const response = {
      ...baseTurn,
      case_state: { ...baseTurn.case_state, observations: ['Crack grows under load'] },
      ranked_checks: [
        baseTurn.ranked_checks[0],
        { ...baseTurn.ranked_checks[0], rank: 2, part_name: 'SUPPORT ANGLE', evidence_record_ids: [secondRecordId] },
      ],
      evidence: [
        baseTurn.evidence[0],
        { ...baseTurn.evidence[0], record_id: secondRecordId, part_name: 'SUPPORT ANGLE', text: 'Support angle deformation reported.' },
      ],
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: response });
    client.maintenanceAPI.assetHistory.mockResolvedValue({
      data: {
        records: [{
          ...baseTurn.evidence[0],
          part_condition: 'CRACKED',
          part_location: 'LH FUSELAGE',
          text: 'Original FAA maintenance narrative for the drag angle.',
        }],
      },
    });

    renderPage(true);
    await send('inspect component evidence');
    await screen.findByText(/Inspect the drag angle/);
    animateMock.mockClear();
    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    const select = within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' });
    select.focus();
    expect(select).toHaveFocus();
    fireEvent.click(select);
    expect(select).toHaveAttribute('aria-pressed', 'true');

    const inspector = within(liveRanking).getByRole('region', { name: 'Component evidence inspector' });
    expect(within(inspector).getByRole('heading', { name: 'DRAG ANGLE' })).toBeDefined();
    expect(within(inspector).getByText('Rank 1')).toBeDefined();
    expect(within(inspector).getByText('Crack grows under load')).toBeDefined();
    expect(within(inspector).getByText('SWIA2024010100001')).toBeDefined();
    expect(within(inspector).queryByText(secondRecordId)).toBeNull();
    await within(inspector).findByText('Original FAA maintenance narrative for the drag angle.');
    expect(within(inspector).getByText('CRACKED · LH FUSELAGE')).toBeDefined();
    expect(client.maintenanceAPI.assetHistory).toHaveBeenCalledWith('1');
    expect(animateMock).not.toHaveBeenCalled();

    fireEvent.click(within(inspector).getByRole('button', { name: /Open full record view/ }));
    expect(screen.getByTestId('location')).toHaveTextContent('/app/asset-history/1#SWIA2024010100001');
    expect(screen.getByRole('complementary', { name: 'Investigation workspace panels' })).toHaveClass('xl:overflow-y-auto');
  });

  it('shows honest empty, missing-record, and failed-history states with retry', async () => {
    const emptyTurn = {
      ...baseTurn,
      ranked_checks: [{ ...baseTurn.ranked_checks[0], evidence_count: 0, evidence_record_ids: [] }],
      evidence: [],
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValueOnce({ data: emptyTurn });
    const page = renderPage();
    await send('component without evidence');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
    expect(within(liveRanking).getByText('No supporting record IDs were returned for this component.')).toBeDefined();
    expect(client.maintenanceAPI.assetHistory).not.toHaveBeenCalled();
    page.unmount();

    client.maintenanceAPI.copilotTurn.mockResolvedValueOnce({ data: baseTurn });
    client.maintenanceAPI.assetHistory.mockResolvedValueOnce({ data: { records: [] } });
    const missingPage = renderPage();
    await send('record missing from history');
    const missingRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(missingRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
    await within(missingRanking).findByText(/not found in the retrieved aircraft history/i);

    missingPage.unmount();
  });

  it('keeps the response evidence visible when history retrieval fails and can retry', async () => {
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: baseTurn });
    client.maintenanceAPI.assetHistory
      .mockRejectedValueOnce({ response: { status: 503, data: { detail: 'History temporarily unavailable' } } })
      .mockResolvedValueOnce({ data: { records: [{ ...baseTurn.evidence[0], part_condition: 'CRACKED' }] } });

    renderPage();
    await send('history failure');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
    const inspector = within(liveRanking).getByRole('region', { name: 'Component evidence inspector' });
    expect(within(inspector).getByText('Crack reported at the drag angle during inspection.')).toBeDefined();
    const alert = await within(inspector).findByRole('alert');
    expect(alert).toHaveTextContent('History temporarily unavailable');
    fireEvent.click(within(alert).getByRole('button', { name: 'Retry' }));
    await within(inspector).findByText('CRACKED');
    await waitFor(() => expect(within(inspector).queryByRole('alert')).toBeNull());
  });

  it('resolves ID-only component evidence through the read-only records list', async () => {
    const recordId = 'SWIA2024070700007';
    const idOnlyTurn = {
      ...baseTurn,
      ranked_checks: [{ ...baseTurn.ranked_checks[0], evidence_record_ids: [recordId] }],
      evidence: [],
    };
    client.maintenanceAPI.copilotTurn.mockResolvedValue({ data: idOnlyTurn });
    client.maintenanceAPI.records.mockResolvedValue({
      data: {
        items: [{
          record_id: recordId,
          asset_id: '1',
          tail_number: 'N813SK',
          occurred_at: '2024-07-07',
          part_name: 'DRAG ANGLE',
          part_condition: 'CRACKED',
          text: 'Source record found from its exact identifier.',
        }],
      },
    });

    renderPage(true);
    await send('ID-only evidence');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
    const inspector = within(liveRanking).getByRole('region', { name: 'Component evidence inspector' });
    await within(inspector).findByText('Source record found from its exact identifier.');
    expect(client.maintenanceAPI.records).toHaveBeenCalledWith({ q: recordId, limit: 1, offset: 0 });
    fireEvent.click(within(inspector).getByRole('button', { name: /Open full record view/ }));
    expect(screen.getByTestId('location')).toHaveTextContent(`/app/asset-history/1#${recordId}`);
  });

  it('keeps selection synchronized when a component moves and reports when it is ruled out', async () => {
    const nextRecordId = 'SWIA2024050500005';
    const movedTurn = {
      ...baseTurn,
      reply: 'Drag angle moved after the current observation.',
      case_state: { ...baseTurn.case_state, observations: ['Movement observed at fitting'] },
      ranked_checks: [{ ...baseTurn.ranked_checks[0], rank: 4, evidence_record_ids: [nextRecordId] }],
      ranking_delta: { moved_up: [], moved_down: [{ part_name: 'DRAG ANGLE', from_rank: 1, to_rank: 4 }], new: [], dropped: [], newly_cited_records: [nextRecordId] },
      evidence: [{ ...baseTurn.evidence[0], record_id: nextRecordId, occurred_at: '2024-05-05', text: 'Later historical drag angle report.' }],
    };
    const ruledOutTurn = {
      ...baseTurn,
      reply: 'Drag angle is ruled out of the current ranking.',
      case_state: { ...movedTurn.case_state, ruled_out: ['DRAG ANGLE'] },
      ranked_checks: checksFor('PUMP'),
      ranking_delta: { moved_up: [], moved_down: [], new: [{ part_name: 'PUMP', rank: 1 }], dropped: [{ part_name: 'DRAG ANGLE', from_rank: 4 }], newly_cited_records: [] },
      evidence: [],
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: movedTurn })
      .mockResolvedValueOnce({ data: ruledOutTurn });

    renderPage();
    await send('initial evidence');
    let liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));
    await send('new observation');
    await screen.findByText('Drag angle moved after the current observation.');
    liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    let inspector = within(liveRanking).getByRole('region', { name: 'Component evidence inspector' });
    expect(within(inspector).getByText('Rank 4')).toBeDefined();
    expect(within(inspector).getByText(nextRecordId)).toBeDefined();
    expect(within(inspector).queryByText('SWIA2024010100001')).toBeNull();

    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Rule out DRAG ANGLE' }));
    await screen.findByText('Drag angle is ruled out of the current ranking.');
    inspector = within(liveRanking).getByRole('region', { name: 'Component evidence inspector' });
    expect(within(inspector).getByText('Ruled out of the current investigation')).toBeDefined();
    expect(within(inspector).getByText(/previously rank 4/i)).toBeDefined();
    expect(within(inspector).queryByText(nextRecordId)).toBeNull();
  });

  it('animates real upward, downward, new, dropped, and removal-driven reorder changes', async () => {
    const initialChecks = [
      { ...baseTurn.ranked_checks[0], part_name: 'DRAG ANGLE', rank: 1 },
      { ...baseTurn.ranked_checks[0], part_name: 'STRINGER SPLICE', rank: 2 },
      { ...baseTurn.ranked_checks[0], part_name: 'FRAME', rank: 3 },
      { ...baseTurn.ranked_checks[0], part_name: 'RIB', rank: 4 },
      { ...baseTurn.ranked_checks[0], part_name: 'SKIN', rank: 5 },
      { ...baseTurn.ranked_checks[0], part_name: 'SUPPORT ANGLE', rank: 13 },
    ];
    const changedTurn = {
      ...baseTurn,
      reply: 'The updated ordering reflects the new observation.',
      ranked_checks: checksFor('FRAME', 'SEAL', 'RIB', 'SUPPORT ANGLE', 'DRAG ANGLE'),
      ranking_delta: {
        moved_up: [{ part_name: 'SUPPORT ANGLE', from_rank: 13, to_rank: 4 }],
        moved_down: [{ part_name: 'DRAG ANGLE', from_rank: 1, to_rank: 5 }],
        new: [{ part_name: 'SEAL', rank: 2 }],
        dropped: [{ part_name: 'STRINGER SPLICE', from_rank: 2 }],
        newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: { ...baseTurn, ranked_checks: initialChecks } })
      .mockResolvedValueOnce({ data: changedTurn });

    renderPage();
    await send('establish six checks');
    await screen.findByText(/Inspect the drag angle/);
    animateMock.mockClear();
    await send('new observation changes order');
    await screen.findByText(/updated ordering reflects/i);

    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    const support = within(liveRanking).getByText('SUPPORT ANGLE').closest('li');
    const drag = within(liveRanking).getByText('DRAG ANGLE').closest('li');
    const seal = within(liveRanking).getByText('SEAL').closest('li');
    const dropped = within(liveRanking).getByText('STRINGER SPLICE').closest('li');
    expect(support).toHaveAttribute('data-component-id', 'SUPPORT ANGLE');
    expect(support).toHaveAttribute('data-ranking-animation', 'moved-up');
    expect(within(support).getByText('Moved up 9')).toBeDefined();
    expect(within(support).getByText('Rank 13 → Rank 4')).toBeDefined();
    expect(drag).toHaveAttribute('data-ranking-animation', 'moved-down');
    expect(within(drag).getByText('Moved down 4')).toBeDefined();
    expect(seal).toHaveAttribute('data-ranking-animation', 'new');
    expect(dropped).toHaveAttribute('data-ranking-animation', 'dropped');
    expect(within(dropped).getByText(/space was removed, not because their failure probability increased/i)).toBeDefined();
    expect(within(liveRanking).getByText(/Remaining checks may shift upward because a ranked item was removed/i)).toBeDefined();
    expect(within(liveRanking).getByRole('status')).toHaveTextContent('SUPPORT ANGLE moved up 9 places, from rank 13 to 4.');
    expect(within(liveRanking).getByRole('status')).toHaveTextContent('STRINGER SPLICE was removed');
    expect(animateMock).toHaveBeenCalled();

    await waitFor(() => expect(within(liveRanking).queryByText('STRINGER SPLICE')).toBeNull());
    expect(within(liveRanking).getAllByRole('listitem').map(item => item.dataset.componentId)).toEqual([
      'FRAME', 'SEAL', 'RIB', 'SUPPORT ANGLE', 'DRAG ANGLE',
    ]);
  });

  it('does not animate an unchanged successful turn', async () => {
    const unchangedTurn = {
      ...baseTurn,
      reply: 'The ranking remains unchanged.',
      ranking_delta: { moved_up: [], moved_down: [], new: [], dropped: [], newly_cited_records: [] },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: unchangedTurn });

    renderPage();
    await send('first observation');
    await screen.findByText(/Inspect the drag angle/);
    animateMock.mockClear();
    await send('observation confirms current order');
    await screen.findByText('The ranking remains unchanged.');

    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    expect(within(liveRanking).getByText('DRAG ANGLE').closest('li')).toHaveAttribute('data-ranking-animation', 'none');
    expect(within(liveRanking).queryByRole('status')).toBeNull();
    expect(animateMock).not.toHaveBeenCalled();
    expect(screen.getAllByText('No rank change').length).toBeGreaterThan(0);
  });

  it('disables ranking motion when reduced motion is preferred', async () => {
    const reducedMotionTurn = {
      ...baseTurn,
      reply: 'Pump is now the leading check.',
      ranked_checks: checksFor('PUMP'),
      ranking_delta: {
        moved_up: [], moved_down: [], new: [{ part_name: 'PUMP', rank: 1 }],
        dropped: [{ part_name: 'DRAG ANGLE', from_rank: 1 }], newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: reducedMotionTurn });
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });

    renderPage();
    await send('first observation');
    await screen.findByText(/Inspect the drag angle/);
    animateMock.mockClear();
    await send('rule out drag angle');
    await screen.findByText('Pump is now the leading check.');

    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    expect(within(liveRanking).queryByText('DRAG ANGLE')).toBeNull();
    expect(within(liveRanking).getByText('PUMP').closest('li')).toHaveAttribute('data-ranking-animation', 'none');
    expect(within(liveRanking).queryByRole('status')).toBeNull();
    expect(animateMock).not.toHaveBeenCalled();
  });

  it('settles rapid successful ranking updates without stale or duplicate cards', async () => {
    const secondTurn = {
      ...baseTurn,
      reply: 'Second ordering completed.',
      ranked_checks: checksFor('RIB', 'FRAME', 'SKIN'),
      ranking_delta: {
        moved_up: [{ part_name: 'RIB', from_rank: 2, to_rank: 1 }],
        moved_down: [{ part_name: 'FRAME', from_rank: 1, to_rank: 2 }],
        new: [], dropped: [], newly_cited_records: [],
      },
    };
    const thirdTurn = {
      ...baseTurn,
      reply: 'Third ordering completed.',
      ranked_checks: checksFor('SKIN', 'RIB', 'FRAME'),
      ranking_delta: {
        moved_up: [{ part_name: 'SKIN', from_rank: 3, to_rank: 1 }],
        moved_down: [{ part_name: 'FRAME', from_rank: 2, to_rank: 3 }],
        new: [], dropped: [], newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: { ...baseTurn, ranked_checks: checksFor('FRAME', 'RIB', 'SKIN') } })
      .mockResolvedValueOnce({ data: secondTurn })
      .mockResolvedValueOnce({ data: thirdTurn });

    renderPage();
    await send('first ordering');
    await screen.findByText(/Inspect the drag angle/);
    await send('second ordering');
    await screen.findByText('Second ordering completed.');
    await send('third ordering immediately');
    await screen.findByText('Third ordering completed.');

    const list = within(screen.getByRole('region', { name: 'Live investigation ranking' })).getByRole('list', { name: 'Current ranked checks' });
    await waitFor(() => expect(within(list).getAllByRole('listitem')).toHaveLength(3));
    expect(within(list).getAllByRole('listitem').map(item => item.dataset.componentId)).toEqual(['SKIN', 'RIB', 'FRAME']);
    expect(new Set(within(list).getAllByRole('listitem').map(item => item.dataset.componentId)).size).toBe(3);
  });

  it('replaces the live ranking after a later turn while retaining historical snapshots', async () => {
    const secondTurn = {
      ...baseTurn,
      reply: 'The support angle is now the leading check.',
      ranked_checks: checksFor('SUPPORT ANGLE', 'PUMP'),
      ranking_delta: {
        moved_up: [{ part_name: 'SUPPORT ANGLE', from_rank: 4, to_rank: 1 }],
        moved_down: [], new: [{ part_name: 'PUMP', rank: 2 }], dropped: [{ part_name: 'DRAG ANGLE', from_rank: 1 }], newly_cited_records: [],
      },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: secondTurn });

    renderPage(true);
    await send('first observation');
    await screen.findByText(/Inspect the drag angle/);
    await send('second observation');
    await screen.findByText(/support angle is now/i);

    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    expect(within(liveRanking).getByRole('button', { name: 'Inspect evidence for SUPPORT ANGLE' })).toBeDefined();
    expect(within(liveRanking).getByText('Rank 4 → Rank 1')).toBeDefined();
    await waitFor(() => expect(within(liveRanking).queryByText('DRAG ANGLE')).toBeNull());

    const historicalSummary = screen.getByText('Historical ranking snapshot · Turn 1');
    const historical = historicalSummary.closest('details');
    expect(historical).not.toHaveAttribute('open');
    fireEvent.click(historicalSummary);
    expect(historical).toHaveAttribute('open');
    expect(within(historical).getByText('1. DRAG ANGLE')).toBeDefined();
    expect(screen.getByText(/support angle is now/i)).toBeDefined();
    expect(screen.getByTestId('copilot-composer')).toBeDefined();
    fireEvent.click(within(historical).getAllByRole('button', { name: 'SWIA2024010100001' })[0]);
    expect(screen.getByTestId('location')).toHaveTextContent('/app/asset-history/1#SWIA2024010100001');
    expect(screen.getByText('Current turn details · Turn 2')).toBeDefined();
  });

  it('removes a ruled-out component from current recommendations and sends updated case state', async () => {
    const afterRuleOut = {
      ...baseTurn,
      reply: 'Drag angle was ruled out; inspect the pump.',
      case_state: { ...baseTurn.case_state, ruled_out: ['DRAG ANGLE'] },
      ranked_checks: checksFor('PUMP'),
      ranking_delta: { moved_up: [], moved_down: [], new: [{ part_name: 'PUMP', rank: 1 }], dropped: [{ part_name: 'DRAG ANGLE', from_rank: 1 }], newly_cited_records: [] },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: afterRuleOut });

    renderPage();
    await send('crack found');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Rule out DRAG ANGLE' }));
    await screen.findByText(/inspect the pump/i);

    await waitFor(() => expect(within(liveRanking).queryByText('DRAG ANGLE')).toBeNull());
    expect(within(liveRanking).getByText('PUMP')).toBeDefined();
    expect(client.maintenanceAPI.copilotTurn).toHaveBeenLastCalledWith(expect.objectContaining({
      message: 'Case update: ruled out DRAG ANGLE.',
      case_state: expect.objectContaining({ ruled_out: ['DRAG ANGLE'] }),
    }));
  });

  it('keeps Mark done functional from the live ranking panel', async () => {
    const afterDone = {
      ...baseTurn,
      reply: 'The completed check was recorded.',
      case_state: { ...baseTurn.case_state, checks_done: ['DRAG ANGLE'] },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: afterDone });

    renderPage();
    await send('crack found');
    const liveRanking = await screen.findByRole('region', { name: 'Live investigation ranking' });
    const markDone = within(liveRanking).getByRole('button', { name: 'Mark DRAG ANGLE done' });
    markDone.focus();
    expect(markDone).toHaveFocus();
    fireEvent.click(markDone);
    await screen.findByText(/completed check was recorded/i);

    expect(client.maintenanceAPI.copilotTurn).toHaveBeenLastCalledWith(expect.objectContaining({
      message: 'Case update: check completed DRAG ANGLE.',
      case_state: expect.objectContaining({ checks_done: ['DRAG ANGLE'] }),
    }));
  });

  it('restores the latest ranking from a saved multi-turn session', async () => {
    const supportRecordId = 'SWIA2024060600006';
    const secondTurn = {
      ...baseTurn,
      reply: 'Inspect the support angle next.',
      ranked_checks: [{ ...checksFor('SUPPORT ANGLE')[0], evidence_record_ids: [supportRecordId] }],
      evidence: [{ ...baseTurn.evidence[0], record_id: supportRecordId, part_name: 'SUPPORT ANGLE', text: 'Historical support angle report.' }],
      ranking_delta: { moved_up: [{ part_name: 'SUPPORT ANGLE', from_rank: 3, to_rank: 1 }], moved_down: [], new: [], dropped: [{ part_name: 'DRAG ANGLE', from_rank: 1 }], newly_cited_records: [] },
    };
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockResolvedValueOnce({ data: secondTurn });

    renderPage();
    await send('saved investigation');
    await screen.findByText(/Inspect the drag angle/);
    await send('follow-up observation');
    await screen.findByText(/support angle next/i);
    const currentRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(currentRanking).getByRole('button', { name: 'Inspect evidence for SUPPORT ANGLE' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save session' }));
    fireEvent.click(screen.getByRole('button', { name: 'New investigation' }));
    expect(within(screen.getByRole('region', { name: 'Live investigation ranking' })).getByText('No completed ranking yet')).toBeDefined();

    animateMock.mockClear();
    fireEvent.click(screen.getByRole('button', { name: 'saved investigation' }));
    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    expect(within(liveRanking).getByRole('button', { name: 'Inspect evidence for SUPPORT ANGLE' })).toBeDefined();
    expect(within(liveRanking).queryByText('DRAG ANGLE')).toBeNull();
    expect(within(liveRanking).getByRole('button', { name: 'Inspect evidence for SUPPORT ANGLE' })).toHaveAttribute('aria-pressed', 'true');
    expect(within(liveRanking).getByRole('region', { name: 'Component evidence inspector' })).toHaveTextContent(supportRecordId);
    expect(animateMock).not.toHaveBeenCalled();
  });

  it('keeps the last completed ranking during loading and after a failed turn', async () => {
    let rejectPending;
    const pending = new Promise((resolve, reject) => { rejectPending = reject; });
    client.maintenanceAPI.copilotTurn
      .mockResolvedValueOnce({ data: baseTurn })
      .mockReturnValueOnce(pending);

    renderPage();
    await send('initial finding');
    await screen.findByText(/Inspect the drag angle/);
    const liveRanking = screen.getByRole('region', { name: 'Live investigation ranking' });
    fireEvent.click(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' }));

    await send('request that fails');
    await within(liveRanking).findByText('Updating after the current case change…');
    expect(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' })).toBeDefined();
    expect(within(liveRanking).getByRole('region', { name: 'Component evidence inspector' })).toHaveTextContent('SWIA2024010100001');
    expect(within(liveRanking).queryByText('PUMP')).toBeNull();

    await act(async () => {
      rejectPending({ code: 'ERR_NETWORK', message: 'Network Error', request: {} });
      await pending.catch(() => {});
    });
    await screen.findByText('Cannot reach the Halite API');
    expect(within(liveRanking).getByRole('button', { name: 'Inspect evidence for DRAG ANGLE' })).toBeDefined();
    expect(within(liveRanking).queryByText('PUMP')).toBeNull();
  });
});
