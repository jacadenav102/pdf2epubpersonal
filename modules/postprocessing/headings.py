"""
Normalize heading levels in marker-pdf Markdown.

Without an LLM, marker-pdf assigns heading levels from font-size clusters,
which often gives chapters "###", sections "####" and stray "#" captions.
Since the EPUB is split into chapters at H1 and its table of contents is
built from H1/H2, that produces a poor book.

Strategy (book-agnostic):

1. PDF outline (bookmarks), when the PDF has a usable one: headings are
   aligned to the outline entries in reading order (tolerant to truncated
   titles such as "TÍTULO LARGO (...)", case/accent/spacing differences and
   headings split over two lines). Matched headings take the outline level;
   outline entries that marker left as plain text lines are promoted;
   duplicates of outline titles that were not aligned (e.g. inside a printed
   table of contents) are turned into plain text; remaining headings are
   placed one level below the section they belong to, keeping their relative
   order.
2. Otherwise, heuristics: headings that look like chapters ("CAPÍTULO 3",
   "Chapter 3", "IV. TÍTULO", "INTRODUCCIÓN", "BIBLIOGRAPHY", ...) become H1
   and the rest are renumbered below them.
3. In both cases, figure/table captions emitted as headings ("GRÁFICA IV.7.
   ...", "Table 2 ...") become bold paragraphs.

The result is stable: running it again on its own output changes nothing.
"""
from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_TRUNCATED_RE = re.compile(r"\s*(\(\s*(\.\.\.|…)\s*\)|\.\.\.|…)\s*$")

# Inline noise stripped before comparing heading text.
_INLINE_NOISE = [
    re.compile(r"\[\^[^\]]+\]"),            # footnote references
    re.compile(r"<[^>]+>"),                 # HTML tags (<sup>, <span id=...>)
    re.compile(r"!\[[^\]]*\]\([^)]*\)"),    # images
    re.compile(r"\{#[^}]*\}"),              # pandoc attributes
]
_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")

_CAPTION_WORDS = (
    "gráfica", "gráfico", "cuadro", "figura", "tabla", "mapa", "diagrama", "esquema",
    "ilustración", "imagen", "lámina", "recuadro", "figure", "fig", "table", "chart",
    "graph", "exhibit", "plate", "illustration", "tableau", "graphique", "abbildung",
    "tabelle", "grafik", "karte", "quadro", "tavola", "grafico", "tabella",
)
_CAPTION_RE = re.compile(
    r"^(?:" + "|".join(_CAPTION_WORDS) + r")\.?\s+"
    r"(?:[0-9]+|[IVXLC]+)(?:[.\-–][0-9A-Za-z]+)*(?:[.:\-–]|\s|$)",
    re.IGNORECASE,
)

_NUMBER_WORDS = (
    "uno|una|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|primer[oa]?|segund[oa]|tercer[oa]?|"
    "cuart[oa]|quint[oa]|sext[oa]|s[eé]ptim[oa]|octav[oa]|noven[oa]|d[eé]cim[oa]|"
    "one|two|three|four|five|six|seven|eight|nine|ten|first|second|third|fourth|fifth|"
    "un|deux|trois|quatre|cinq|premi[eè]re?|seconde?|eins|zwei|drei|vier|f[uü]nf"
)
_CHAPTER_WORD_RE = re.compile(
    r"^(?:cap[ií]tulo|chapter|chapitre|kapitel|capitolo|parte|part|partie|teil|libro|book|livre|"
    r"anexo|ap[eé]ndice|appendix|annexe|anhang|appendice)\s+"
    r"(?:[0-9]+|[IVXLC]+|[A-Z]|" + _NUMBER_WORDS + r")\b",
    re.IGNORECASE,
)
_NUMBERED_CHAPTER_RE = re.compile(r"^(?:[IVXLC]+|[0-9]{1,2})[.)]\s+\S")
# Front/back matter titles (compared without accents, lowercase).
_MATTER_TITLES = {
    # es / pt / it / fr / de / en
    "introduccion", "prologo", "prefacio", "presentacion", "conclusiones", "conclusion",
    "epilogo", "postscriptum", "postcriptum", "posdata", "bibliografia", "referencias",
    "referencias bibliograficas", "indice", "agradecimientos", "apendice", "apendices",
    "anexo", "anexos", "glosario", "notas", "dedicatoria", "nota preliminar",
    "introducao", "conclusao", "conclusoes", "referencias", "introduzione", "conclusioni",
    "premessa", "prefazione", "ringraziamenti", "avant-propos", "avant propos", "preface",
    "conclusions", "remerciements", "einleitung", "vorwort", "nachwort", "schluss",
    "literaturverzeichnis", "literatur", "danksagung", "anhang", "introduction", "foreword",
    "conclusion", "epilogue", "afterword", "prologue", "bibliography", "references",
    "index", "acknowledgments", "acknowledgements", "appendix", "appendices", "notes",
    "contents", "table of contents", "glossary", "works cited",
}

