"""Build an editable review chapter from retained report/reference Markdown."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[3]
CHAPTER = ROOT / 'docs/fyp1-final/USMAN_FINAL_REPORT_DRAFT.md'
REFERENCES = ROOT / 'docs/fyp1-final/USMAN_RESEARCH_REFERENCES.md'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inline(paragraph, value, base, revision):
    for part in re.split(r'(\[[^\]]+\]\([^)]+\)|`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)', value):
        link = re.fullmatch(r'\[([^\]]+)\]\(([^)]+)\)', part)
        if link:
            label, url = link.groups()
            if not url.startswith('https://'):
                relative = (base / url).resolve().relative_to(ROOT)
                url = f'https://github.com/umaritics/halite/blob/{revision}/{relative.as_posix()}'
            relation = paragraph.part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
            element = OxmlElement('w:hyperlink')
            element.set(qn('r:id'), relation)
            run = OxmlElement('w:r')
            prop = OxmlElement('w:rPr')
            color = OxmlElement('w:color'); color.set(qn('w:val'), '1D4ED8'); prop.append(color)
            run.append(prop)
            text = OxmlElement('w:t'); text.text = label; run.append(text)
            element.append(run); paragraph._p.append(element)
        else:
            run = paragraph.add_run(part.strip('`') if part.startswith('`') else part.strip('*') if part.startswith('*') else part)
            if part.startswith('`'):
                run.font.name = 'Liberation Mono'; run.font.size = Pt(9)
            elif part.startswith('**'):
                run.bold = True
            elif part.startswith('*'):
                run.italic = True


def math_run(value):
    run = OxmlElement('m:r')
    text = OxmlElement('m:t'); text.text = value; run.append(text)
    return run


def subscript(base, sub):
    element = OxmlElement('m:sSub')
    e = OxmlElement('m:e'); e.append(math_run(base)); element.append(e)
    s = OxmlElement('m:sub'); s.append(math_run(sub)); element.append(s)
    return element


def fraction(numerator, denominator):
    element = OxmlElement('m:f')
    for name, values in [('num', numerator), ('den', denominator)]:
        part = OxmlElement('m:' + name)
        for value in values:
            part.append(value)
        element.append(part)
    return element


def exponential(score):
    return [math_run('exp('), fraction([score], [math_run('T')]), math_run(')')]


def belief_equation(doc, other=False):
    paragraph = doc.add_paragraph()
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    block = OxmlElement('m:oMathPara')
    equation = OxmlElement('m:oMath')
    equation.append(subscript('b', 'other' if other else 'i'))
    equation.append(math_run('='))
    summation = OxmlElement('m:nary')
    properties = OxmlElement('m:naryPr')
    for name, value in [('chr', '∑'), ('limLoc', 'subSup'), ('supHide', '1')]:
        prop = OxmlElement('m:' + name); prop.set(qn('m:val'), value); properties.append(prop)
    summation.append(properties)
    sub = OxmlElement('m:sub'); sub.append(math_run('j')); summation.append(sub)
    summation.append(OxmlElement('m:sup'))
    body = OxmlElement('m:e')
    for value in exponential(subscript('s', 'j')):
        body.append(value)
    summation.append(body)
    denominator = exponential(math_run('c')) + [math_run('+'), summation]
    numerator = exponential(math_run('c') if other else subscript('s', 'i'))
    equation.append(fraction(numerator, denominator))
    block.append(equation); paragraph._p.append(block)


def add_table(doc, lines, base, revision):
    values = [[cell.strip() for cell in row.strip().strip('|').split('|')] for row in lines]
    values = [values[0]] + values[2:]
    table = doc.add_table(rows=0, cols=3)
    table.autofit = False
    for column, width in zip(table.columns, [3.1, 1.7, 1.7]):
        column.width = Inches(width)
    properties = table._tbl.tblPr
    borders = OxmlElement('w:tblBorders')
    for edge in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        item = OxmlElement('w:' + edge)
        for key, val in [('val', 'single'), ('sz', '4'), ('color', 'D9D9D9')]:
            item.set(qn('w:' + key), val)
        borders.append(item)
    properties.append(borders)
    for index, cells in enumerate(values):
        row = table.add_row()
        no_split = OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(no_split)
        if index == 0:
            row._tr.get_or_add_trPr().append(OxmlElement('w:tblHeader'))
        for column, value in enumerate(cells):
            cell = row.cells[column]
            cell.width = Inches([3.1, 1.7, 1.7][column])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            props = cell._tc.get_or_add_tcPr()
            margins = OxmlElement('w:tcMar')
            for edge in ['top', 'left', 'bottom', 'right']:
                item = OxmlElement('w:' + edge); item.set(qn('w:w'), '100'); item.set(qn('w:type'), 'dxa'); margins.append(item)
            props.append(margins)
            shading = OxmlElement('w:shd'); shading.set(qn('w:fill'), 'E2E8F0' if index == 0 else ('F8FAFC' if index % 2 == 0 else 'FFFFFF')); props.append(shading)
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.05
            if column:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
            inline(paragraph, value, base, revision)
            for run in paragraph.runs:
                run.font.size = Pt(10)
                run.bold = index == 0
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def markdown(doc, path, revision, skip_intro=False):
    chunks = re.split(r'\n\s*\n', path.read_text())
    for i, chunk in enumerate(chunks):
        if i == 0 or (skip_intro and i == 1):
            continue
        value = ' '.join(chunk.strip().splitlines())
        if chunk.startswith('## '):
            # The final chapter's editable heading ladder uses plain words.
            title = re.sub(r'[^\w\s]', ' ', value[3:])
            doc.add_heading(' '.join(title.split()), 1)
        elif chunk.startswith('|'):
            add_table(doc, chunk.splitlines(), path.parent, revision)
        elif re.match(r'^\d+\.\s', chunk):
            for item in re.split(r'\n(?=\d+\.\s)', chunk):
                paragraph = doc.add_paragraph()
                paragraph.paragraph_format.keep_together = True
                paragraph.paragraph_format.left_indent = Inches(0.2)
                paragraph.paragraph_format.first_line_indent = Inches(-0.2)
                inline(paragraph, ' '.join(item.split()), path.parent, revision)
        elif value.startswith('The deterministic ranker supplies'):
            doc.add_paragraph('The deterministic ranker supplies at most ten named hypotheses and evidence. The following beliefs use each named score, temperature T and an additional other score c.')
            belief_equation(doc)
            belief_equation(doc, other=True)
            doc.add_paragraph('The implementation uses stable softmax. The other bucket explicitly represents support outside the retrieved candidate set. Temperature and c are fitted by negative log likelihood on 2023 correction pairs, separately from threshold selection. A ranker version mismatch invalidates fitted parameters.')
        else:
            paragraph = doc.add_paragraph()
            inline(paragraph, value, path.parent, revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[0-9a-f]{40}', args.revision)
    doc = Document()
    section = doc.sections[0]
    section.page_width, section.page_height = Inches(8.5), Inches(11)
    section.top_margin = section.bottom_margin = Inches(0.75)
    section.left_margin = section.right_margin = Inches(1)
    footer = section.footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run('Page ').font.size = Pt(9)
    field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), 'PAGE'); footer._p.append(field)
    for name in ['Normal', 'Title', 'Subtitle', 'Heading 1', 'Heading 2', 'Caption']:
        style = doc.styles[name]
        style.font.name = 'Open Sans'
        style.font.color.rgb = RGBColor(0, 0, 0)
    normal = doc.styles['Normal']
    normal.font.size = Pt(11)
    normal.paragraph_format.space_after = Pt(7)
    normal.paragraph_format.line_spacing = 1.12
    for name, size in [('Title', 24), ('Subtitle', 12), ('Heading 1', 15), ('Heading 2', 12)]:
        style = doc.styles[name]; style.font.size = Pt(size)
        style.paragraph_format.space_before = Pt(12 if name.startswith('Heading') else 0)
        style.paragraph_format.space_after = Pt(8)
        style.paragraph_format.keep_with_next = True
    doc.add_paragraph('Investigation Sessions for Halite', 'Title')
    doc.add_paragraph('FYP I contribution report', 'Subtitle')
    doc.add_paragraph('Muhammad Usman Al Haq')
    doc.add_paragraph('The frozen evaluation answered 7 of 157 cases, with 5 top one matches and 150 abstentions. This chapter explains the investigation workflow, decision design, temporal experiment and evidence behind that result. Its coverage cost and candidate retrieval failures constrain what can be concluded.')
    doc.add_paragraph('AI assistance supported implementation, documentation and verification. Independent human grounding labels, actual M4 measurements and student or supervisor acceptance are separate evidence gates; none is inferred from this document.')
    markdown(doc, CHAPTER, args.revision, skip_intro=True)
    doc.add_page_break()
    doc.add_heading('Research context and references', 1)
    markdown(doc, REFERENCES, args.revision, skip_intro=True)
    figure_files = []
    for index, title in enumerate(['Fixed abstention comparison', 'Fixed question budget comparisons', 'Candidate retrieval and part change counts'], 1):
        section = doc.add_section(WD_SECTION_START.NEW_PAGE)
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = Inches(11), Inches(8.5)
        section.left_margin = section.right_margin = Inches(0.5)
        section.top_margin = section.bottom_margin = Inches(0.45)
        doc.add_heading('Figure ' + str(index) + ' ' + title, 1)
        image = ROOT / f'docs/work/usman/evidence/phase23-report-figures/page-{index}.png'
        figure_files.append(image)
        paragraph = doc.add_paragraph()
        paragraph.paragraph_format.space_after = Pt(0)
        picture = paragraph.add_run().add_picture(str(image), width=Inches(9.5))
        picture._inline.docPr.set('descr', title + '; values, intervals, sample sizes and caveats are also provided in the editable chapter and frozen artifact.')
    doc.core_properties.title = 'Investigation Sessions for Halite'
    doc.core_properties.author = 'Muhammad Usman Al Haq'
    doc.core_properties.subject = 'FYP I contribution chapter with retained empirical evidence'
    # Remove inherited template decorations, including Word's Title blue rule.
    for root in [doc.styles.element, doc.element]:
        for border in root.xpath('.//w:pBdr'):
            border.getparent().remove(border)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(args.output)
    manifest = {'schema': 'halite-report-chapter-export-v1', 'source_revision': args.revision,
                'sources': {str(p.relative_to(ROOT)): sha(p) for p in [CHAPTER, REFERENCES] + figure_files},
                'builder_sha256': sha(Path(__file__)), 'docx_sha256': sha(args.output),
                'native_equations': 2, 'tables': len(doc.tables), 'figures': 3,
                'acceptance': 'editable chapter prepared for student review; no new empirical result or approval'}
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
