"""Unit tests for heading normalization (stdlib only)."""
import unittest

from modules.postprocessing import postprocess_text
from modules.postprocessing.headings import is_caption, normalize_headings, prepare_outline

OUTLINE = [
    (0, "MI LIBRO: TÍTULO COMPLETO (...)", 0),
    (1, "ÍNDICE", 3),
    (1, "INTRODUCCIÓN", 5),
    (1, "I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS (...)", 10),
    (2, "TEORÍA DEL CICLO Y LAS CRISIS PERIÓDICAS (...)", 12),
    (2, "UBICACIÓN HISTÓRICA", 20),
    (1, "II. LA SEGUNDA PARTE", 30),
    (2, "CRISIS SOCIAL: ECONOMÍA DE LA INSEGURIDAD (...)", 31),
    (1, "BIBLIOGRAFÍA", 50),
]

DOC = """# Mi libro

### ÍNDICE

### INTRODUCCIÓN

### I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS LARGAS IRREGULARES

### Ubicación histórica

Texto del capítulo uno.

#### TEORIA DEL CICLO Y LAS CRISIS PERIODICAS DEL CAPITALISMO

##### Los pioneros

Texto.

# GRÁFICA I.1. Ondas largas

#### Ubicacion historica

### II. LA SEGUNDA

### PARTE

> CRISIS SOCIAL: ECONOMÍA DE LA INSEGURIDAD Y LA DESIGUALDAD

Texto.

### Bibliografía

- Autor, A. (2000). Obra.
"""


def levels(md):
    return [(len(line.split(" ")[0]), line.split(" ", 1)[1]) for line in md.split("\n") if line.startswith("#")]


class OutlineTests(unittest.TestCase):
    def test_prepare_outline_strips_root_and_truncation(self):
        entries = prepare_outline(OUTLINE)
        self.assertEqual(entries[0].title, "ÍNDICE")
        self.assertEqual(entries[0].level, 1)
        self.assertTrue(entries[2].truncated)
        self.assertEqual(entries[2].title, "I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS")
        self.assertEqual(entries[3].level, 2)

    def test_levels_follow_outline(self):
        out, rep = normalize_headings(DOC, OUTLINE)
        self.assertEqual(rep.mode, "outline")
        lv = dict((t, n) for n, t in levels(out))
        self.assertEqual(lv["INTRODUCCIÓN"], 1)
        self.assertEqual(lv["I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS LARGAS IRREGULARES"], 1)
        # Truncated + accent-less match.
        self.assertEqual(lv["TEORIA DEL CICLO Y LAS CRISIS PERIODICAS DEL CAPITALISMO"], 2)
        # Unmatched subsection goes one level below its section.
        self.assertEqual(lv["Los pioneros"], 3)
        self.assertEqual(lv["Bibliografía"], 1)

    def test_last_duplicate_wins_and_earlier_one_is_kept_as_subsection(self):
        out, _ = normalize_headings(DOC, OUTLINE)
        hs = levels(out)
        # "Ubicación histórica" appears twice; the later one is aligned (H2)...
        self.assertIn((2, "Ubicacion historica"), hs)
        # ...and the earlier, single duplicate stays a (lower) heading.
        self.assertIn((2, "Ubicación histórica"), hs)

    def test_split_heading_is_merged_and_blockquote_promoted(self):
        out, rep = normalize_headings(DOC, OUTLINE)
        self.assertIn("# II. LA SEGUNDA PARTE", out.split("\n"))
        self.assertNotIn("### PARTE", out)
        self.assertEqual(rep.merged, 1)
        self.assertIn("## CRISIS SOCIAL: ECONOMÍA DE LA INSEGURIDAD Y LA DESIGUALDAD", out.split("\n"))
        self.assertEqual(rep.promoted, 1)

    def test_captions_become_bold(self):
        out, rep = normalize_headings(DOC, OUTLINE)
        self.assertIn("**GRÁFICA I.1. Ondas largas**", out)
        self.assertEqual(rep.captions_demoted, 1)

    def test_printed_contents_cluster_is_demoted(self):
        md = (
            "### ÍNDICE\n\n### INTRODUCCIÓN\n\n### I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS\n\n"
            "### II. LA SEGUNDA PARTE\n\n### BIBLIOGRAFÍA\n\nTexto.\n\n### INTRODUCCIÓN\n\nTexto.\n\n"
            "### I. MARCO TEÓRICO: CICLO Y CRISIS, ONDAS\n\nTexto.\n\n### II. LA SEGUNDA PARTE\n\nTexto.\n\n"
            "### BIBLIOGRAFÍA\n\n- Autor (2000).\n"
        )
        out, rep = normalize_headings(md, OUTLINE)
        self.assertEqual(rep.duplicates_demoted, 4)
        self.assertEqual([t for n, t in levels(out) if n == 1][0], "ÍNDICE")
        self.assertEqual(sum(1 for n, t in levels(out) if t == "INTRODUCCIÓN"), 1)

    def test_unrelated_outline_falls_back_to_heuristics(self):
        out, rep = normalize_headings(DOC, [(0, "Page 1", 0), (0, "Page 2", 1), (0, "Page 3", 2)])
        self.assertEqual(rep.mode, "heuristic")

    def test_idempotent(self):
        once, _ = normalize_headings(DOC, OUTLINE)
        twice, rep = normalize_headings(once, OUTLINE)
        self.assertEqual(once, twice)
        self.assertEqual(rep.changed, 0)


