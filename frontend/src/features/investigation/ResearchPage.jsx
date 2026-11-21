import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import ResearchChart, { decimal, percentage } from '../../components/ui/ResearchChart';
import { EmptyState, ErrorCard, PageHeader } from '../../components/ui/ResearchPrimitives';
import { sessionsAPI } from './api';
import { acceptedScope, decisionSeries, frozenSeries, GROUP_LABELS, METRIC_LABELS, POLICY_LABELS, publicationData, questionSeries, stoppingSeries } from './research';

function MetricTable({ table }) {
  const rows = [['Coverage', 'coverage', percentage], ['Top-1 match among answers', 'accuracy_top1', percentage],
    ['Top-3 match among answers', 'accuracy_top3', percentage], ['Outcome-key top-3 misses / all cases', 'unsupported_suggestion_rate', percentage],
    ['Questions per case', 'mean_questions', decimal], ['Abstention rate', 'abstention_rate', percentage]];
  const value = (stats, key, format) => {
    const ci = stats.ci95[key];
    return stats[key] == null ? 'Undefined (no answered cases)' : `${format(stats[key])}; 95% CI ${format(ci.low)} to ${format(ci.high)}; ${ci.valid_resamples} valid draws`;
  };
  return <div className="overflow-x-auto"><table className="w-full text-left text-sm">
    <caption className="mb-3 text-left text-secondary">Fixed information-gain setting: {table.chosen.n_pairs} cases, {table.chosen.n_originals} original reports. {table.chosen.n_answered} answers, {table.chosen.n_correct_top1} top-one matches, {table.chosen.n_pairs - table.chosen.n_answered} abstentions.</caption>
    <thead><tr>{['Measurement', 'Frozen policy', 'Abstention off · same terminal questions'].map(label => <th key={label} scope="col" className="border-b border-theme p-2">{label}</th>)}</tr></thead>
    <tbody>{rows.map(([label, key, format]) => <tr key={key}><th scope="row" className="border-b border-theme p-2 font-normal">{label}</th>{['chosen', 'abstention_off'].map(id => <td key={id} className="border-b border-theme p-2">{value(table[id], key, format)}</td>)}</tr>)}</tbody>
  </table></div>;
}

