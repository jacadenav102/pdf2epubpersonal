"""Tests for the borderless-table detection heuristics (stdlib only)."""
import unittest

from modules.table_rescue import (
    PROCESSOR_PATH,
    caption_kind,
    classify_block,
    column_rows,
    looks_like_figure,
    group_rows,
    is_caption_only,
    is_label_text,
    is_source_line,
    is_table_caption,
    looks_like_split_table,
    table_region,
    trimmed_table_top,
    caption_continuation,
    table_overlap,
    numeric_ratio,
    looks_like_table,
    processor_list_with_rescue,
)

# Line boxes from marker for "CUADRO I.1" (page 47 of the test book).
TABLE_LINES = [
    (68, 413, 122, 422), (169, 403, 216, 412), (167, 413, 215, 422),
    (263, 403, 314, 412), (263, 413, 311, 422),
    (93, 428, 296, 437), (93, 443, 295, 452), (93, 458, 295, 467), (93, 472, 296, 481),
]
# A justified paragraph (first line indented, short last line).
PROSE_LINES = [
    (65, 223, 338, 233), (47, 235, 335, 245), (47, 247, 338, 257),
    (47, 259, 338, 269), (47, 271, 338, 281), (47, 283, 130, 293),
]
# A real two-column grid without caption.
GRID_LINES = [
    (50, 100, 120, 110), (200, 100, 300, 110),
    (50, 115, 110, 125), (200, 115, 280, 125),
    (50, 130, 130, 140), (200, 130, 290, 140),
    (50, 145, 100, 155), (200, 145, 260, 155),
]


class CaptionTests(unittest.TestCase):
    def test_table_captions(self):
        for text in ("CUADRO I.1. Fases", "Cuadro 3", "TABLA 2.4 Datos", "Table 1: Results",
                     "Tableau IV", "Tabelle 2", "**CUADRO II.6.** Crisis"):
            self.assertTrue(is_table_caption(text), text)

    def test_not_table_captions(self):
        for text in ("Cuadros comparativos", "GRÁFICA I.1", "Figure 2", "La tabla siguiente muestra",
                     "Table of contents"):
            self.assertFalse(is_table_caption(text), text)


class GeometryTests(unittest.TestCase):
    def test_rows(self):
        rows = group_rows(TABLE_LINES)
        # 2 header rows (y 403 and 413) + 4 body rows.
        self.assertEqual(len(rows), 6)
        self.assertEqual(column_rows(TABLE_LINES), (2, 6))
        self.assertEqual(column_rows(PROSE_LINES), (0, 6))

    def test_table_with_caption(self):
        self.assertTrue(looks_like_table(TABLE_LINES, has_caption=True))

    def test_table_without_caption_needs_strong_columns(self):
        self.assertFalse(looks_like_table(TABLE_LINES, has_caption=False))
        self.assertTrue(looks_like_table(GRID_LINES, has_caption=False))

    def test_prose_is_never_a_table(self):
        self.assertFalse(looks_like_table(PROSE_LINES, has_caption=True))
        self.assertFalse(looks_like_table(PROSE_LINES, has_caption=False))

    def test_word_spacing_is_not_a_column(self):
        # Two fragments of one line separated by a normal word space.
        line = [(47, 100, 150, 110), (153, 100, 300, 110), (47, 112, 300, 122), (47, 124, 200, 134)]
        self.assertFalse(looks_like_table(line, has_caption=True))

    def test_too_few_lines(self):
        self.assertFalse(looks_like_table(TABLE_LINES[:2], has_caption=True))


# Text labels of a vector chart ("GRÁFICA I.1", page 41 of the test book).
CHART_LINES = [
    (317, 96, 322, 143), (196, 101, 235, 107), (126, 101, 154, 107), (46, 104, 52, 176),
    (171, 117, 190, 124), (58, 134, 87, 140), (317, 146, 322, 192), (57, 188, 70, 193),
    (274, 188, 312, 195), (56, 197, 94, 210), (48, 214, 69, 221), (114, 214, 121, 219),
    (139, 214, 147, 219), (190, 214, 198, 219),
]
CHART_BOX = (46, 83, 334, 221)


