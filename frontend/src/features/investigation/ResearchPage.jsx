import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import ResearchChart, { decimal, percentage } from '../../components/ui/ResearchChart';
import { EmptyState, ErrorCard, PageHeader } from '../../components/ui/ResearchPrimitives';
import { sessionsAPI } from './api';
import { decisionSeries, GROUP_LABELS, METRIC_LABELS, POLICY_LABELS, publicationData, questionSeries } from './research';

function Results({ publication }) {
  const [group, setGroup] = useState('all_attributes');
  const [cohortKey, setCohortKey] = useState('all');
  const [metric, setMetric] = useState('top1');
  const [decisionMetric, setDecisionMetric] = useState('accuracy_top1');
  const question = publication.question_selection;
  const decision = publication.decision_selection;
  const selectedGroup = question.summaries[group];
  const cohort = cohortKey === 'all' ? selectedGroup.all : selectedGroup.by_part_change[cohortKey];
  const difference = cohort.information_gain_minus_random.at(-1);
  const ci = difference.ci95[metric];
  const includesZero = ci.low <= 0 && ci.high >= 0;
  const format = metric === 'entropy' ? decimal : percentage;
  const selection = decision.selection;
  const sample = { year: question.year, n: cohort.n_pairs, originals: cohort.n_originals, resamples: cohort.bootstrap_resamples };
  const decisionSample = { year: decision.split.select.join(', '), n: selection.n, originals: selection.n_original_reports, resamples: selection.bootstrap_resamples };
  return <>
    <section className="halite-card space-y-2 p-5 text-sm text-secondary" aria-label="Research status">
      <p className="font-semibold text-primary">Selection evidence · not final held-out performance</p>
      <p>Belief parameters fitted on {decision.split.fit.join(', ')}. These experiments use {decision.split.select.join(', ')} selection data and ranker {decision.ranker_version}. The {decision.split.test.join(', ')} held-out set has not been evaluated.</p>
      <p>No operating point has been accepted. These charts do not activate a live policy. The question simulation and the pre-question abstention study are separate experiments.</p>
    </section>
    <section className="space-y-4" aria-labelledby="questions-heading">
      <h2 id="questions-heading" className="font-brand text-xl text-primary">Do follow-up questions help?</h2>
      <div className="flex flex-wrap gap-4">
        <label className="text-sm text-primary">Attribute control<select className="halite-input mt-1" value={group} onChange={event => { setGroup(event.target.value); setCohortKey('all'); }}>
          {Object.entries(GROUP_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
        <label className="text-sm text-primary">Correction cohort<select className="halite-input mt-1" value={cohortKey} onChange={event => setCohortKey(event.target.value)}>
          <option value="all">All known-outcome pairs</option>{Object.keys(selectedGroup.by_part_change).map(key => <option key={key} value={key}>{key.replaceAll('_', ' ')}</option>)}
        </select></label>
        <label className="text-sm text-primary">Question metric<select className="halite-input mt-1" value={metric} onChange={event => setMetric(event.target.value)}>
          {Object.entries(METRIC_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
      </div>
      <ResearchChart title={`${METRIC_LABELS[metric]} after follow-up questions`} {...sample} xLabel="Question budget" yLabel={METRIC_LABELS[metric]} xFormat={String} yFormat={format} xDomain={[0, 3]} yDomain={metric === 'entropy' ? [0, 'auto'] : [0, 1]}
        series={questionSeries(cohort, metric)} caption={`${GROUP_LABELS[group]}. A simulated technician supplies only original-report attributes; missing answers remain “not sure”. The question budget is a maximum, not a guarantee that every case was asked that many questions. Intervals cluster pairs sharing an original report.`} />
      <p className="text-sm text-secondary" data-testid="paired-difference">At budget {difference.after_questions}, {POLICY_LABELS.information_gain} minus {POLICY_LABELS.random}: {format(difference[metric])}; paired 95% interval {format(ci.low)} to {format(ci.high)}. {includesZero ? 'The interval includes zero; an advantage is not established at this budget.' : metric === 'entropy' ? 'Lower entropy means more concentrated relative support; it does not establish greater accuracy.' : 'The paired interval excludes zero for this metric and cohort.'}</p>
    </section>
    <section className="space-y-4" aria-labelledby="abstention-heading">
      <h2 id="abstention-heading" className="font-brand text-xl text-primary">What changes when Halite abstains?</h2>
      <label className="block max-w-sm text-sm text-primary">Answered-case accuracy<select className="halite-input mt-1" value={decisionMetric} onChange={event => setDecisionMetric(event.target.value)}>
        <option value="accuracy_top1">Top-1 accuracy</option><option value="accuracy_top3">Top-3 accuracy</option>
      </select></label>
      <ResearchChart title="Accuracy against coverage" {...decisionSample} xLabel="Coverage" yLabel={decisionMetric === 'accuracy_top1' ? 'Top-1 accuracy' : 'Top-3 accuracy'} series={decisionSeries(selection, decisionMetric)}
        caption="Coverage is answered cases divided by all eligible cases. Accuracy is measured only among answered cases; it is undefined when no cases are answered. Whiskers show both coverage and accuracy intervals. No chosen-point marker is shown because none is accepted." />
      <ResearchChart title="Unsupported top-3 outcome-key proxy" {...decisionSample} xLabel="Coverage" yLabel="Unsupported proxy" series={decisionSeries(selection, 'unsupported_suggestion_rate')}
        caption="This counts answered cases whose top three parts omit the correction's outcome key, divided by all eligible cases. It is an outcome-key proxy, not a sentence hallucination or clinical safety rate. Abstention off disables both confidence and evidence gates; empty rankings still cannot answer." />
      <p className="text-sm text-secondary">Leading-named-belief ECE: {decimal(selection.ece_named_top_10_bins)} (95% interval {decimal(selection.ece_ci95.low)} to {decimal(selection.ece_ci95.high)}). {selection.ece_definition}</p>
    </section>
    <details className="halite-card p-5 text-sm text-secondary"><summary className="cursor-pointer text-primary underline">Reproducibility and source fingerprints</summary>
      <p className="mt-3">Question method: {question.method_version}. Decision method: {decision.method_version}. These measured methods record a dirty working tree; per-file method fingerprints are retained in the committed artifacts.</p>
      <ul className="mt-3 space-y-3">{publication.artifacts.map(artifact => <li key={artifact.id}><p>{artifact.path}</p><code className="break-all">SHA-256 {artifact.sha256}</code></li>)}</ul>
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
