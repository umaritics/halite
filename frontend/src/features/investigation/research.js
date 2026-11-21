export const GROUP_LABELS = { all_attributes: 'All attributes', structured_fields_only: 'Structured fields only', coded_fields_only: 'Coded fields only' };
export const POLICY_LABELS = { information_gain: 'Information gain', random: 'Random questions', no_questions: 'No questions' };
export const METRIC_LABELS = { top1: 'Top-1 accuracy', top3: 'Top-3 accuracy', entropy: 'Belief entropy (bits)' };

export function publicationData(data) {
  if (data?.schema_version !== 'investigation-results-v2') throw new Error('Incompatible research publication.');
  if (data.state === 'empty') return data;
  if (data.state !== 'available' || data.question_selection?.year !== 2024 || data.question_selection.held_out_evaluated !== false
    || data.decision_selection?.held_out_evaluated !== false || !data.decision_selection?.selection?.curve?.length
    || data.selected_policy?.status !== 'selected' || data.selected_policy.belief_label !== 'relative support'
    || data.held_out?.year !== 2025 || data.held_out.held_out_evaluated !== true || data.held_out.selection_or_tuning_performed !== false
    || data.held_out.policy?.file_sha256 !== data.selected_policy.file_sha256 || !data.stopping_selection?.tables?.length
    || Object.keys(GROUP_LABELS).some(key => !data.question_selection.summaries?.[key]?.all
      || !data.held_out.question_budget_summaries?.[key]?.['primary_all/all'])) throw new Error('Incomplete research publication.');
  return data;
}

export function questionSeries(cohort, metric) {
  return Object.entries(POLICY_LABELS).map(([id, label], index) => ({ id, label, role: ['ours', 'baseline', 'control'][index],
    points: cohort.policies[id].map(row => ({ x: row.after_questions, y: row[metric], yCI: row.ci95[metric], label: `${row.after_questions} questions` })) }));
}

export function decisionSeries(selection, metric) {
  const point = row => ({ x: row.coverage, y: row[metric], xCI: row.ci95.coverage, yCI: row.ci95[metric],
    label: row.tau_answer == null ? 'Both gates disabled' : `Answer threshold ${row.tau_answer}` });
  const series = [
    { id: 'policy', label: 'Confidence and evidence gates', role: 'ours', points: selection.curve.map(point) },
    { id: 'off', label: 'Abstention off', role: 'baseline', line: false, points: [point(selection.abstention_off)] },
  ];
  // A future accepted publication must identify an exact saved curve row.
  const accepted = selection.selected_operating_point;
  if (accepted) {
    const row = selection.curve.find(item => item.tau_answer === accepted.tau_answer);
    if (!row) throw new Error('Accepted operating point is missing from the saved curve.');
    series.push({ id: 'accepted', label: 'Accepted operating point', role: 'accepted', line: false, points: [point(row)] });
  }
  return series;
}

const measuredPoint = (row, metric, label) => ({ x: row.coverage, y: row[metric], xCI: row.ci95.coverage, yCI: row.ci95[metric], label });
export function acceptedScope(policy, group, stratum) {
  return group === policy.attribute_pool && stratum === 'all';
}
export function stoppingSeries(rows, metric, policy, showAccepted) {
  const series = Object.entries(POLICY_LABELS).map(([id, label], index) => ({ id, label, role: ['ours', 'baseline', 'control'][index],
    points: rows.filter(row => row.strategy === id).map(row => measuredPoint(row, metric, `Answer threshold ${row.tau_answer}; gain ${row.g_min} bits`)) }));
  if (showAccepted) {
    const accepted = rows.find(row => row.strategy === policy.strategy && row.tau_answer === policy.parameters.tau_answer && row.g_min === policy.parameters.g_min);
    if (!accepted) throw new Error('Accepted operating point is missing from its selection curve.');
    series.push({ id: 'accepted', label: 'Accepted operating point', role: 'accepted', line: false, points: [measuredPoint(accepted, metric, 'Selected on 2024')] });
  }
  return series;
}
export function frozenSeries(tables, metric, showAccepted) {
  const ig = tables.find(row => row.strategy === 'information_gain');
  return [
    { id: 'frozen', label: showAccepted ? 'Accepted policy on held-out cases' : 'Information-gain control', role: showAccepted ? 'accepted' : 'ours', line: false, points: [measuredPoint(ig.chosen, metric, 'Frozen setting')] },
    { id: 'off', label: 'Abstention off · same terminal questions', role: 'baseline', line: false, points: [measuredPoint(ig.abstention_off, metric, 'Confidence and evidence gates disabled')] },
    ...['random', 'no_questions'].map((id, index) => ({ id, label: POLICY_LABELS[id], role: index ? 'control' : 'baseline', line: false,
      points: [measuredPoint(tables.find(row => row.strategy === id).chosen, metric, 'Same frozen thresholds')] })),
  ];
}
