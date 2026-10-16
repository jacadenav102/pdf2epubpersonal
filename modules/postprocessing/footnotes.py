"""
Convert PDF-style footnotes in marker-pdf output into linked Markdown footnotes.

marker-pdf emits footnotes as plain text:

    ...apreciándose cierto acuerdo entre ellos.3 De una parte...    <- reference
    <sup>3</sup> Entre estos autores figuran Tylecote (1992)...     <- note text
    3 Entre estos autores figuran Tylecote (1992)...                <- (variant)

This module rewrites them as standard footnotes understood by both Pandoc and
Python-Markdown's ``footnotes`` extension:

    ...apreciándose cierto acuerdo entre ellos.[^c2-3] De una parte...
    [^c2-3]: Entre estos autores figuran Tylecote (1992)...

Design notes:
* Notes are numbered per *scope*. A new scope starts at every level-1 heading
  or whenever the note numbering restarts. Labels include the scope so they
  are unique across the whole book.
* A note's reference is searched for between the previous resolved reference
  of the same scope and the note text itself. Candidates are ranked:
  ``<sup>n</sup>`` > number glued to punctuation (``ellos.3``) > number glued
  to a lowercase word (``hegemónicos3``). The closest candidate wins.
  Numbers after Roman numerals or digits (``gráfica I.3``, ``2.3``) are ignored.
* Notes whose reference cannot be found are left untouched (never guessed).
* Note texts are moved to the end of their scope. If a note interrupted a
  paragraph (page break), the two halves of the paragraph are re-joined.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

_HEADING_RE = re.compile(r"^(#{1,6})\s")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_SUP_DEF_RE = re.compile(r"^\s*<sup>(\d{1,3})</sup>\s*(\S.*)$")
_PLAIN_DEF_RE = re.compile(r"^\s*(\d{1,3})\s+([A-ZÁÉÍÓÚÑÜ\"“«¿¡(].*)$")
# "gráfica I.3", "cuadro IV.2", "2.3": the number is part of a numbering.
# The Roman numeral must be a standalone token (so "I+D.1" is still a reference).
_ROMAN_OR_DIGIT_BEFORE_DOT_RE = re.compile(r"(?:(?<![^\s(])[IVXLCDM]+|\d)\.$")
_TERMINAL_PUNCT = tuple('.!?:;»"”)]')

# A plain "N Text" line is only treated as a note if it is long enough and
# its number follows the current sequence (avoids numbered titles/lists).
_MIN_PLAIN_DEF_LEN = 25
_MAX_PLAIN_DEF_GAP = 3
# Lowercase-glued references need a real word before them ("m2" is a unit).
_MIN_GLUED_WORD_LEN = 3
_MIN_UPPER_GLUED_WORD_LEN = 5


@dataclass
class FootnoteReport:
    linked: int = 0
    unresolved: list[tuple[int, int]] = field(default_factory=list)  # (line_no, note number)

    def summary(self) -> str:
        msg = f"{self.linked} footnote(s) linked"
        if self.unresolved:
            nums = ", ".join(f"{n} (line {ln})" for ln, n in self.unresolved[:10])
            more = "..." if len(self.unresolved) > 10 else ""
            msg += f"; {len(self.unresolved)} left unchanged (reference not found): {nums}{more}"
        return msg


@dataclass
class _Def:
    line: int
    number: int
    text: str
    scope: int
    is_sup: bool
    ref: tuple[int, int, int] | None = None  # (line, start, end)


def _is_structural(line: str) -> bool:
    """Lines that never end a paragraph's text flow (tables, images, headings)."""
    s = line.lstrip()
    return s.startswith("|") or s.startswith("![") or bool(_HEADING_RE.match(s))


def _no_references(line: str) -> bool:
    """Lines where references must not be searched (tables and images).

    Headings are allowed: chapter titles often carry a note ("...CAPITALISTA1").
    """
    s = line.lstrip()
    return s.startswith("|") or s.startswith("![")


