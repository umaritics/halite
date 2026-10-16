"""Render the versioned Mid-I report addendum Markdown as a small PDF.

Install the isolated renderer dependency with:
    python -m pip install -r docs/requirements-render.txt
"""
from __future__ import annotations

import re
import textwrap
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "mid1" / "15_report_mid1_addendum.md"
OUTPUT = ROOT / "docs" / "mid1" / "Halite_FYP_Report_Mid1_Addendum.pdf"

PAGE = pymupdf.paper_rect("a4")
LEFT = 54
TOP = 54
BOTTOM = 54


def _plain(text: str) -> str:
    text = text.replace("<br>", "")
    text = text.replace("–", "-").replace("—", "-")
    text = text.replace("‘", "'").replace("’", "'")
    text = text.replace("“", '"').replace("”", '"')
    return re.sub(r"[*`]", "", text)


def _blocks(markdown: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    paragraph: list[str] = []

    def flush() -> None:
        if paragraph:
            blocks.append(("paragraph", _plain(" ".join(paragraph))))
            paragraph.clear()

    for raw in markdown.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("# "):
            flush()
            blocks.append(("title", _plain(line[2:])))
        elif line.startswith("## "):
            flush()
            blocks.append(("heading", _plain(line[3:])))
        elif line.startswith("- "):
            flush()
            blocks.append(("bullet", _plain(line[2:])))
        else:
            paragraph.append(line)
    flush()
    return blocks


def render() -> None:
    document = pymupdf.open()
    page = document.new_page(width=PAGE.width, height=PAGE.height)
    y = TOP

    def new_page() -> None:
        nonlocal page, y
        page = document.new_page(width=PAGE.width, height=PAGE.height)
        y = TOP

    for kind, text in _blocks(SOURCE.read_text(encoding="utf-8")):
        if kind == "title":
            size, font, width, before, after = 18, "hebo", 54, 0, 14
        elif kind == "heading":
            size, font, width, before, after = 13, "hebo", 72, 8, 8
        elif kind == "bullet":
            size, font, width, before, after = 10, "helv", 88, 1, 4
            text = "- " + text
        else:
            size, font, width, before, after = 10, "helv", 92, 1, 7

        lines = textwrap.wrap(text, width=width, break_long_words=False) or [""]
        height = before + len(lines) * (size * 1.35) + after
        if y + height > PAGE.height - BOTTOM:
            new_page()
        y += before
        for line in lines:
            page.insert_text((LEFT, y), line, fontname=font, fontsize=size, color=(0, 0, 0))
            y += size * 1.35
        y += after

    metadata = document.metadata
    metadata.update({
        "title": "Halite FYP-I Mid Report Addendum",
        "author": "Halite FYP Team",
        "subject": "Implementation status correction and responsible tool disclosure",
    })
    document.set_metadata(metadata)
    document.save(
        OUTPUT,
        garbage=4,
        deflate=True,
        no_new_id=True,
        reproducible=True,
    )
    document.close()


if __name__ == "__main__":
    render()