class FigureTests(unittest.TestCase):
    def test_chart_labels_next_to_figure_caption(self):
        self.assertTrue(looks_like_figure(CHART_LINES, CHART_BOX))
        self.assertEqual(classify_block(CHART_LINES, "figure", CHART_BOX), "figure")

    def test_chart_labels_are_not_a_table(self):
        self.assertFalse(looks_like_table(CHART_LINES, has_caption=False))
        self.assertIsNone(classify_block(CHART_LINES, None, CHART_BOX))

    def test_prose_next_to_figure_caption_kept(self):
        self.assertIsNone(classify_block(PROSE_LINES, "figure"))

    def test_table_next_to_table_caption(self):
        self.assertEqual(classify_block(TABLE_LINES, "table"), "table")
        self.assertIsNone(classify_block(TABLE_LINES, None))

    def test_axis_ticks_count_as_chart(self):
        # Y-axis values stacked vertically (GRÁFICA V.1): no columns, but numeric.
        boxes = [(34, 105 + 20 * k, 50, 112 + 20 * k) for k in range(6)] + [(55, 215, 346, 226)]
        texts = ["-1.5", "0.5", "2.5", "4.5", "6.5", "8.5", "2001 2003 2005 2007 2009 2011"]
        self.assertFalse(looks_like_figure(boxes, (34, 105, 346, 226)))
        self.assertTrue(looks_like_figure(boxes, (34, 105, 346, 226), texts))
        self.assertGreaterEqual(numeric_ratio(texts), 0.6)
        self.assertEqual(numeric_ratio(["2007-01", "2008-01", "20%", "Mundo"]), 0.75)

    def test_numbered_prose_is_not_numeric(self):
        texts = ["1) la introducción de un nuevo bien", "de un bien; 2) la introducción", "3) la apertura"]
        self.assertEqual(numeric_ratio(texts), 0.0)

    def test_label_text(self):
        self.assertTrue(is_label_text("-3.5"))
        self.assertTrue(is_label_text("Economías avanzadas Economías en desarrollo y emergente Mundo"))
        self.assertFalse(is_label_text("FUENTE: elaborado con datos del FMI (2020)."))
        self.assertFalse(is_label_text("GRÁFICA V.2. Otra gráfica"))
        self.assertFalse(is_label_text("Lo anterior puede verse en cuadro I.1:"))
        self.assertFalse(is_label_text(" ".join(["palabra"] * 30)))

    def test_caption_kinds(self):
        self.assertEqual(caption_kind("GRÁFICA I.1. Modelo"), "figure")
        self.assertEqual(caption_kind("Figure 3: Results"), "figure")
        self.assertEqual(caption_kind("CUADRO II.6. Crisis"), "table")
        self.assertIsNone(caption_kind("Fuente: tomado de Tylecote (1992: 20)."))
        self.assertIsNone(caption_kind("Las gráficas muestran"))


def item(box, kind=None, type_="Text", source=False, prose=False):
    return {"box": box, "kind": kind, "type": type_, "source": source, "prose": prose,
            "width": box[2] - box[0]}


class SplitTableTests(unittest.TestCase):
    # CUADRO III.6 of the test book: row labels and cell texts in separate blocks.
    LABELS = [(47, 180, 112, 190), (47, 191, 112, 201), (45, 359, 112, 371), (45, 372, 112, 383)]
    CELLS = [(125, 178, 330, 188), (125, 189, 330, 199), (125, 200, 330, 210),
             (126, 345, 319, 356), (126, 360, 319, 370)]

    def test_split_table_geometry(self):
        self.assertTrue(looks_like_split_table(self.LABELS + self.CELLS))
        self.assertFalse(looks_like_split_table(PROSE_LINES))
        self.assertFalse(looks_like_split_table(self.CELLS))  # one column only

    def test_region_ends_at_source_line(self):
        items = [
            item((70, 70, 310, 81), kind="table", type_="Caption"),
            item((125, 88, 327, 182)),
            item((47, 180, 112, 201), type_="SectionHeader"),
            item((126, 178, 335, 225)),
            item((43, 531, 246, 540), source=True),
            item((46, 550, 338, 600), prose=True),
        ]
        region, closed = table_region(items, 0, content_width=295)
        self.assertEqual((sorted(region), closed), ([1, 2, 3], True))
        self.assertEqual(region[0], 1)  # top-most block first (it becomes the Table)

    def test_region_with_detected_table_is_skipped(self):
        items = [item((70, 70, 310, 81), kind="table"), item((49, 111, 340, 495), type_="Table"),
                 item((51, 502, 224, 510), source=True)]
        self.assertIsNone(table_region(items, 0, content_width=295))

    def test_region_without_source_stops_at_paragraph(self):
        items = [item((70, 70, 310, 81), kind="table"), item((60, 90, 200, 120)),
                 item((210, 90, 330, 120)), item((46, 130, 338, 200), prose=True), item((46, 210, 338, 260))]
        region, closed = table_region(items, 0, content_width=292)
        self.assertEqual((region, closed), ([1, 2], False))

    def test_region_stops_at_next_caption(self):
        items = [item((70, 70, 310, 81), kind="table"), item((60, 90, 200, 120)),
                 item((70, 130, 310, 141), kind="table"), item((60, 150, 200, 180))]
        self.assertEqual(table_region(items, 0, content_width=292)[0], [1])

    def test_table_box_trimmed_below_its_caption(self):
        # CUADRO III.2: table box starts above the caption line.
        self.assertEqual(trimmed_table_top((40, 60, 340, 300), (70, 62, 310, 72)), 72.5)
        # Caption below the table, or beside it: untouched.
        self.assertIsNone(trimmed_table_top((40, 60, 340, 300), (70, 305, 310, 315)))
        self.assertIsNone(trimmed_table_top((40, 60, 340, 300), (70, 250, 310, 260)))
        # A "table" that is only the caption is not trimmed to nothing.
        self.assertIsNone(trimmed_table_top((40, 60, 340, 80), (70, 62, 310, 72)))

    def test_source_and_caption_only(self):
        for text in ("FUENTE: elaborado con base en Modelski (1987).", "Fuentes: INEGI", "Source: IMF",
                     "Nota: a/ los datos", "Notes: values in %"):
            self.assertTrue(is_source_line(text), text)
        for text in ("Fuerte crecimiento", "Notable aumento", "La fuente principal"):
            self.assertFalse(is_source_line(text), text)
        self.assertTrue(is_caption_only(2))
        self.assertFalse(is_caption_only(0))
        self.assertFalse(is_caption_only(8))


