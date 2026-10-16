"""
Recover tables that marker's layout model labelled as text.

Borderless / "booktabs" tables (only horizontal rules) are sometimes detected
as a Caption or Text block, so marker outputs their cells as one flat
paragraph ("Fase del ciclo Preferencia por el orden … 1 alta baja 2 alta …")
and no table processor (local or LLM) ever sees them.

TableRescueProcessor runs just before marker's TableProcessor and relabels
such blocks as Table, so they then get normal table recognition (and the
Claude table correction when --use-llm is on). A block is relabelled only on
geometric evidence that prose never shows: lines side by side in the same
row (columns), plus either an adjacent table caption ("CUADRO I.1",
"Table 3", "Tabla 2"...) or a strong column pattern. Lists, pictures and
other block types are never touched.

The geometry helpers are plain functions on (x0, y0, x1, y1) boxes so they
can be tested without marker.
"""
from __future__ import annotations

import re
from copy import deepcopy
from html import escape as html_escape
from typing import Annotated, Iterable, Sequence

Box = Sequence[float]  # (x0, y0, x1, y1)

TABLE_CAPTION_RE = re.compile(
    r"^\W*(?:cuadro|tabla|table|tableau|tabelle|quadro|tabella|tab\.)\s+"
    r"(?:[0-9]+|[IVXLC]+)(?:[.\-–][0-9A-Za-z]+)*\b",
    re.IGNORECASE,
)

# Row grouping: lines overlap vertically by at least this fraction of the
# shorter line's height.
ROW_OVERLAP = 0.5
# Two lines in a row are separate columns if the horizontal gap between them
# is at least this many line-heights (a word space is ~0.3).
COLUMN_GAP = 0.8


FIGURE_CAPTION_RE = re.compile(
    r"^\W*(?:gr[aá]fica|gr[aá]fico|figura|fig\.|figure|chart|graph|diagrama|diagram|esquema|"
    r"mapa|map|ilustraci[oó]n|illustration|graphique|abbildung|abb\.|grafik|grafico|exhibit|"
    r"l[aá]mina|plate)\s+(?:[0-9]+|[IVXLC]+)(?:[.\-–][0-9A-Za-z]+)*\b",
    re.IGNORECASE,
)


# Lines that end a table region: source / notes under the table.
SOURCE_RE = re.compile(
    r"^\W*(?:fuentes?|sources?|notas?|notes?|elaboraci[oó]n propia|quelle|fonte|nota bene)\b",
    re.IGNORECASE,
)


def is_source_line(text: str) -> bool:
    return bool(SOURCE_RE.match(text.strip()))


# A "Table" block starting with a caption and this short is just the caption.
CAPTION_MAX_LINES = 3


def is_caption_only(line_count: int) -> bool:
    return 0 < line_count <= CAPTION_MAX_LINES


def is_table_caption(text: str) -> bool:
    return bool(TABLE_CAPTION_RE.match(text.strip()))


def is_figure_caption(text: str) -> bool:
    return bool(FIGURE_CAPTION_RE.match(text.strip()))


def caption_kind(text: str) -> str | None:
    if is_table_caption(text):
        return "table"
    if is_figure_caption(text):
        return "figure"
    return None


def group_rows(boxes: Iterable[Box]) -> list[list[Box]]:
    """Group line boxes into visual rows (vertical overlap), top to bottom."""
    rows: list[list[Box]] = []
    for box in sorted(boxes, key=lambda b: (b[1], b[0])):
        h = max(box[3] - box[1], 1e-6)
        for row in rows:
            ref = row[0]
            overlap = min(box[3], ref[3]) - max(box[1], ref[1])
            if overlap >= ROW_OVERLAP * min(h, max(ref[3] - ref[1], 1e-6)):
                row.append(box)
                break
        else:
            rows.append([box])
    return rows


def _has_columns(row: list[Box]) -> bool:
    if len(row) < 2:
        return False
    row = sorted(row, key=lambda b: b[0])
    height = min(b[3] - b[1] for b in row) or 1.0
    return any(nxt[0] - cur[2] >= COLUMN_GAP * height for cur, nxt in zip(row, row[1:]))


def column_rows(boxes: Iterable[Box]) -> tuple[int, int]:
    """(rows with side-by-side columns, total rows)."""
    rows = group_rows(boxes)
    return sum(1 for r in rows if _has_columns(r)), len(rows)


