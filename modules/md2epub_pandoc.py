"""
Build an EPUB from the Markdown produced by pdf2md using Pandoc.

Compared to the legacy builder (mark2epub.py), Pandoc:
* splits the book into one XHTML file per chapter (level-1 heading),
* generates the table of contents (nav + NCX) from the headings,
* renders Markdown footnotes ([^id]) as linked, back-linked EPUB3 notes
  (pop-up footnotes in most readers),
* rewrites internal links (e.g. citation -> bibliography) across chapter files.

Metadata is collected exactly like the legacy builder (description.json +
interactive prompts), so both builders are interchangeable.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from modules import mark2epub

PANDOC_ENV_VAR = "PANDOC_PATH"
# Pandoc reader: its default Markdown already enables footnotes, pipe_tables,
# tex_math_dollars, raw_html and native_spans. "smart" is disabled so the
# book's own quotes/dashes are kept exactly as extracted.
PANDOC_INPUT_FORMAT = "markdown-smart"


def find_pandoc() -> str | None:
    """Locate a pandoc binary: $PANDOC_PATH, PATH, then pypandoc_binary's bundled copy."""
    explicit = os.environ.get(PANDOC_ENV_VAR)
    if explicit and Path(explicit).is_file():
        return explicit
    on_path = shutil.which("pandoc")
    if on_path:
        return on_path
    try:
        import pypandoc  # provided by the pypandoc_binary package

        path = pypandoc.get_pandoc_path()
        return path if path and Path(path).is_file() else None
    except Exception:
        return None


def pandoc_version(pandoc: str) -> tuple[int, ...]:
    out = subprocess.run([pandoc, "--version"], capture_output=True, text=True, check=True).stdout
    m = re.search(r"pandoc(?:\.exe)?\s+(\d+(?:\.\d+)*)", out)
    return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)


# Frequent non-BCP-47 language values -> correct codes. The language drives
# hyphenation, fonts and text-to-speech in readers, so it matters.
_LANGUAGE_FIXES = {
    "sp": "es", "spa": "es", "esp": "es", "spanish": "es", "español": "es", "espanol": "es",
    "eng": "en", "english": "en", "ger": "de", "deu": "de", "german": "de",
    "fre": "fr", "fra": "fr", "french": "fr", "ita": "it", "italian": "it",
    "por": "pt", "portuguese": "pt",
}


def normalize_language(lang: str) -> str:
    fixed = _LANGUAGE_FIXES.get(lang.strip().lower())
    if fixed:
        print(f"Note: language '{lang}' is not a valid code; using '{fixed}'.")
        return fixed
    return lang.strip()


def _metadata_args(metadata: dict) -> list[str]:
    mapping = {
        "dc:title": "title",
        "dc:creator": "author",
        "dc:identifier": "identifier",
        "dc:language": "lang",
        "dc:rights": "rights",
        "dc:publisher": "publisher",
        "dc:date": "date",
    }
    args = []
    for key, pandoc_key in mapping.items():
        value = (metadata.get(key) or "").strip()
        if value and pandoc_key == "lang":
            value = normalize_language(value)
        if value:
            args += ["--metadata", f"{pandoc_key}={value}"]
    return args


def build_pandoc_command(
    pandoc: str,
    version: tuple[int, ...],
    work_dir: Path,
    output_path: Path,
    metadata: dict,
    css_files: list[Path],
    cover_image: Path | None,
    toc_depth: int = 2,
    split_level: int = 1,
) -> list[str]:
    split_flag = f"--split-level={split_level}" if version >= (3,) else f"--epub-chapter-level={split_level}"
    resource_path = os.pathsep.join([str(work_dir), str(work_dir / "images")])
    cmd = [
        pandoc,
        "--from", PANDOC_INPUT_FORMAT,
        "--to", "epub3",
        "--output", str(output_path),
        # Render $...$ / $$...$$ as MathML (EPUB3 standard). Without this,
        # pandoc's EPUB writer falls back to showing the raw TeX source.
        "--mathml",
        "--toc",
        f"--toc-depth={toc_depth}",
        split_flag,
        f"--resource-path={resource_path}",
        *_metadata_args(metadata),
    ]
    for css in css_files:
        cmd += ["--css", str(css)]
    if cover_image:
        cmd += ["--epub-cover-image", str(cover_image)]
    return cmd


