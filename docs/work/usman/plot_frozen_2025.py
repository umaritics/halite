"""Export saved measurements only; no fitting, simulation, bootstrap or inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from reportlab.graphics import renderPDF
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, Line
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / 'backend/investigation/experiments/results/held_out_2025_v1/results.json'
SOURCE_SHA = '0815e2089902105e9c459ffe0afeffc664a1dc2039419ae415070b972b876a12'
GREEN, BLUE, GRAY, RED = map(colors.HexColor, ['#087f5b', '#2563eb', '#64748b', '#c2410c'])
WIDTH, HEIGHT = landscape(A4)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def text(c, x, y, value, size=10, bold=False, color='#243247'):
    c.setFillColor(colors.HexColor(color))
    font = 'Helvetica-Bold' if bold else 'Helvetica'
    available = WIDTH - 42 - x
    size = min(size, size * available / max(available, c.stringWidth(value, font, size)))
    c.setFont(font, size)
    c.drawString(x, y, value)


def header(c, number, title, subtitle):
    text(c, 42, HEIGHT - 38, 'HALITE / FROZEN 2025 RESEARCH', 10, True, '#087f5b')
    text(c, 42, HEIGHT - 72, title, 22, True)
    text(c, 42, HEIGHT - 94, subtitle, 10)
    c.setStrokeColor(colors.HexColor('#dbe2ea'))
    c.line(42, 48, WIDTH - 42, 48)
    text(c, 42, 33, 'Saved results SHA-256: ' + SOURCE_SHA, 7)
    text(c, WIDTH - 75, 33, f'{number} / 3', 8)


def legend(c, x, y, entries):
    for label, color in entries:
        c.setFillColor(color)
        c.circle(x, y + 3, 3, fill=1, stroke=0)
        text(c, x + 10, y, label, 9)
        x += 12 + c.stringWidth(label, 'Helvetica', 9) + 24


def line_plot(series, width, height, x_max, y_max, y_ticks, percent=False, joined=True):
    d = Drawing(width + 60, height + 45)
    p = LinePlot()
    p.x, p.y, p.width, p.height = 42, 28, width, height
    p.data = [points for _, _, points in series]
    p.joinedLines = int(joined)
    p.xValueAxis.valueMin, p.xValueAxis.valueMax = 0, x_max
    p.yValueAxis.valueMin, p.yValueAxis.valueMax = 0, y_max
    p.xValueAxis.valueSteps = [0, 20, 40, 60, 80, 100] if x_max > 3 else [0, 1, 2, 3]
    p.yValueAxis.valueSteps = y_ticks
    if x_max > 3:
        p.xValueAxis.labelTextFormat = '%d%%'
    p.yValueAxis.labelTextFormat = '%d%%' if percent else '%.1f'
    for axis in [p.xValueAxis, p.yValueAxis]:
        axis.labels.fontName, axis.labels.fontSize = 'Helvetica', 9
        axis.strokeColor = colors.HexColor('#94a3b8')
    p.yValueAxis.visibleGrid = True
    p.yValueAxis.gridStrokeColor = colors.HexColor('#e8edf3')
    for i, (_, color, _) in enumerate(series):
        p.lines[i].strokeColor, p.lines[i].strokeWidth = color, 1.5
        p.lines[i].symbol = makeMarker('FilledCircle', size=5, fillColor=color, strokeColor=color)
    d.add(p)
    return d, p


def whisker(d, p, x, y, low, high, color, x_max, y_max, horizontal=False):
    px = p.x + p.width * x / x_max
    py = p.y + p.height * y / y_max
    if horizontal:
        a, b = p.x + p.width * low / x_max, p.x + p.width * high / x_max
        segments = [(a, py, b, py), (a, py - 3, a, py + 3), (b, py - 3, b, py + 3)]
    else:
        a, b = p.y + p.height * low / y_max, p.y + p.height * high / y_max
        segments = [(px, a, px, b), (px - 3, a, px + 3, a), (px - 3, b, px + 3, b)]
    for segment in segments:
        d.add(Line(*segment, strokeColor=color, strokeWidth=0.8))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--font-dir', type=Path, default=Path('/usr/share/fonts/truetype/open-sans'))
    args = parser.parse_args()
    # Embed measured fonts so PDF viewers cannot substitute incompatible metrics.
    font_files = [args.font_dir / 'OpenSans-Regular.ttf', args.font_dir / 'OpenSans-Bold.ttf']
    for name, filename in zip(['Helvetica', 'Helvetica-Bold'], font_files):
        pdfmetrics.registerFont(TTFont(name, str(filename)))
    assert digest(SOURCE) == SOURCE_SHA, 'Frozen source changed'
    data = json.loads(SOURCE.read_text())
    assert data['held_out_evaluated'] is True
    assert data['selection_or_tuning_performed'] is False
    rows = [r for r in data['stopping'] if r['cohort'] == 'all_attributes'
            and r['availability'] == 'primary_all' and r['strategy'] == 'information_gain']
    overall = next(r for r in rows if r['stratum'] == 'all')
    q = data['question_budget_summaries']['all_attributes']['primary_all/all']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(args.output), pagesize=(WIDTH, HEIGHT), invariant=1)
    c.setTitle('Halite - frozen 2025 research results')
    c.setAuthor('Muhammad Usman Al Haq; AI-assisted figure preparation')
    header(c, 1, 'Abstention trades coverage for selectivity',
           'Fixed setting selected on 2024; 157 test pairs / 140 original reports; all attributes.')
    entries = [('Frozen policy: 7 answers / 5 top-one matches', GREEN),
               ('Abstention off: 157 answers / 31 matches', BLUE)]
    legend(c, 60, 463, entries)
    series = [(label, color, [(100 * row['coverage'], 100 * row['accuracy_top1'])])
              for (label, color), row in zip(entries, [overall['chosen'], overall['abstention_off']])]
    drawing, plot = line_plot(series, 650, 280, 105, 105, [0, 20, 40, 60, 80, 100], True, False)
    for row, color in [(overall['chosen'], GREEN), (overall['abstention_off'], BLUE)]:
        x, y = 100 * row['coverage'], 100 * row['accuracy_top1']
        for key, horizontal in [('coverage', True), ('accuracy_top1', False)]:
            ci = row['ci95'][key]
            whisker(drawing, plot, x, y, 100 * ci['low'], 100 * ci['high'], color, 105, 105, horizontal)
    renderPDF.draw(drawing, c, 48, 126)
    text(c, 332, 128, 'Coverage (% of all test cases)', 10, True)
    c.saveState()
    c.translate(29, 218)
    c.rotate(90)
    text(c, 0, 0, 'Top-1 match among answered cases (%)', 10, True)
    c.restoreState()
    text(c, 115, 425, '4.46% coverage; 71.43% match', 10, True, '#087f5b')
    text(c, 480, 237, '100% coverage; 19.75% match', 10, True, '#2563eb')
    text(c, 60, 102, 'Both arms use the same terminal questions: mean 1.46 per case. Frozen policy abstains on 150 cases.', 10)
    text(c, 60, 85, 'Whiskers: saved 95% clustered bootstrap intervals (1,000 draws; 999 valid answered-accuracy draws for policy).', 9)
    text(c, 60, 68, 'Two fixed points, no test-year threshold sweep. Part-key match is a research proxy; it is not repair approval.', 9)
    c.showPage()

    header(c, 2, 'Question budget changes ranking and uncertainty',
           'Saved fixed-budget simulations; all attributes / all eligible test cases; these are separate from stopping metrics.')
    controls = [('information_gain', 'Information gain', GREEN), ('random', 'Random questions', BLUE), ('no_questions', 'No questions', GRAY)]
    legend(c, 75, 461, [(label, color) for _, label, color in controls])
    for offset, metric, label, maximum, ticks in [
        (0, 'top1', 'Top-1 accuracy (%)', 35, [0, 10, 20, 30]),
        (260, 'top3', 'Top-3 accuracy (%)', 45, [0, 10, 20, 30, 40]),
        (520, 'entropy', 'Belief entropy (bits)', 3.2, [0, 1, 2, 3]),
    ]:
        scale = 1 if metric == 'entropy' else 100
        series = [(label, color, [(r['after_questions'], scale * r[metric]) for r in q['policies'][key]])
                  for key, label, color in controls]
        drawing, plot = line_plot(series, 185, 235, 3, maximum, ticks, metric != 'entropy')
        for key, _, color in controls:
            for row in q['policies'][key]:
                ci = row['ci95'][metric]
                whisker(drawing, plot, row['after_questions'], scale * row[metric], scale * ci['low'], scale * ci['high'], color, 3, maximum)
        renderPDF.draw(drawing, c, 28 + offset, 156)
        text(c, 64 + offset, 437, label, 11, True)
        text(c, 85 + offset, 151, 'Allowed question budget', 9)
    text(c, 60, 121, '157 pairs / 140 originals; whiskers preserve saved 95% intervals from 1,000 original-report-clustered draws.', 9)
    text(c, 60, 103, 'Simulated answers come from original-report attributes; missing values remain not sure. No-question rankings stay fixed.', 9)
    text(c, 60, 85, 'Information-gain top-1: 12.74%, 17.20%, 21.02%, 18.47%. More questions do not necessarily improve accuracy.', 9)
    text(c, 60, 67, 'Entropy describes concentration of relative support, not calibrated correctness or evidence of diagnostic safety.', 9)
    c.showPage()

    header(c, 3, 'Candidate retrieval limits downstream selection',
           'Descriptive test counts, not confidence intervals. Same frozen policy and primary all-attribute cohort.')
    strata = [next(r for r in rows if r['stratum'] == key)['chosen']
              for key in ['named_to_named', 'same', 'unknown_to_named']]
    chart = VerticalBarChart()
    chart.x, chart.y, chart.width, chart.height = 45, 35, 400, 265
    chart.data = [[r['n_pairs'] - r['n_answered'] for r in strata],
                  [r['n_answered'] - r['n_correct_top1'] for r in strata],
                  [r['n_correct_top1'] for r in strata]]
    chart.categoryAxis.style = 'stacked'
    chart.categoryAxis.categoryNames = ['Changed named part', 'Same named part', 'Unknown to named']
    chart.categoryAxis.labels.fontSize = 9
    chart.categoryAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.labels.fontName = 'Helvetica'
    chart.valueAxis.valueMin, chart.valueAxis.valueMax, chart.valueAxis.valueStep = 0, 100, 20
    for i, color in enumerate([GRAY, RED, GREEN]):
        chart.bars[i].fillColor = color
        chart.bars[i].strokeColor = None
    drawing = Drawing(480, 315)
    drawing.add(chart)
    renderPDF.draw(drawing, c, 30, 135)
    legend(c, 75, 465, [('Abstained', GRAY), ('Answered: top-1 miss', RED), ('Answered: match', GREEN)])
    text(c, 535, 427, '113 / 157', 31, True, '#c2410c')
    text(c, 535, 403, 'recorded parts absent from initial top ten', 10)
    text(c, 535, 373, 'Reweighting cannot add a missing candidate.', 10, True)
    for y, line in [(335, 'Changed named part: 94 cases; 2 answers; 0 matches.'),
                    (315, 'Same named part: 51 cases; 5 answers; 5 matches.'),
                    (295, 'Unknown to named: 12 cases; 0 answers.'),
                    (257, 'All five matches are in the same-part cohort.'),
                    (237, 'Both answered misses lacked the true top-ten part.'),
                    (199, 'Named-top ECE: 0.184 (95% CI 0.131 to 0.246).'),
                    (179, 'Relative support is not a calibrated probability.')]:
        text(c, 535, y, line, 9)
    text(c, 75, 117, 'Case count', 10, True)
    text(c, 60, 92, 'Outcome keys are recorded correction-part proxies, not confirmed root causes. No test-year tuning was performed.', 9)
    text(c, 60, 73, 'Research implication: improve candidate retrieval and assess changed-part cases before broader answer coverage.', 9)
    c.save()
    manifest = {'schema': 'halite-frozen-figure-export-v1', 'source': str(SOURCE.relative_to(ROOT)),
                'source_sha256': SOURCE_SHA, 'generator_sha256': digest(Path(__file__)),
                'pdf_sha256': digest(args.output), 'pages': 3,
                'embedded_font_sha256': {p.name: digest(p) for p in font_files},
                'operations': 'plot saved values only; no experiment/model/fit/sweep/bootstrap',
                'fixed_policy_and_comparison': overall, 'question_budget_rows': q,
                'strata': {r['stratum']: r['chosen'] for r in rows if r['stratum'] != 'all'},
                'retrieval_counts': data['case_counts']}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