class HeuristicTests(unittest.TestCase):
    MD = (
        "# Título del libro\n\n### SECCIÓN DE OBRAS DE ECONOMÍA\n\n### INTRODUCCIÓN\n\nTexto.\n\n"
        "### CAPÍTULO 1. El comienzo\n\n### Una sección\n\n#### Un apartado\n\n"
        "# Figura 2: un gráfico\n\n### Chapter Two\n\n### 3. Otro capítulo\n\n### Bibliography\n"
    )

    def test_chapters_become_h1(self):
        out, rep = normalize_headings(self.MD)
        self.assertEqual(rep.mode, "heuristic")
        lv = dict((t, n) for n, t in levels(out))
        for t in ("INTRODUCCIÓN", "CAPÍTULO 1. El comienzo", "Chapter Two", "3. Otro capítulo", "Bibliography"):
            self.assertEqual(lv[t], 1, t)
        self.assertEqual(lv["SECCIÓN DE OBRAS DE ECONOMÍA"], 2)
        self.assertEqual(lv["Título del libro"], 2)
        self.assertEqual(lv["Una sección"], 2)
        self.assertEqual(lv["Un apartado"], 3)
        self.assertIn("**Figura 2: un gráfico**", out)

    def test_idempotent(self):
        once, _ = normalize_headings(self.MD)
        twice, rep = normalize_headings(once)
        self.assertEqual(once, twice)
        self.assertEqual(rep.changed, 0)

    def test_without_chapters_top_level_becomes_h1(self):
        out, _ = normalize_headings("### Uno\n\n#### Dos\n\n### Tres\n")
        self.assertEqual(levels(out), [(1, "Uno"), (2, "Dos"), (1, "Tres")])

    def test_fenced_code_untouched(self):
        md = "### INTRODUCCIÓN\n\n```\n# not a heading\n```\n\n### CONCLUSIONES\n"
        out, _ = normalize_headings(md)
        self.assertIn("```\n# not a heading\n```", out)


class CaptionTests(unittest.TestCase):
    def test_caption_detection(self):
        for text in ("GRÁFICA IV.7. Valores", "CUADRO II.6. Crisis", "Table 3: Results", "Figure 1.2 A", "Fig. 4 B"):
            self.assertTrue(is_caption(text), text)
        for text in ("Gráficas y cuadros", "Tablas de multiplicar del siglo XX", "Figuras retóricas"):
            self.assertFalse(is_caption(text), text)


class PipelineTests(unittest.TestCase):
    def test_headings_run_before_footnotes(self):
        md = "### CAPÍTULO 1\n\nTexto.1 Fin.\n\n<sup>1</sup> Nota suficientemente larga aquí.\n\n### CAPÍTULO 2\n\nMás.\n"
        out, report = postprocess_text(md)
        self.assertIn("# CAPÍTULO 1", out.split("\n"))
        self.assertIn("[^c1-1]: Nota suficientemente larga aquí.", out)
        self.assertLess(out.index("[^c1-1]:"), out.index("# CAPÍTULO 2"))
        out2, _ = postprocess_text(md, fix_headings=False)
        self.assertIn("### CAPÍTULO 1", out2)


if __name__ == "__main__":
    unittest.main()