def _collect_definitions(lines: list[str]) -> list[_Def]:
    """
    Return note definitions, each tagged with its numbering scope.

    A new scope starts whenever the note numbering restarts (n <= previous n).
    Heading levels are deliberately NOT used: marker-pdf often assigns
    chapter titles inconsistent levels (e.g. "###" chapters and a stray "#"
    figure title), and numbering restarts are what actually define a chapter's
    notes.
    """
    defs: list[_Def] = []
    scope = 0
    last_number = 0
    in_fence = False

    for i, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        m = _SUP_DEF_RE.match(line)
        is_sup = bool(m)
        if not m:
            m = _PLAIN_DEF_RE.match(line)
            if not m or len(line.strip()) < _MIN_PLAIN_DEF_LEN:
                continue
            n = int(m.group(1))
            in_sequence = last_number < n <= last_number + _MAX_PLAIN_DEF_GAP
            if not (in_sequence or n == 1):
                continue
        n = int(m.group(1))
        if n <= last_number and defs:  # numbering restarted: new chapter/scope
            scope += 1
        last_number = n
        defs.append(_Def(i, n, m.group(2).strip(), scope, is_sup))

    return defs


def _candidates(line: str, number: int, start_col: int):
    """Yield (priority, start, end) reference candidates for `number` in line."""
    s = str(number)
    tail = r"(?!\d)(?=[\s.,;:)\]»”\"']|$)"
    for m in re.finditer(rf"<sup>{s}</sup>", line):
        if m.start() >= start_col:
            yield 0, m.start(), m.end()
    for m in re.finditer(rf"(?<=[.,;:!?)\]\"”»’']){s}{tail}", line):
        if m.start() < start_col:
            continue
        before = line[: m.start()]
        if len(before) >= 2 and before[-2].isdigit():
            continue  # "2.3", "1,5"
        if before.endswith(".") and _ROMAN_OR_DIGIT_BEFORE_DOT_RE.search(before):
            continue  # "gráfica I.3"
        yield 1, m.start(), m.end()
    for m in re.finditer(rf"(?<=[a-záéíóúñüàèìòùç]){s}{tail}", line):
        if m.start() < start_col:
            continue
        word = re.search(r"[^\W\d_]+$", line[: m.start()])
        if word and len(word.group(0)) >= _MIN_GLUED_WORD_LEN:
            yield 2, m.start(), m.end()
    # "economías emergentes; 12 previamente": detached number between a
    # comma/semicolon and a lowercase word. The leading space is consumed.
    for m in re.finditer(rf"(?<=[,;]) {s}(?= [a-záéíóúñü])", line):
        if m.start() >= start_col:
            yield 3, m.start(), m.end()
    # "DESARROLLO CAPITALISTA1" (uppercase titles): require a long all-caps
    # word so acronyms such as "G20" or "CO2" never match.
    for m in re.finditer(rf"(?<=[A-ZÁÉÍÓÚÑÜ]){s}{tail}", line):
        if m.start() < start_col:
            continue
        word = re.search(r"[^\W\d_]+$", line[: m.start()])
        if word and len(word.group(0)) >= _MIN_UPPER_GLUED_WORD_LEN and word.group(0).isupper():
            yield 4, m.start(), m.end()


def _find_reference(lines, skip_lines, start, end_line, number):
    """Best reference for `number` in [start, end_line). start = (line, col)."""
    best = None  # (priority, -line, -col, line, s, e)
    start_line, start_col = start
    for li in range(start_line, end_line):
        if li in skip_lines or _no_references(lines[li]):
            continue
        col = start_col if li == start_line else 0
        for prio, s, e in _candidates(lines[li], number, col):
            key = (prio, -li, -s)
            if best is None or key < best[0]:
                best = (key, (li, s, e))
    return best[1] if best else None


def _label(d: _Def) -> str:
    return f"c{d.scope + 1}-{d.number}"


def _ends_paragraph(line: str) -> bool:
    s = line.rstrip()
    return not s or s.endswith(_TERMINAL_PUNCT) or _is_structural(s) or s.startswith(("-", "*", ">", "[^"))