function Results({ publication }) {
  const [dataset, setDataset] = useState('held_out');
  const [availability, setAvailability] = useState('primary_all');
  const [group, setGroup] = useState('all_attributes');
  const [cohortKey, setCohortKey] = useState('all');
  const [metric, setMetric] = useState('top1');
  const [decisionMetric, setDecisionMetric] = useState('accuracy_top1');
  const question = publication.question_selection;
  const decision = publication.decision_selection;
  const held = publication.held_out;
  const policy = publication.selected_policy;
  const isHeld = dataset === 'held_out';
  const isLegacy = dataset === 'pre_question';
  const selectedGroup = question.summaries[group];
  const cohort = isHeld ? held.question_budget_summaries[group][`${availability}/${cohortKey}`]
    : cohortKey === 'all' ? selectedGroup.all : selectedGroup.by_part_change[cohortKey];
  const difference = cohort.information_gain_minus_random.at(-1);
  const ci = difference.ci95[metric];
  const includesZero = ci.low <= 0 && ci.high >= 0;
  const format = metric === 'entropy' ? decimal : percentage;
  const selection = decision.selection;
  const sample = { year: isHeld ? held.year : question.year, stage: isHeld ? 'held-out' : 'selection', n: cohort.n_pairs, originals: cohort.n_originals, resamples: cohort.bootstrap_resamples };
  const showAccepted = acceptedScope(policy, group, cohortKey);
  const stoppingRows = publication.stopping_selection.tables.filter(row => row.cohort === group && row.stratum === cohortKey);
  const heldRows = held.stopping.filter(row => row.cohort === group && row.stratum === cohortKey && row.availability === availability);
  const heldIG = heldRows.find(row => row.strategy === 'information_gain');
  const series = key => isHeld ? frozenSeries(heldRows, key, showAccepted) : isLegacy ? decisionSeries(selection, key) : stoppingSeries(stoppingRows, key, policy, showAccepted);
  const decisionSample = isLegacy ? { year: question.year, n: selection.n, originals: selection.n_original_reports, resamples: selection.bootstrap_resamples } : sample;
  const ece = isHeld ? heldIG.named_top_ece : null;
  return <>
    <section className="halite-card space-y-2 p-5 text-sm text-secondary" aria-label="Research status">
      <p className="font-semibold text-primary">Frozen research evaluation · live policy unchanged</p>
      <p>Accepted on {policy.selection_year}: answer threshold {policy.parameters.tau_answer.toFixed(2)}, minimum gain {policy.parameters.g_min.toFixed(2)} bits, at least {policy.parameters.n_min} evidence records and at most {policy.parameters.max_questions} questions. This choice applies to all-attribute information gain on all cases.</p>
      <p>Belief parameters fitted on {decision.split.fit.join(', ')}; selection on {policy.selection_year}; fixed test on {held.year}, using ranker {policy.ranker_version}. No test-year fitting or threshold search was performed. Bars remain relative support.</p>
      <p>The test uses recorded correction-part keys and simulated original-report answers. These are research proxies, not confirmed fault causes, technician measurements or repair approval. Small answered sets have wide uncertainty.</p>
    </section>
    <label className="block max-w-lg text-sm text-primary">Evidence set<select className="halite-input mt-1" value={dataset} onChange={event => { setDataset(event.target.value); setCohortKey('all'); }}>
      <option value="held_out">2025 · frozen held-out evaluation</option><option value="stopping_selection">2024 · question-conditioned selection</option><option value="pre_question">2024 · earlier pre-question study</option>
    </select></label>
    <section className="space-y-4" aria-labelledby="questions-heading">
      <h2 id="questions-heading" className="font-brand text-xl text-primary">Do follow-up questions help?</h2>
      <div className="flex flex-wrap gap-4">
        <label className="text-sm text-primary">Attribute control<select className="halite-input mt-1" value={group} onChange={event => { setGroup(event.target.value); setCohortKey('all'); }}>
          {Object.entries(GROUP_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
        <label className="text-sm text-primary">Correction cohort<select className="halite-input mt-1" value={cohortKey} onChange={event => setCohortKey(event.target.value)}>
          <option value="all">All known-outcome pairs</option>{Object.keys(selectedGroup.by_part_change).map(key => <option key={key} value={key}>{key.replaceAll('_', ' ')}</option>)}
        </select></label>
        {isHeld && <label className="text-sm text-primary">Time-availability check<select className="halite-input mt-1" value={availability} onChange={event => setAvailability(event.target.value)}><option value="primary_all">All eligible occurrence-year cases</option><option value="after_selection_labels">After latest selection label</option></select></label>}
        <label className="text-sm text-primary">Question metric<select className="halite-input mt-1" value={metric} onChange={event => setMetric(event.target.value)}>
          {Object.entries(METRIC_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
      </div>
      <ResearchChart title={`${METRIC_LABELS[metric]} after follow-up questions`} {...sample} xLabel="Question budget" yLabel={METRIC_LABELS[metric]} xFormat={String} yFormat={format} xDomain={[0, Math.max(...cohort.policies.information_gain.map(row => row.after_questions))]} xTicks={cohort.policies.information_gain.map(row => row.after_questions)} yDomain={metric === 'entropy' ? [0, 'auto'] : [0, 1]}
        series={questionSeries(cohort, metric)} caption={`${GROUP_LABELS[group]}. Simulated answers use only original-report attributes; missing answers remain “not sure”. These fixed-budget curves are separate from the stopping-policy measurements below. Intervals cluster pairs sharing an original report; more questions need not improve accuracy.`} />
      <p className="text-sm text-secondary" data-testid="paired-difference">At budget {difference.after_questions}, {POLICY_LABELS.information_gain} minus {POLICY_LABELS.random}: {format(difference[metric])}; paired 95% interval {format(ci.low)} to {format(ci.high)}. {includesZero ? 'The interval includes zero; an advantage is not established at this budget.' : metric === 'entropy' ? 'Lower entropy means more concentrated relative support; it does not establish greater accuracy.' : 'The paired interval excludes zero for this metric and cohort.'}</p>
    </section>
    <section className="space-y-4" aria-labelledby="abstention-heading">
      <h2 id="abstention-heading" className="font-brand text-xl text-primary">What changes when Halite abstains?</h2>
      <p className="text-sm text-secondary">{isHeld ? 'Fixed test-year points only; no test-year threshold curve was searched. Abstention off uses the same terminal beliefs and questions, disabling only the final confidence and evidence gates.' : isLegacy ? 'Historical study before questioning. Its curve is separate from the accepted question-conditioned policy; it has no accepted-point marker.' : `Saved selection curves at the accepted minimum gain of ${policy.parameters.g_min.toFixed(2)} bits. The green accepted-point marker appears only for all-attribute information gain on all cases.`}</p>
      <label className="block max-w-sm text-sm text-primary">Answered-case accuracy<select className="halite-input mt-1" value={decisionMetric} onChange={event => setDecisionMetric(event.target.value)}>
        <option value="accuracy_top1">Top-1 accuracy</option><option value="accuracy_top3">Top-3 accuracy</option>
      </select></label>
      <ResearchChart title="Accuracy against coverage" {...decisionSample} xLabel="Coverage" yLabel={decisionMetric === 'accuracy_top1' ? 'Top-1 accuracy' : 'Top-3 accuracy'} series={series(decisionMetric)}
        caption="Coverage is answered cases divided by all eligible cases. Accuracy is measured only among answered cases and is undefined with no answers. Horizontal and vertical whiskers retain the saved 95% intervals. The values table preserves undefined points instead of plotting zero." />
      <ResearchChart title="Unsupported top-3 outcome-key proxy" {...decisionSample} xLabel="Coverage" yLabel="Unsupported proxy" series={series('unsupported_suggestion_rate')}
        caption="Answered cases whose top three parts omit the recorded correction key, divided by all eligible cases. This is an outcome-key proxy, not a sentence hallucination or safety rate. Empty rankings cannot answer even with abstention off." />
      {isHeld && <>
        <MetricTable table={heldIG} />
        <p className="text-sm text-secondary" data-testid="held-out-ece">Named-top ECE: {decimal(ece.value)} (95% CI {decimal(ece.ci95.low)} to {decimal(ece.ci95.high)}; {ece.ci95.valid_resamples} valid draws). {ece.definition} Relative support is not a calibrated probability.</p>
        <p className="text-sm text-secondary">Across the complete test, the recorded part is missing from the initial top ten in {held.case_counts.true_part_missing_top10} of {held.case_counts.n_pairs} cases. Named-candidate reweighting cannot add a missing part. Queries at or before the latest selection-label cutoff: {held.case_counts.before_or_at_selection_label_time_pairs}. The separate time-availability view preserves the predeclared sensitivity check.</p>
      </>}
      {isLegacy && <p className="text-sm text-secondary">Pre-question named-top ECE: {decimal(selection.ece_named_top_10_bins)} (95% CI {decimal(selection.ece_ci95.low)} to {decimal(selection.ece_ci95.high)}). {selection.ece_definition}</p>}
    </section>
    <details className="halite-card p-5 text-sm text-secondary"><summary className="cursor-pointer text-primary underline">Reproducibility and source fingerprints</summary>
      <p className="mt-3">The question-conditioned selection and frozen test use the accepted policy fingerprint below. The selection view projects saved rows at the accepted gain; it never runs a new sweep. Earlier pre-question artifacts retain their original method fingerprints.</p>
      <p className="mt-3 break-all">Accepted policy SHA-256: {policy.file_sha256}</p>
      <p className="mt-3">Pre-test receipt: {held.pretest_receipt.recorded_before_test_access_utc}. Selection-label cutoff: {held.protocol.sensitivity_label_cutoff}. Independent stopping tables verified: {publication.held_out_verification.tables_verified}.</p>
      <ul className="mt-3 space-y-3">{held.notes.map(note => <li key={note}>{note}</li>)}</ul>
      <ul className="mt-3 space-y-3">{publication.artifacts.map(artifact => <li key={artifact.id}><p className="break-all">{artifact.path}</p><code className="break-all">SHA-256 {artifact.sha256}</code></li>)}</ul>
      <p className="mt-3 break-all">Publication SHA-256: {publication.publication_sha256}</p>
    </details>
  </>;
}

function ResearchLoader() {
  const [publication, setPublication] = useState(null);
  const [error, setError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setPublication(null); setError(null);
    sessionsAPI.experiments(controller.signal).then(({ data }) => {
      if (!controller.signal.aborted) setPublication(publicationData(data));
    }).catch(() => { if (!controller.signal.aborted) setError('Research results could not be verified or loaded. Try again; no substitute measurements are shown.'); });
    return () => controller.abort();
  }, [attempt]);
  if (error) return <ErrorCard message={error} onRetry={() => setAttempt(value => value + 1)} />;
  if (!publication) return <p role="status" className="text-sm text-secondary">Loading verified research results…</p>;
  if (publication.state === 'empty') return <EmptyState title="No experiments published yet">Measured results will appear here when a verified publication is available.</EmptyState>;
  return <Results publication={publication} />;
}

export default function ResearchPage() {
  const { user } = useAuth();
  return <div className="h-full overflow-y-auto p-4 sm:p-6"><div className="mx-auto max-w-7xl space-y-6">
    <PageHeader title="How Halite decides" description="Measured question selection, uncertainty and abstention."><Link className="halite-btn-outline" to="/app/investigations">Investigations</Link></PageHeader>
    {user ? <ResearchLoader key={`${user.id}:${user.organization_id}`} /> : <p className="text-primary">Sign in to view research results.</p>}
  </div></div>;
}