def _vertical(box: Box) -> bool:
    w, h = box[2] - box[0], box[3] - box[1]
    return h > 2.5 * max(w, 1e-6) and h > 20


_NUMERIC_LABEL_RE = re.compile(r"^[\s\-–+−]*[\d.,%]+(?:\s+[\-–+−]?[\d.,%]+)*\s*%?$")


def numeric_ratio(texts: Sequence[str]) -> float:
    """Share of non-empty lines that are only numbers (axis ticks: "-1.5", "2007-01", "20%")."""
    texts = [t.strip() for t in texts if t and t.strip()]
    if not texts:
        return 0.0
    numeric = sum(1 for t in texts if _NUMERIC_LABEL_RE.match(t) or re.fullmatch(r"\d{4}-\d{2}", t))
    return numeric / len(texts)


def is_label_text(text: str, max_words: int = 25) -> bool:
    """Short text that reads like a chart label/legend, not a sentence."""
    t = " ".join(text.split())
    if not t or caption_kind(t):
        return False
    if len(t.split()) > max_words or re.search(r"[.;:!?]$", t):
        return False
    return True


def looks_like_figure(boxes: Sequence[Box], block_box: Box | None = None, texts: Sequence[str] | None = None) -> bool:
    """
    Text that is really the labels of a vector chart/diagram: rotated (vertical)
    labels, axis tick values (mostly numeric lines), or many short labels
    scattered across the block.
    """
    if len(boxes) < 4:
        return False
    if any(_vertical(b) for b in boxes):
        return True
    if texts is not None and numeric_ratio(texts) >= 0.6:
        return True
    x0 = min(b[0] for b in boxes) if block_box is None else block_box[0]
    x1 = max(b[2] for b in boxes) if block_box is None else block_box[2]
    width = max(x1 - x0, 1e-6)
    widths = sorted(b[2] - b[0] for b in boxes)
    median = widths[len(widths) // 2]
    multi, total = column_rows(boxes)
    return median < 0.25 * width and multi >= 2


def looks_like_table(boxes: Sequence[Box], has_caption: bool) -> bool:
    """Decide from line geometry whether a text block is really a table."""
    if len(boxes) < 3 or any(_vertical(b) for b in boxes):
        return False
    multi, total = column_rows(boxes)
    if total < 2:
        return False
    if has_caption:
        return multi >= 1
    return multi >= 3 and multi >= 0.5 * total


def looks_like_split_table(boxes: Sequence[Box]) -> bool:
    """
    Lines gathered from several blocks under a table caption: a table if at
    least two rows have side-by-side columns (prose blocks stacked vertically
    never do).
    """
    if len(boxes) < 3 or any(_vertical(b) for b in boxes):
        return False
    multi, _ = column_rows(boxes)
    return multi >= 2


def table_region(items, caption_index: int, content_width: float, prose_width: float = 0.85):
    """
    Pick the blocks forming the table under a caption.

    items: per-block dicts in page order with keys "box", "kind" (caption kind
    or None), "type" (marker block type name), "source" (bool), "prose" (bool:
    multi-line block without columns), "width".
    Returns (indices, closed) where closed tells whether a source/notes line
    ended the region, or None when the region already holds a table/picture.
    """
    cap = items[caption_index]["box"]
    below = [
        i for i, it in enumerate(items)
        if i != caption_index and it["box"][1] >= cap[3] - 3
    ]
    below.sort(key=lambda i: (items[i]["box"][1], items[i]["box"][0]))
    region, closed = [], False
    for i in below:
        it = items[i]
        if it["source"]:
            closed = True
            break
        if it["kind"] or it["type"] in ("PageFooter", "Footnote"):
            break
        if it["type"] in ("Table", "Picture", "Figure", "TableOfContents", "Form"):
            return None  # the table was detected after all
        region.append(i)
    if not closed:
        # Without a source line, stop at the first full-width paragraph.
        for k, i in enumerate(region):
            if items[i]["prose"] and items[i]["width"] >= prose_width * content_width:
                region = region[:k]
                break
    return region, closed


def trimmed_table_top(table: Box, caption: Box, min_overlap: float = 0.5) -> float | None:
    """
    New top edge for a table box that swallows its caption at the top, or
    None when they don't overlap that way (caption below/beside the table, or
    the table would become too small).
    """
    tx0, ty0, tx1, ty1 = table
    cx0, cy0, cx1, cy1 = caption
    area = max((cx1 - cx0) * (cy1 - cy0), 1e-6)
    inter = max(0.0, min(tx1, cx1) - max(tx0, cx0)) * max(0.0, min(ty1, cy1) - max(ty0, cy0))
    if inter / area < min_overlap:
        return None
    if cy0 > ty0 + 0.3 * (ty1 - ty0):  # caption is not at the top of the table
        return None
    new_top = cy1 + 0.5
    if ty1 - new_top < 2 * (cy1 - cy0):  # nothing left of the table
        return None
    return new_top


SPILL_OVERLAP = 0.6


def table_overlap(a: Box, b: Box) -> float:
    """Intersection area over the smaller box's area (1.0 = one box inside the other)."""
    inter = max(0.0, min(a[2], b[2]) - max(a[0], b[0])) * max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    smaller = min((a[2] - a[0]) * (a[3] - a[1]), (b[2] - b[0]) * (b[3] - b[1]))
    return inter / smaller if smaller > 0 else 0.0


def caption_continuation(
    caption: Box,
    runs: Sequence[tuple[Box, str]],
    max_rows: int = 2,
    max_gap: float = 0.8,
) -> tuple[list[str], float] | None:
    """
    Caption lines that sit inside the top of a table box, right under the
    caption above it (e.g. the second line "en los Estados Unidos, 1983-2014").

    runs: PDF text runs (box, text) inside the table box.
    Returns (texts, new table top) or None. A continuation row is a single
    text run (no columns) whose gap to the line above is below max_gap line
    heights; the table proper starts at the first row with columns or a
    larger gap.
    """
    cx0, cy0, cx1, cy1 = caption
    rows = group_rows([box for box, _ in runs])
    if len(rows) <= max_rows:
        return None  # nothing would be left of the table
    texts, prev_bottom = [], cy1
    for row in rows[:max_rows]:
        top = min(b[1] for b in row)
        bottom = max(b[3] for b in row)
        height = max(bottom - top, 1e-6)
        if _has_columns(row) or top - prev_bottom > max_gap * height:
            break
        x0, x1 = min(b[0] for b in row), max(b[2] for b in row)
        if x1 < cx0 or x0 > cx1:  # not under the caption
            break
        row_text = " ".join(
            text.strip() for box, text in sorted(runs, key=lambda r: r[0][0]) if box in row and text.strip()
        )
        if not row_text or numeric_ratio(row_text.split()) > 0.5:
            break
        texts.append(row_text)
        prev_bottom = bottom
    if not texts:
        return None
    return texts, prev_bottom + 0.5


def classify_block(
    boxes: Sequence[Box],
    nearest_caption: str | None,
    block_box: Box | None = None,
    texts: Sequence[str] | None = None,
) -> str | None:
    """
    "table", "figure" or None (leave as text), given the line boxes (and
    optionally line texts) of a text/caption block and the kind of the
    nearest caption ("table", "figure" or None).
    """
    if nearest_caption == "figure":
        return "figure" if looks_like_figure(boxes, block_box, texts) else None
    if looks_like_table(boxes, has_caption=nearest_caption == "table"):
        return "table"
    return None


# --------------------------------------------------------------------------- #
# marker processor
# --------------------------------------------------------------------------- #
try:
    from marker.processors import BaseProcessor
    from marker.schema import BlockTypes
    from marker.schema.polygon import PolygonBox
    from marker.schema.registry import get_block_class
except ImportError:  # marker not installed: helpers above remain usable
    BaseProcessor = object
    BlockTypes = None

PROCESSOR_PATH = "modules.table_rescue.TableRescueProcessor"


class _PdfText:
    """Text inside a box of a PDF page (marker coordinates: points, top-left origin)."""

    def __init__(self, path):
        self.pdf = None
        if path:
            try:
                import pypdfium2 as pdfium

                self.pdf = pdfium.PdfDocument(str(path))
            except Exception:
                self.pdf = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        if self.pdf is not None:
            self.pdf.close()

    def get(self, page, bbox) -> str:
        if self.pdf is None or not 0 <= page.page_id < len(self.pdf):
            return ""
        try:
            pdf_page = self.pdf[page.page_id]
            width, height = pdf_page.get_size()
            scale = width / max(page.polygon.width, 1e-6)  # marker page box -> PDF points
            x0, y0, x1, y1 = (v * scale for v in bbox)
            text_page = pdf_page.get_textpage()
            text = text_page.get_text_bounded(left=x0, bottom=height - y1, right=x1, top=height - y0)
            text_page.close()
            pdf_page.close()
            return text or ""
        except Exception:
            return ""

    def runs(self, page, bbox) -> list[tuple[tuple[float, float, float, float], str]]:
        """Text runs (marker-coordinate box, text) whose centre lies inside bbox."""
        if self.pdf is None or not 0 <= page.page_id < len(self.pdf):
            return []
        try:
            pdf_page = self.pdf[page.page_id]
            width, height = pdf_page.get_size()
            scale = width / max(page.polygon.width, 1e-6)
            bx0, by0, bx1, by1 = bbox
            text_page = pdf_page.get_textpage()
            out = []
            for k in range(text_page.count_rects()):
                left, bottom, right, top = text_page.get_rect(k)
                box = (left / scale, (height - top) / scale, right / scale, (height - bottom) / scale)
                mx, my = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
                if bx0 <= mx <= bx1 and by0 <= my <= by1:
                    text = text_page.get_text_bounded(left=left, bottom=bottom, right=right, top=top)
                    out.append((box, text or ""))
            text_page.close()
            pdf_page.close()
            return out
        except Exception:
            return []


class TableRescueProcessor(BaseProcessor):
    """
    Relabel Caption/Text blocks that are really tables (-> Table) or the text
    labels of vector charts next to a figure caption (-> Picture, so the
    chart is kept as an image).
    """

    table_rescue_enabled: Annotated[bool, "Relabel text blocks that are really tables or charts."] = True
    table_rescue_caption_window: Annotated[int, "Blocks before/after to look for a caption."] = 2
    table_rescue_label_margin: Annotated[
        float, "Distance (PDF points) within which label blocks are merged into a rescued chart."
    ] = 15.0

    def __call__(self, document):
        if not self.table_rescue_enabled or BlockTypes is None:
            return
        candidates = (BlockTypes.Caption, BlockTypes.Text)
        with _PdfText(getattr(document, "filepath", None)) as pdf_text:
            self._process(document, candidates, pdf_text)

    def _process(self, document, candidates, pdf_text):
        for page in document.pages:
            blocks = [b for b in page.structure_blocks(document) if not b.removed]
            kinds = [caption_kind(b.raw_text(document)) for b in blocks]
            # Captions mislabelled as running headers/footers would be dropped.
            # A caption line detected as a "table" of its own gets garbled into cells.
            for i, block in enumerate(blocks):
                if not kinds[i]:
                    continue
                if block.block_type in (BlockTypes.PageHeader, BlockTypes.PageFooter):
                    blocks[i] = self._relabel(page, block, BlockTypes.Caption)
                elif block.block_type == BlockTypes.Text and is_caption_only(
                    len(block.contained_blocks(document, (BlockTypes.Line,)))
                ):
                    # A caption typed as Text at the top of a page gets glued to
                    # the paragraph ending the previous page (hyphenated words).
                    blocks[i] = self._relabel(page, block, BlockTypes.Caption)
            for i, block in enumerate(blocks):
                if block.block_type != BlockTypes.Table:
                    continue
                # Table blocks often carry no text lines yet: then read the PDF text in their box.
                own_lines = block.contained_blocks(document, (BlockTypes.Line,))
                text = block.raw_text(document) if own_lines else pdf_text.get(page, block.polygon.bbox)
                lines = [ln for ln in text.splitlines() if ln.strip()]
                count = len(own_lines) if own_lines else len(lines)
                if caption_kind(text) == "table" and is_caption_only(count):
                    kinds[i] = "table"
                    caption = self._relabel(page, block, BlockTypes.Caption)
                    if not own_lines:  # nothing to render from: give it the PDF text
                        caption.html = "<p>" + html_escape(" ".join(ln.strip() for ln in lines)) + "</p>"
                    blocks[i] = caption
            self._keep_captions_out_of_tables(document, page, blocks, kinds)
            self._pull_caption_continuations(document, page, blocks, kinds, pdf_text)
            self._absorb_table_spill(document, page)
            for i, block in enumerate(blocks):
                if block.block_type not in candidates or kinds[i]:
                    continue  # not a candidate, or the caption itself
                if block.removed or block.ignore_for_output:
                    continue  # already absorbed into a picture
                lines = block.contained_blocks(document, (BlockTypes.Line,))
                boxes = [ln.polygon.bbox for ln in lines]
                texts = [ln.raw_text(document) for ln in lines]
                kind = classify_block(boxes, self._nearest_caption(kinds, i), block.polygon.bbox, texts)
                if kind == "table":
                    self._relabel(page, block, BlockTypes.Table)
                elif kind == "figure":
                    picture = self._relabel(page, block, BlockTypes.Picture)
                    self._absorb_labels(document, picture, blocks, kinds, candidates)
            self._merge_split_tables(document, page)

    @staticmethod
    def _keep_captions_out_of_tables(document, page, blocks, kinds):
        """
        A table box that overlaps its caption makes marker's TableProcessor
        delete the caption (blocks >95% inside a table are dropped). Move the
        table's top edge below such a caption.
        """
        captions = [b for b, k in zip(blocks, kinds) if k == "table" and b.block_type != BlockTypes.Table]
        # Captions can also sit inside a TableGroup next to the table.
        nested = page.contained_blocks(document, (BlockTypes.Caption, BlockTypes.Text, BlockTypes.SectionHeader))
        seen = {id(b) for b in captions}
        captions += [
            b for b in nested
            if id(b) not in seen and not b.removed and caption_kind(b.raw_text(document)) == "table"
        ]
        if not captions:
            return
        for table in page.contained_blocks(document, (BlockTypes.Table,)):
            if table.removed:
                continue
            for cap in captions:
                tx0, ty0, tx1, ty1 = table.polygon.bbox
                cx0, cy0, cx1, cy1 = cap.polygon.bbox
                new_top = trimmed_table_top((tx0, ty0, tx1, ty1), (cx0, cy0, cx1, cy1))
                if new_top is not None:
                    table.polygon = PolygonBox.from_bbox([tx0, new_top, tx1, ty1])

    @staticmethod
    def _pull_caption_continuations(document, page, blocks, kinds, pdf_text):
        """
        A caption whose last line(s) ended up inside the table box right below
        it: move those lines into the caption and the table top below them, so
        they don't become a bogus first table row.
        """
        captions = [
            b for b, k in zip(blocks, kinds)
            if k == "table" and b.block_type != BlockTypes.Table and not b.removed
        ]
        if not captions:
            return
        for table in page.contained_blocks(document, (BlockTypes.Table,)):
            if table.removed:
                continue
            tx0, ty0, tx1, ty1 = table.polygon.bbox
            for cap in captions:
                cx0, cy0, cx1, cy1 = cap.polygon.bbox
                line_h = min((cy1 - cy0), 14.0) or 10.0
                if not (cy1 - 2 <= ty0 <= cy1 + line_h) or cx1 < tx0 or cx0 > tx1:
                    continue  # caption is not right above this table
                found = caption_continuation((cx0, cy0, cx1, cy1), pdf_text.runs(page, (tx0, ty0, tx1, ty1)))
                if not found:
                    continue
                texts, new_top = found
                if ty1 - new_top < 2 * line_h:
                    continue
                cap_text = " ".join(cap.raw_text(document).split())
                cap.html = "<p>" + html_escape(" ".join([cap_text, *texts])) + "</p>"
                table.polygon = PolygonBox.from_bbox([tx0, new_top, tx1, ty1])
                break

    @staticmethod
    def _absorb_table_spill(document, page):
        """
        Layout sometimes boxes only part of a table (e.g. its header) as the
        Table and labels the rest, overlapping it, as Caption/Text. Grow the
        table over such a block so all rows are recognised, and hide the block.
        """
        tables = [t for t in page.contained_blocks(document, (BlockTypes.Table,)) if not t.removed]
        if not tables:
            return
        others = page.contained_blocks(document, (BlockTypes.Caption, BlockTypes.Text))
        for table in tables:
            for b in others:
                if b.removed or b.ignore_for_output:
                    continue
                text = b.raw_text(document)
                if caption_kind(text) or is_source_line(text):
                    continue
                if table_overlap(table.polygon.bbox, b.polygon.bbox) < SPILL_OVERLAP:
                    continue
                table.polygon = table.polygon.merge([b.polygon])
                b.ignore_for_output = True

    def _merge_split_tables(self, document, page):
        """A table split into several text/heading blocks under its caption -> one Table."""
        blocks = [
            b for b in page.structure_blocks(document)
            if not b.removed and not b.ignore_for_output
            and b.block_type not in (BlockTypes.PageHeader,)
        ]
        if not blocks:
            return
        mergeable = {BlockTypes.Text, BlockTypes.SectionHeader, BlockTypes.Caption,
                     BlockTypes.ListGroup, BlockTypes.ListItem}
        items, lines_of = [], []
        for b in blocks:
            text = b.raw_text(document)
            lines = b.contained_blocks(document, (BlockTypes.Line,))
            boxes = [ln.polygon.bbox for ln in lines]
            multi, total = column_rows(boxes)
            x0, y0, x1, y1 = b.polygon.bbox
            items.append({
                "box": (x0, y0, x1, y1), "kind": caption_kind(text), "type": str(b.block_type),
                "source": is_source_line(text), "prose": total >= 2 and multi == 0, "width": x1 - x0,
            })
            lines_of.append(boxes)
        content_width = max(it["box"][2] for it in items) - min(it["box"][0] for it in items)
        for ci, it in enumerate(items):
            if it["kind"] != "table":
                continue
            found = table_region(items, ci, content_width)
            if not found:
                continue
            region, _ = found
            if len(region) < 2 or any(blocks[i].block_type not in mergeable for i in region):
                continue
            if not looks_like_split_table([bx for i in region for bx in lines_of[i]]):
                continue
            first = blocks[region[0]]
            table = self._relabel(page, first, BlockTypes.Table)
            others = [blocks[i] for i in region[1:]]
            table.polygon = table.polygon.merge([b.polygon for b in others])
            for b in others:
                table.structure = (table.structure or []) + list(b.structure or [])
                page.remove_structure_items([b.id])
                b.removed = True
            for i in region:
                items[i]["type"] = "Table"  # don't reuse these blocks for another caption

    def _absorb_labels(self, document, picture, blocks, kinds, candidates):
        """Merge small label blocks (legend, axis, stray ticks) touching the picture into it."""
        changed = True
        while changed:
            changed = False
            margin = self.table_rescue_label_margin
            x0, y0, x1, y1 = picture.polygon.bbox
            for b in blocks:
                if b is picture or b.removed or b.ignore_for_output or b.block_type not in candidates:
                    continue
                if kinds[blocks.index(b)]:
                    continue
                bx0, by0, bx1, by1 = b.polygon.bbox
                touches = bx0 < x1 + margin and bx1 > x0 - margin and by0 < y1 + margin and by1 > y0 - margin
                if touches and is_label_text(b.raw_text(document)):
                    picture.polygon = picture.polygon.merge([b.polygon])
                    b.ignore_for_output = True
                    changed = True

    def _nearest_caption(self, kinds, i):
        for d in range(1, self.table_rescue_caption_window + 1):
            for j in (i - d, i + d):
                if 0 <= j < len(kinds) and kinds[j]:
                    return kinds[j]
        return None

    @staticmethod
    def _relabel(page, block, block_type):
        new_cls = get_block_class(block_type)
        new_block = new_cls(
            polygon=deepcopy(block.polygon),
            page_id=block.page_id,
            structure=deepcopy(block.structure),
            text_extraction_method=block.text_extraction_method,
            source="heuristics",
            top_k=block.top_k,
            metadata=block.metadata,
        )
        page.replace_block(block, new_block)
        return new_block


def processor_list_with_rescue(default_processors) -> list[str]:
    """marker's processor list (as import paths) with the rescue inserted before TableProcessor."""
    paths = [f"{p.__module__}.{p.__name__}" for p in default_processors]
    idx = next((i for i, p in enumerate(paths) if p.endswith(".TableProcessor")), 0)
    return paths[:idx] + [PROCESSOR_PATH] + paths[idx:]