_MIN_MATCH_RATIO = 0.88
_PROMOTE_MAX_LEN = 200


@dataclass
class OutlineEntry:
    level: int
    title: str
    page: int | None = None
    truncated: bool = False
    key: str = ""


@dataclass
class HeadingReport:
    mode: str = "none"
    outline_entries: int = 0
    matched: int = 0
    promoted: int = 0
    merged: int = 0
    duplicates_demoted: int = 0
    captions_demoted: int = 0
    changed: int = 0
    unmatched_outline: list[str] = field(default_factory=list)

    def summary(self) -> str:
        if self.mode == "outline":
            s = (f"{self.changed} heading(s) adjusted using the PDF outline "
                 f"({self.matched + self.promoted}/{self.outline_entries} outline entries found")
            extra = []
            if self.promoted:
                extra.append(f"{self.promoted} promoted from plain text")
            if self.merged:
                extra.append(f"{self.merged} split heading(s) merged")
            if self.duplicates_demoted:
                extra.append(f"{self.duplicates_demoted} duplicate(s) turned into text")
            s += ("; " + ", ".join(extra)) if extra else ""
            s += ")"
        elif self.mode == "heuristic":
            s = f"{self.changed} heading(s) adjusted by chapter heuristics"
        else:
            s = f"{self.changed} heading(s) adjusted"
        if self.captions_demoted:
            s += f", {self.captions_demoted} caption heading(s) turned into bold text"
        return s


