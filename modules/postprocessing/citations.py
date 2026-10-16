"""
Link author-year citations to their entries in the bibliography section.

    Modelski (1987)        ->  Modelski ([1987](#ref-modelski-1987))
    (Cassidy, 2002; Ernst, 2010)
                           ->  (Cassidy, [2002](#ref-cassidy-2002); Ernst, [2010](#ref-ernst-2010))

Only the year is turned into a link, so the wording itself is never altered.
A citation is linked only when an entry with the same year exists AND the
first author's surname (or the corporate author's name) appears right before
the year. Ambiguous or unmatched citations are left as plain text.

Bibliography entries look like (Spanish/APA-like styles):

    - Aglietta, M. (1979). Regulación y crisis del capitalismo...
    - Breznitz, D., y M. Murphree (2011). Run of The Red Queen...
    - Banco Mundial (2020). Indicadores del Desarrollo...
    - ——— (2019). Informe sobre el Desarrollo Mundial...   (same author as above)

Each entry gets an invisible anchor ``<span id="ref-..."></span>``, which both
Pandoc and Python-Markdown pass through as an HTML id.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_BIB_TITLE_RE = re.compile(
    r"^(bibliograf[ií]a|referencias(\s+bibliogr[aá]ficas)?|obras\s+citadas|"
    r"fuentes(\s+consultadas)?|references|bibliography|works\s+cited|literature(\s+cited)?)\b",
    re.IGNORECASE,
)
_ENTRY_RE = re.compile(
    r"^(?P<prefix>\s*(?:[-*+]|\d+\.)\s+)?(?P<authors>[^()]{1,200}?)\s*"
    r"(?:\((?:eds?|coords?|comps?|dirs?|trads?)\.?\)\s*)?"       # "Glasner, D. (ed.) (1997)"
    r"\((?P<years>[^()]*?\d{4}[^()]*)\)"                          # "(2016b, octubre)", "([1939] 2002)"
)
_ENTRY_YEAR_RE = re.compile(r"(?<!\d)(\d{4})([a-z])?(?![\d])")
_ACRONYM_RE = re.compile(r"\[([^\]]{2,15})\]")
_NAME_PARTICLES = {"van", "von", "de", "del", "der", "den", "di", "da", "dos", "du", "la", "le"}
_SAME_AUTHOR_RE = re.compile(r"^[\s\-—–_]+$")
_PAREN_GROUP_RE = re.compile(r"\(([^()]*)\)")
_YEAR_RE = re.compile(r"(?<![\d\w])(1[5-9]\d\d|20\d\d)([a-z])?(?![\d\w])")
_ANCHOR_RE = re.compile(r'<span id="ref-[^"]*"></span>')
_CONNECTORS = {"y", "and", "e", "et", "al", "eds", "ed", "coord", "coords", "comp", "comps", "trad", "the", "de", "del", "la", "los", "las", "van", "von", "der"}
_PRECEDING_WINDOW = 120
# "Rivera, Lujano y García (2018)": first author may be a few words before "(".
_NARRATIVE_MAX_DISTANCE = 45


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).casefold()


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _norm(s)).strip("-") or "ref"


@dataclass
class BibEntry:
    line: int
    names: list[str]           # first author + aliases: ["Comisión Económica ...", "CEPAL"]
    other_authors: list[str]
    years: list[tuple[str, str]]  # [("2002", ""), ("1939", "")] (year, letter suffix)
    anchor: str = ""

    @property
    def first_author(self) -> str:
        return self.names[0]


@dataclass
class CitationReport:
    entries: int = 0
    linked: int = 0
    section_found: bool = False

    def summary(self) -> str:
        if not self.section_found:
            return "no bibliography section found; citations not linked"
        return f"{self.entries} bibliography entr(y/ies) anchored, {self.linked} citation(s) linked"


def find_bibliography(lines: list[str]) -> tuple[int, int] | None:
    """Return (heading_line, end_line_exclusive) of the last bibliography section."""
    found = None
    for i, line in enumerate(lines):
        m = _HEADING_RE.match(line)
        if m and _BIB_TITLE_RE.match(m.group(2).strip("*_ ")):
            level = len(m.group(1))
            end = len(lines)
            for j in range(i + 1, len(lines)):
                h = _HEADING_RE.match(lines[j])
                if h and len(h.group(1)) <= level:
                    end = j
                    break
            found = (i, end)
    return found


def _split_authors(authors: str) -> tuple[list[str], list[str]]:
    """
    'Breznitz, D., y M. Murphree' -> (['Breznitz'], ['Murphree'])
    'Fondo Monetario Internacional [FMI]' -> (['Fondo Monetario Internacional', 'FMI'], [])
    'Van Gelderen' -> (['Van Gelderen', 'Gelderen'], [])
    """
    authors = authors.strip().rstrip(".,")
    acronyms = _ACRONYM_RE.findall(authors)
    authors = _ACRONYM_RE.sub("", authors).strip()
    if "," in authors:
        first, rest = authors.split(",", 1)
    else:  # corporate author, or a surname without initials
        first, rest = authors, ""
    first = first.strip()
    names = [first] + [a.strip() for a in acronyms]
    words = first.split()
    if len(words) > 1 and _norm(words[0]) in _NAME_PARTICLES:
        stripped = [w for w in words if _norm(w) not in _NAME_PARTICLES]
        if stripped:
            names.append(" ".join(stripped))
    others = []
    for tok in re.findall(r"[^\W\d_][\w'’\-]*", rest):
        if len(tok) > 2 and tok[0].isupper() and _norm(tok) not in _CONNECTORS:
            others.append(tok)
    return names, others


def parse_bibliography(lines: list[str], start: int, end: int) -> list[BibEntry]:
    entries: list[BibEntry] = []
    previous: tuple[list[str], list[str]] | None = None
    for i in range(start + 1, end):
        if lines[i].lstrip().startswith("[^"):  # footnote definition, not an entry
            continue
        m = _ENTRY_RE.match(_ANCHOR_RE.sub("", lines[i]))
        if not m:
            continue
        authors = m.group("authors")
        if _SAME_AUTHOR_RE.match(authors):
            if previous is None:
                continue
            names, others = previous
        else:
            names, others = _split_authors(authors)
            if not names[0] or not re.search(r"[^\W\d_]", names[0]):
                continue
        years = [(y, s or "") for y, s in _ENTRY_YEAR_RE.findall(m.group("years"))]
        # The edition actually cited comes first unless it is the bracketed
        # original: "([1939] 2002)" -> 2002 first, "(2014 [2013])" -> 2014 first.
        bracketed = {y for y in re.findall(r"\[(\d{4})\]", m.group("years"))}
        years.sort(key=lambda ys: ys[0] in bracketed)
        previous = (names, others)
        entries.append(BibEntry(i, names, others, years))

    used = set()
    for e in entries:
        year, suffix = e.years[0]
        base = f"ref-{_slug(e.first_author)}-{year}{suffix}"
        anchor, k = base, 2
        while anchor in used:
            anchor, k = f"{base}-{k}", k + 1
        used.add(anchor)
        e.anchor = anchor
    return entries


def _match_entry(
    window: str,
    year: str,
    suffix: str,
    by_year: dict[str, list[BibEntry]],
    max_distance: int | None = None,
) -> BibEntry | None:
    """Pick the entry for `year` whose first author appears in `window`.

    If max_distance is given, the first author's name must end within that
    many characters of the end of the window (narrative citations).
    """
    candidates = by_year.get(year, [])
    if suffix:
        candidates = [(e, s) for e, s in candidates if s == suffix] or candidates
    w = _norm(window)

    def positions(names: list[str]) -> list[int]:
        hits = [
            m.end()
            for name in names
            for m in re.finditer(rf"(?<!\w){re.escape(_norm(name))}(?!\w)", w)
        ]
        if max_distance is not None:
            hits = [h for h in hits if len(w) - h <= max_distance]
        return hits

    scored = []
    for e, _ in candidates:
        first_hits = positions(e.names)
        other_hits = positions(e.other_authors)
        if first_hits:
            # First author found: prefer more co-authors matched, then closest.
            scored.append(((1, len({h for h in other_hits}), max(first_hits)), e))
        elif other_hits:
            # Fallback for misspelled first authors ("Bryonjolfsson y McAfee").
            scored.append(((0, len(other_hits), max(other_hits)), e))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    best_key, best = scored[0]
    if best_key[0] == 0 and sum(1 for k, _ in scored if k[0] == 0) > 1:
        return None  # co-author-only match must be unambiguous
    return best


def _link_line(line: str, by_year: dict[str, list[BibEntry]]) -> tuple[str, int]:
    """Return line with citation years linked, and the number of links."""
    replacements = []
    for g in _PAREN_GROUP_RE.finditer(line):
        if g.start() > 0 and line[g.start() - 1] == "]":
            continue  # markdown link target: [text](...)
        content, base = g.group(1), g.start(1)
        if "](" in content or "http" in content:
            continue
        for y in _YEAR_RE.finditer(content):
            if y.start() > 0 and content[y.start() - 1] == "[":
                continue  # already linked
            seg_start = content.rfind(";", 0, y.start()) + 1
            segment = content[seg_start:y.start()]
            window, max_distance = segment, None
            if not re.search(r"[^\W\d_]{2,}", segment):
                # "Modelski (1987)" or "(1988, 2002)": names precede the group.
                window = line[max(0, g.start() - _PRECEDING_WINDOW):g.start()] + segment
                max_distance = _NARRATIVE_MAX_DISTANCE + len(segment)
            entry = _match_entry(window, y.group(1), y.group(2) or "", by_year, max_distance)
            if entry:
                s, e = base + y.start(), base + y.end()
                replacements.append((s, e, f"[{line[s:e]}](#{entry.anchor})"))
    for s, e, new in sorted(replacements, reverse=True):
        line = line[:s] + new + line[e:]
    return line, len(replacements)


def link_citations(markdown: str) -> tuple[str, CitationReport]:
    lines = markdown.split("\n")
    report = CitationReport()
    section = find_bibliography(lines)
    if not section:
        return markdown, report
    report.section_found = True
    start, end = section
    entries = parse_bibliography(lines, start, end)
    report.entries = len(entries)
    if not entries:
        return markdown, report

    # Anchor every entry (idempotent).
    for e in entries:
        line = _ANCHOR_RE.sub("", lines[e.line])
        m = re.match(r"^(\s*(?:[-*+]|\d+\.)\s+)?", line)
        cut = m.end() if m else 0
        lines[e.line] = f'{line[:cut]}<span id="{e.anchor}"></span>{line[cut:]}'

    by_year: dict[str, list[tuple[BibEntry, str]]] = {}
    for e in entries:
        for year, suffix in e.years:
            by_year.setdefault(year, []).append((e, suffix))

    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if in_fence or start <= i < end or _HEADING_RE.match(line) or line.lstrip().startswith("!["):
            continue
        lines[i], n = _link_line(line, by_year)
        report.linked += n

    return "\n".join(lines), report