def link_footnotes(markdown: str) -> tuple[str, FootnoteReport]:
    """Rewrite plain-text footnotes as linked Markdown footnotes."""
    lines = markdown.split("\n")
    defs = _collect_definitions(lines)
    report = FootnoteReport()
    if not defs:
        return markdown, report

    fence_lines = set()
    heading_lines = []
    in_fence = False
    for i, line in enumerate(lines):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            fence_lines.add(i)
        elif in_fence:
            fence_lines.add(i)
        elif _HEADING_RE.match(line):
            heading_lines.append(i)

    def_lines = {d.line for d in defs}
    skip = def_lines | fence_lines

    # Resolve references left to right through the whole document. References
    # appear in reading order, so the search for a note starts after the
    # previous note's reference. When a new scope (chapter) starts, it also
    # starts after the previous scope's last note text: a chapter's first
    # reference comes after the previous chapter's notes.
    cursor = (0, 0)
    last_def_line: dict[int, int] = {}
    current_scope = defs[0].scope
    for d in defs:
        if d.scope != current_scope:
            cursor = max(cursor, (last_def_line[current_scope] + 1, 0))
            current_scope = d.scope
        d.ref = _find_reference(lines, skip, cursor, d.line, d.number)
        if d.ref:
            cursor = (d.ref[0], d.ref[2])
        last_def_line[d.scope] = d.line

    # Apply reference replacements (right to left within each line).
    replacements: dict[int, list[tuple[int, int, str]]] = {}
    for d in defs:
        if d.ref:
            li, s, e = d.ref
            replacements.setdefault(li, []).append((s, e, f"[^{_label(d)}]"))
            report.linked += 1
        else:
            report.unresolved.append((d.line + 1, d.number))
    for li, reps in replacements.items():
        line = lines[li]
        for s, e, new in sorted(reps, reverse=True):
            line = line[:s] + new + line[e:]
        lines[li] = line

    # Remove resolved note lines; collect them per scope.
    removed = set()
    notes_by_scope: dict[int, list[str]] = {}
    for d in defs:
        if d.ref:
            removed.add(d.line)
            notes_by_scope.setdefault(d.scope, []).append(f"[^{_label(d)}]: {d.text}")

    # Where to emit each scope's notes: before the first heading that follows
    # the scope's last note (i.e. still inside the chapter, never inside a
    # later section such as the bibliography), and no later than the first
    # note of the next scope.
    first_def_line: dict[int, int] = {}
    for d in defs:
        first_def_line.setdefault(d.scope, d.line)
    flush_at: dict[int, list[int]] = {}
    for scope in notes_by_scope:
        last = last_def_line[scope]
        pos = next((h for h in heading_lines if h > last), len(lines))
        pos = min(pos, first_def_line.get(scope + 1, len(lines)))
        flush_at.setdefault(pos, []).append(scope)

    def flush(position: int) -> None:
        for scope in sorted(flush_at.get(position, [])):
            _flush_notes(out, notes_by_scope.pop(scope, []))

    # Rebuild, re-joining paragraphs that a removed note had split.
    out: list[str] = []
    i = 0
    while i < len(lines):
        if i in flush_at:
            flush(i)
        if i in removed:
            j = i
            while (
                j < len(lines)
                and (j == i or j not in flush_at)
                and (j in removed or not lines[j].strip())
            ):
                j += 1
            prev_idx = len(out) - 1
            while prev_idx >= 0 and not out[prev_idx].strip():
                prev_idx -= 1
            nxt = lines[j] if j < len(lines) else ""
            can_join = (
                prev_idx >= 0
                and not _ends_paragraph(out[prev_idx])
                and nxt[:1].islower()
                and j not in flush_at
            )
            if can_join:
                del out[prev_idx + 1:]
                out[prev_idx] = out[prev_idx].rstrip() + " " + nxt.lstrip()
                i = j + 1
            else:
                # Drop the note and collapse surrounding blank lines to one.
                while out and not out[-1].strip():
                    out.pop()
                out.append("")
                i = j
            continue
        out.append(lines[i])
        i += 1
    flush(len(lines))
    for scope in sorted(notes_by_scope):  # defensive; should be empty
        _flush_notes(out, notes_by_scope[scope])

    return "\n".join(out), report


def _flush_notes(out: list[str], notes: list[str]) -> None:
    if not notes:
        return
    while out and not out[-1].strip():
        out.pop()
    out.append("")
    for note in notes:
        out.append(note)
        out.append("")