# --------------------------------------------------------------------------- #
# Text helpers
# --------------------------------------------------------------------------- #
def _plain(text: str) -> str:
    """Heading text without Markdown/HTML decoration."""
    for rx in _INLINE_NOISE:
        text = rx.sub("", text)
    text = _LINK_RE.sub(r"\1", text)
    text = re.sub(r"[*_`]+", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _key(text: str) -> str:
    """Comparison key: lowercase letters/digits only (robust to spacing, accents, punctuation)."""
    text = _strip_accents(unicodedata.normalize("NFKC", _plain(text))).casefold()
    return re.sub(r"[\W_]+", "", text)


def _words(text: str) -> str:
    text = _strip_accents(unicodedata.normalize("NFKC", _plain(text))).casefold()
    return re.sub(r"[\W_]+", " ", text).strip()


def is_caption(text: str) -> bool:
    return bool(_CAPTION_RE.match(_plain(text)))


def _looks_like_chapter(text: str) -> bool:
    plain = _plain(text)
    if _CHAPTER_WORD_RE.match(plain) or _NUMBERED_CHAPTER_RE.match(plain):
        return True
    return _words(plain) in _MATTER_TITLES


# --------------------------------------------------------------------------- #
# Outline
# --------------------------------------------------------------------------- #
def read_pdf_outline(pdf_path) -> list[OutlineEntry]:
    """Read the PDF bookmarks with pypdfium2 (installed with marker). [] if unavailable."""
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return []
    try:
        pdf = pdfium.PdfDocument(str(pdf_path))
        try:
            raw = [(b.level, b.title or "", b.page_index) for b in pdf.get_toc()]
        finally:
            pdf.close()
    except Exception:
        return []
    return [OutlineEntry(level, title, page) for level, title, page in raw]


def prepare_outline(entries) -> list[OutlineEntry]:
    """
    Clean outline entries: drop empty titles, mark truncated ones, remove a
    single wrapping root entry (usually the book title) and make levels start
    at 1. Accepts OutlineEntry objects or (level, title[, page]) tuples.
    """
    out = []
    for e in entries:
        if not isinstance(e, OutlineEntry):
            e = OutlineEntry(int(e[0]), str(e[1]), e[2] if len(e) > 2 else None)
        title = _TRUNCATED_RE.sub("", e.title).strip()
        truncated = title != e.title.strip()
        key = _key(title)
        if not key:
            continue
        out.append(OutlineEntry(e.level, title, e.page, truncated, key))
    if not out:
        return out
    top = min(e.level for e in out)
    roots = [i for i, e in enumerate(out) if e.level == top]
    if len(roots) == 1 and roots[0] == 0 and len(out) > 1:
        out = out[1:]  # a single root wrapping the whole book
        top = min(e.level for e in out)
    for e in out:
        e.level = min(6, e.level - top + 1)
    return out


def _similar(a: str, b: str) -> bool:
    if a == b:
        return True
    if min(len(a), len(b)) < 4:
        return False
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio() >= _MIN_MATCH_RATIO


def _matches(entry: OutlineEntry, key: str) -> bool:
    """Does a heading/line key correspond to an outline entry?"""
    o = entry.key
    if not key:
        return False
    if entry.truncated:
        return len(key) >= len(o) and _similar(key[: len(o)], o)
    if _similar(key, o):
        return True
    # Outline titles are sometimes shortened versions of the printed heading.
    return len(o) >= 12 and key.startswith(o)


# --------------------------------------------------------------------------- #
# Document model
# --------------------------------------------------------------------------- #
@dataclass
class _Heading:
    line: int
    level: int
    text: str
    key: str
    new_level: int | None = None
    entry: int | None = None


def _scan(lines: list[str]) -> tuple[list[_Heading], set[int]]:
    headings, fenced, in_fence = [], set(), False
    for i, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            fenced.add(i)
            continue
        if in_fence:
            fenced.add(i)
            continue
        m = _HEADING_RE.match(line)
        if m and m.group(2):
            headings.append(_Heading(i, len(m.group(1)), m.group(2), _key(m.group(2))))
    return headings, fenced


def _merge_split_headings(lines, headings, outline, report) -> list[_Heading]:
    """Join consecutive headings whose concatenation is an outline title."""
    result: list[_Heading] = []
    i = 0
    while i < len(headings):
        h = headings[i]
        if i + 1 < len(headings):
            nxt = headings[i + 1]
            between = lines[h.line + 1: nxt.line]
            if all(not s.strip() for s in between):
                joined = h.key + nxt.key
                single = any(_matches(e, h.key) for e in outline)
                if not single and any(_matches(e, joined) for e in outline):
                    text = f"{h.text} {nxt.text}"
                    lines[h.line] = "#" * h.level + " " + text
                    for k in range(h.line + 1, nxt.line + 1):
                        lines[k] = None  # removed below
                    result.append(_Heading(h.line, h.level, text, joined))
                    report.merged += 1
                    i += 2
                    continue
        result.append(h)
        i += 1
    return result


def _align(headings: list[_Heading], outline: list[OutlineEntry]) -> list[tuple[int, int]]:
    """
    Longest monotonic alignment between headings and outline entries.
    Backtracking from the end prefers the LAST candidate heading for an entry,
    so a printed table of contents earlier in the book does not win.
    """
    n, m = len(headings), len(outline)
    match = [[_matches(outline[j], headings[i].key) for j in range(m)] for i in range(n)]
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        row, nrow = dp[i], dp[i + 1]
        for j in range(m):
            best = max(row[j + 1], nrow[j])
            if match[i][j]:
                best = max(best, row[j] + 1)
            nrow[j + 1] = best
    pairs = []
    i, j = n, m
    while i > 0 and j > 0:
        if match[i - 1][j - 1] and dp[i][j] == dp[i - 1][j - 1] + 1:
            pairs.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif dp[i][j] == dp[i - 1][j]:
            i -= 1
        else:
            j -= 1
    return pairs[::-1]


def _unquote(line: str) -> str:
    """A one-line blockquote ("> TITLE") is a common mis-tagged heading."""
    return re.sub(r"^\s*>\s?", "", line)


def _promotable(line: str) -> bool:
    """A standalone line that could be a heading marker forgot to tag."""
    s = _unquote(line).strip()
    if not s or len(s) > _PROMOTE_MAX_LEN:
        return False
    if s.startswith("**"):  # bold line
        return True
    if s.startswith(("#", "|", ">", "- ", "* ", "+ ", "[^", "!", "<")):
        return False
    if re.search(r"\s\d+$", s):  # "TÍTULO 35": printed table of contents entry
        return False
    return True


def _isolated(lines, i) -> bool:
    before = i == 0 or not (lines[i - 1] or "").strip()
    after = i + 1 >= len(lines) or not (lines[i + 1] or "").strip()
    return before and after


def _promote_missing(lines, headings, outline, aligned, fenced, report) -> list[_Heading]:
    """Promote isolated plain lines that match outline entries the alignment missed."""
    by_entry = {j: headings[i].line for i, j in aligned}
    heading_lines = {h.line for h in headings}
    promoted = []
    for j, entry in enumerate(outline):
        if j in by_entry:
            continue
        lo = max((ln for jj, ln in by_entry.items() if jj < j), default=-1)
        hi = min((ln for jj, ln in by_entry.items() if jj > j), default=len(lines))
        found = None
        for i in range(hi - 1, lo, -1):  # last candidate in the gap
            line = lines[i]
            if line is None or i in fenced or i in heading_lines or not _isolated(lines, i):
                continue
            if _promotable(line) and _matches(entry, _key(_unquote(line))):
                found = i
                break
        if found is None:
            report.unmatched_outline.append(entry.title)
            continue
        text = _plain(_unquote(lines[found]))
        h = _Heading(found, entry.level, text, _key(text), entry.level, j)
        lines[found] = "#" * entry.level + " " + text
        by_entry[j] = found
        heading_lines.add(found)
        promoted.append(h)
        report.promoted += 1
    return promoted


def _assign_relative(headings: list[_Heading], parent_default: int) -> None:
    """Place headings without a level one below their section, keeping relative depth."""
    parent = parent_default
    block: list[_Heading] = []

    def close_block():
        if not block:
            return
        base = min(h.level for h in block)
        for h in block:
            h.new_level = min(6, parent + 1 + (h.level - base))
        block.clear()

    for h in headings:
        if h.new_level is not None and h.entry is not None:
            close_block()
            parent = h.new_level
        elif h.new_level is None:
            block.append(h)
    close_block()


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #
def normalize_headings(markdown: str, outline=None) -> tuple[str, HeadingReport]:
    """
    Normalize heading levels. `outline` is a list of OutlineEntry or
    (level, title[, page]) tuples (e.g. from read_pdf_outline); when it is
    empty or does not match the document, heuristics are used instead.
    """
    report = HeadingReport()
    lines: list = markdown.split("\n")
    headings, fenced = _scan(lines)
    if not headings and not outline:
        return markdown, report
    original_lines = list(lines)

    entries = prepare_outline(outline or [])
    used_outline = False
    if entries:
        trial = list(lines)
        rep = HeadingReport(mode="outline", outline_entries=len(entries))
        hs = _merge_split_headings(trial, list(headings), entries, rep)
        aligned = _align(hs, entries)
        # Only trust the outline if it actually describes this document.
        if len(aligned) >= 2 and len(aligned) >= 0.3 * len(entries):
            used_outline = True
            lines, report, headings = trial, rep, hs
            report.matched = len(aligned)
            for i, j in aligned:
                headings[i].new_level = entries[j].level
                headings[i].entry = j
            headings += _promote_missing(lines, headings, entries, aligned, fenced, report)
            headings.sort(key=lambda h: h.line)
            _demote_contents_duplicates(lines, headings, entries, report)

    if not used_outline:
        report.mode = "heuristic"
        _heuristic_levels(headings)

    # Captions emitted as headings become bold paragraphs.
    for h in headings:
        if h.new_level != 0 and h.entry is None and is_caption(h.text):
            lines[h.line] = f"**{_plain(h.text)}**"
            h.new_level = 0
            report.captions_demoted += 1

    if used_outline:
        _assign_relative([h for h in headings if h.new_level != 0], parent_default=1)

    for h in headings:
        if h.new_level:
            lines[h.line] = "#" * h.new_level + " " + h.text

    report.changed = sum(
        1 for h in headings if lines[h.line] is not None and lines[h.line] != original_lines[h.line]
    )
    text = "\n".join(line for line in lines if line is not None)
    return text, report


def _demote_contents_duplicates(lines, headings, entries, report, min_cluster: int = 3) -> None:
    """
    Headings that repeat outline titles but were not aligned are usually a
    printed table of contents. Turn them into plain text, but only when several
    occur together (between two aligned headings), so a legitimate subsection
    that happens to share a title (e.g. "Ubicación") is kept.
    """
    cluster: list[_Heading] = []

    def close():
        if len(cluster) >= min_cluster:
            for d in cluster:
                lines[d.line] = _plain(d.text)
                d.new_level = 0
                report.duplicates_demoted += 1
        cluster.clear()

    for h in headings:
        if h.entry is not None:
            close()
        elif any(_matches(e, h.key) for e in entries):
            cluster.append(h)
    close()


def _heuristic_levels(headings: list[_Heading]) -> None:
    """Chapter-like headings -> H1, everything else renumbered below them."""
    content = [h for h in headings if not is_caption(h.text)]
    chapters = [h for h in content if _looks_like_chapter(h.text)]
    if len(chapters) >= 2:
        for h in chapters:
            h.new_level = 1
        # Headings at (or above) the chapters' original level are sections;
        # deeper ones keep their relative depth below them.
        levels = [h.level for h in chapters]
        chapter_level = max(set(levels), key=levels.count)
        others = [h for h in content if h.new_level is None]
        deeper = sorted({h.level for h in others if h.level > chapter_level})
        first_deeper = 3 if any(h.level <= chapter_level for h in others) else 2
        for h in others:
            if h.level <= chapter_level:
                h.new_level = 2
            else:
                h.new_level = min(6, first_deeper + deeper.index(h.level))
    elif content:
        # No recognizable chapters: just make the top level H1.
        base = min(h.level for h in content)
        for h in content:
            h.new_level = min(6, 1 + (h.level - base))
    for h in headings:
        if h.new_level is None:
            h.new_level = h.level


def load_outline_for(pdf_path: Path | str | None) -> list[OutlineEntry]:
    return read_pdf_outline(pdf_path) if pdf_path else []