def convert_to_epub(markdown_dir: Path, output_path: Path | None = None, toc_depth: int = 2, interactive: bool = True) -> Path:
    """
    Convert the Markdown chapters in markdown_dir into <markdown_dir>/<name>.epub.

    Returns the path of the generated EPUB. Raises RuntimeError if pandoc is
    not available or fails.
    """
    # Absolute paths: pandoc runs with cwd=markdown_dir.
    markdown_dir = Path(markdown_dir).resolve()
    if not markdown_dir.exists():
        raise FileNotFoundError(f"Markdown directory not found: {markdown_dir}")
    if not list(markdown_dir.glob("*.md")):
        raise ValueError(f"No markdown files found in: {markdown_dir}")

    pandoc = find_pandoc()
    if not pandoc:
        raise RuntimeError("pandoc not found (install pandoc or the pypandoc_binary package)")
    version = pandoc_version(pandoc)

    # Metadata and chapter list: same description.json as the legacy builder.
    description_path = markdown_dir / "description.json"
    existing = {}
    if description_path.exists():
        existing = json.loads(description_path.read_text(encoding="utf-8"))
    if interactive:
        data = mark2epub.get_metadata_from_user(existing)
    else:
        data = {
            "metadata": existing.get("metadata", {}),
            "default_css": existing.get("default_css", ["style.css"]),
            "chapters": existing.get("chapters", []),
            "cover_image": existing.get("cover_image"),
        }
    present = {p.name for p in markdown_dir.glob("*.md")}
    data["chapters"] = [c for c in data["chapters"] if c.get("markdown") in present]
    if not data["chapters"]:
        data["chapters"] = [{"markdown": name, "css": ""} for name in sorted(present)]
    description_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    contents = []
    for chapter in data["chapters"]:
        md_path = markdown_dir / chapter["markdown"]
        if interactive:
            proceed, content = mark2epub.review_markdown(md_path)
            if not proceed:
                raise RuntimeError("Conversion aborted by user")
        else:
            content = md_path.read_text(encoding="utf-8")
        contents.append(content)

    css_names = list(dict.fromkeys(data.get("default_css", []) + [c["css"] for c in data["chapters"] if c.get("css")]))
    css_files = [markdown_dir / "css" / n for n in css_names if (markdown_dir / "css" / n).is_file()]
    cover = data.get("cover_image")
    cover_path = None
    if cover:
        for candidate in (markdown_dir / cover, markdown_dir / "images" / cover):
            if candidate.is_file():
                cover_path = candidate
                break

    if output_path is None or Path(output_path).is_dir():
        output_path = markdown_dir / f"{markdown_dir.name}.epub"
    output_path = Path(output_path).resolve()

    cmd = build_pandoc_command(
        pandoc, version, markdown_dir, output_path, data["metadata"], css_files, cover_path, toc_depth=toc_depth
    )
    print(f"Running pandoc {'.'.join(map(str, version))}...")
    result = subprocess.run(
        cmd, input="\n\n".join(contents), capture_output=True, text=True, encoding="utf-8", cwd=markdown_dir
    )
    warnings = [w for w in result.stderr.splitlines() if w.strip()]
    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed (exit {result.returncode}):\n" + "\n".join(warnings[-20:]))
    if warnings:
        print(f"pandoc reported {len(warnings)} warning line(s); first ones:")
        for w in warnings[:5]:
            print(f"  {w}")
    print(f"EPUB created: {output_path}")
    return output_path
