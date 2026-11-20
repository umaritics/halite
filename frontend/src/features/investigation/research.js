export const GROUP_LABELS = { all_attributes: 'All attributes', structured_fields_only: 'Structured fields only', coded_fields_only: 'Coded fields only' };
export const POLICY_LABELS = { information_gain: 'Information gain', random: 'Random questions', no_questions: 'No questions' };
export const METRIC_LABELS = { top1: 'Top-1 accuracy', top3: 'Top-3 accuracy', entropy: 'Belief entropy (bits)' };

export function publicationData(data) {
  if (data?.schema_version !== 'investigation-results-v1') throw new Error('Incompatible research publication.');
  if (data.state === 'empty') return data;
  if (data.state !== 'available' || data.question_selection?.year !== 2024 || data.question_selection.held_out_evaluated !== false
    || data.decision_selection?.held_out_evaluated !== false || !data.decision_selection?.selection?.curve?.length
    || Object.keys(GROUP_LABELS).some(key => !data.question_selection.summaries?.[key]?.all)) throw new Error('Incomplete research publication.');
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
