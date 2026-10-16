"""
Markdown post-processing for marker-pdf output.

Pipeline (each step is idempotent, so it is safe to re-run on the same file):
1. cleanup:   fix common extraction artifacts (<sup>Y</sup>, split fi/fl ligatures)
2. headings:  normalize heading levels (PDF outline, else chapter heuristics)
3. footnotes: turn plain-text notes into linked Markdown footnotes
4. citations: link author-year citations to bibliography entries (optional)
"""
from __future__ import annotations

import shutil
from pathlib import Path

from .citations import link_citations
from .cleanup import clean_markdown
from .footnotes import link_footnotes
from .headings import normalize_headings, read_pdf_outline

BACKUP_SUFFIX = ".orig"

__all__ = [
    "postprocess_text", "postprocess_markdown_dir", "link_citations", "link_footnotes",
    "clean_markdown", "normalize_headings", "read_pdf_outline",
]


def postprocess_text(
    text: str,
    link_cites: bool = True,
    fix_ligatures: bool = True,
    fix_headings: bool = True,
    outline=None,
) -> tuple[str, list[str]]:
    """
    Run the full pipeline on a Markdown string. Returns (text, report lines).
    `outline` is the PDF outline (see read_pdf_outline), used for headings.
    """
    report = []
    text = clean_markdown(text, ligatures=fix_ligatures)
    if fix_headings:
        text, head_report = normalize_headings(text, outline)
        report.append(head_report.summary())
    text, fn_report = link_footnotes(text)
    report.append(fn_report.summary())
    if link_cites:
        text, cite_report = link_citations(text)
        report.append(cite_report.summary())
    return text, report


def postprocess_markdown_dir(
    markdown_dir: Path,
    link_cites: bool = True,
    fix_ligatures: bool = True,
    fix_headings: bool = True,
    pdf_path: Path | str | None = None,
) -> None:
    """
    Post-process every top-level .md file in markdown_dir in place.

    The first time a file is modified, the original is kept as
    "<name>.md.orig" (not picked up as a chapter, never overwritten).
    `pdf_path` (optional) is the source PDF; its outline guides heading levels.
    """
    markdown_dir = Path(markdown_dir)
    outline = read_pdf_outline(pdf_path) if (fix_headings and pdf_path) else []
    for md_path in sorted(markdown_dir.glob("*.md")):
        original = md_path.read_text(encoding="utf-8")
        processed, report = postprocess_text(
            original,
            link_cites=link_cites,
            fix_ligatures=fix_ligatures,
            fix_headings=fix_headings,
            outline=outline,
        )
        print(f"Post-processing {md_path.name}:")
        for line in report:
            print(f"  - {line}")
        if processed == original:
            continue
        backup = md_path.with_name(md_path.name + BACKUP_SUFFIX)
        if not backup.exists():
            shutil.copy2(md_path, backup)
        md_path.write_text(processed, encoding="utf-8")