class CaptionContinuationTests(unittest.TestCase):
    # CUADRO III.2: caption line 1 above the table box, line 2 inside its top.
    CAPTION = (58, 71, 324, 81)
    RUNS = [
        ((87, 82, 295, 91), "en los Estados Unidos, 1983-2014 (1979=100)"),
        ((116, 101, 151, 108), "Percentil "), ((168, 101, 203, 108), "Percentil "),
        ((223, 101, 258, 108), "Percentil "),
        ((66, 113, 104, 122), "promedio"), ((150, 113, 170, 122), "−3.7"),
        ((66, 125, 90, 134), "1983"), ((150, 125, 170, 134), "−1.1"),
    ]

    def test_second_caption_line_moves_out_of_table(self):
        texts, top = caption_continuation(self.CAPTION, self.RUNS)
        self.assertEqual(texts, ["en los Estados Unidos, 1983-2014 (1979=100)"])
        self.assertGreater(top, 91)
        self.assertLess(top, 101)

    def test_header_row_with_columns_is_not_caption(self):
        self.assertIsNone(caption_continuation(self.CAPTION, self.RUNS[1:]))

    def test_far_line_is_not_caption(self):
        far = [((87, 100, 295, 109), "Un título de columna")] + self.RUNS[1:]
        self.assertIsNone(caption_continuation(self.CAPTION, far))

    def test_numeric_line_is_not_caption(self):
        nums = [((87, 82, 295, 91), "1983 2000 2014")] + self.RUNS[1:]
        self.assertIsNone(caption_continuation(self.CAPTION, nums))

    def test_tiny_table_left_alone(self):
        self.assertIsNone(caption_continuation(self.CAPTION, self.RUNS[:1]))


class SpillTests(unittest.TestCase):
    def test_overlap_is_relative_to_smaller_box(self):
        table, spill = (53, 91, 354, 141), (29, 93, 354, 197)
        self.assertGreater(table_overlap(table, spill), 0.9)
        self.assertEqual(table_overlap(table, (33, 205, 280, 213)), 0.0)

    def test_degenerate_box(self):
        self.assertEqual(table_overlap((0, 0, 0, 0), (0, 0, 10, 10)), 0.0)


class ProcessorListTests(unittest.TestCase):
    def test_inserted_before_table_processor(self):
        class A: pass  # noqa: E701
        class TableProcessor: pass  # noqa: E701
        class B: pass  # noqa: E701
        for cls in (A, TableProcessor, B):
            cls.__module__ = "marker.processors.x"
        paths = processor_list_with_rescue([A, TableProcessor, B])
        self.assertEqual(paths.index(PROCESSOR_PATH) + 1, paths.index("marker.processors.x.TableProcessor"))
        self.assertEqual(len(paths), 4)

    def test_real_marker_list(self):
        try:
            from marker.converters.pdf import PdfConverter
            from marker.util import strings_to_classes
        except ImportError:
            self.skipTest("marker not installed")
        paths = processor_list_with_rescue(PdfConverter.default_processors)
        classes = strings_to_classes(paths)
        names = [c.__name__ for c in classes]
        self.assertEqual(names.index("TableRescueProcessor") + 1, names.index("TableProcessor"))
        self.assertEqual(len(classes), len(PdfConverter.default_processors) + 1)


if __name__ == "__main__":
    unittest.main()
