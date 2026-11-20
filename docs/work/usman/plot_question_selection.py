"""Standalone scientific figure from committed selection results (report tools only)."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[3]
source = ROOT / 'backend/investigation/experiments/results/question_selection_2024_v2/results.json'
data = json.loads(source.read_text())
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
fig, axes = plt.subplots(3, 3, figsize=(12, 10), sharex=True, constrained_layout=True)
colors = {'information_gain': '#145DA0', 'random': '#C15A13', 'no_questions': '#68737D'}
labels = {'information_gain': 'Information gain', 'random': 'Random', 'no_questions': 'No questions'}
for row, (group, result) in enumerate(data['summaries'].items()):
    for col, (key, label) in enumerate([('top1', 'Top-1 accuracy'), ('top3', 'Top-3 accuracy'), ('entropy', 'Mean entropy (bits)')]):
        ax = axes[row, col]
        for policy, steps in result['all']['policies'].items():
            x = [s['after_questions'] for s in steps]
            ax.plot(x, [s[key] for s in steps], marker='o', markersize=4, color=colors[policy], label=labels[policy])
            ax.fill_between(x, [s['ci95'][key]['low'] for s in steps], [s['ci95'][key]['high'] for s in steps], color=colors[policy], alpha=.10)
        ax.set_title(group.replace('_', ' ').capitalize() + '\n' + label)
        ax.set_xticks(range(4))
        ax.grid(alpha=.18)
        if col < 2:
            ax.set_ylim(0, .4)
        if row == 2:
            ax.set_xlabel('Question budget (maximum)')
axes[0, 0].legend(fontsize=8, loc='upper left')
fig.suptitle('2024 selection: simulated technician, frozen Mid-I candidates\n389 pairs / 340 original reports; 95% clustered bootstrap intervals', fontsize=14)
fig.supxlabel('Original-report answers only; narrative mentions may reuse initial text. Accuracy differences remain uncertain.\n2023 fit; 2025 held out. Entropy reduction alone does not establish diagnostic correctness.', fontsize=10)
out = ROOT / 'docs/fyp1-final/figures'
out.mkdir(exist_ok=True)
for suffix in ('png', 'pdf'):
    fig.savefig(out / ('question-selection-2024.' + suffix), dpi=180)
print('Generated PNG and PDF from committed results; Matplotlib ' + matplotlib.__version__)
