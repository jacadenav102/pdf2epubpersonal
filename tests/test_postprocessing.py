"""Unit tests for the markdown post-processing pipeline (stdlib only)."""
import unittest

from modules.postprocessing import postprocess_text
from modules.postprocessing.citations import link_citations
from modules.postprocessing.cleanup import clean_markdown
from modules.postprocessing.footnotes import link_footnotes


class CleanupTests(unittest.TestCase):
    def test_spaced_letter_sup_in_heading(self):
        self.assertEqual(clean_markdown("## CICLO <sup>Y</sup> CRISIS"), "## CICLO Y CRISIS")

    def test_real_superscripts_untouched(self):
        for text in ("1<sup>a</sup> edición", "x<sup>n</sup>", "nota <sup>3</sup> aquí"):
            self.assertEqual(clean_markdown(text), text)

    def test_escaped_sup(self):
        self.assertEqual(clean_markdown("<sup>&</sup>lt;sup>7</sup> Nota"), "<sup>7</sup> Nota")

    def test_ligatures(self):
        self.assertEqual(clean_markdown("fue identifi cado por las fi rmas"), "fue identificado por las firmas")
        self.assertEqual(clean_markdown("staff member, off the record"), "staff member, off the record")
        self.assertEqual(clean_markdown("identifi cado", ligatures=False), "identifi cado")


class FootnoteTests(unittest.TestCase):
    def test_punctuation_glued_reference_and_sup_definition(self):
        md = "# Capítulo\n\nUn acuerdo entre ellos.3 De una parte.\n\n<sup>3</sup> Entre estos autores figuran varios.\n"
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 1)
        self.assertIn("entre ellos.[^c1-3] De una parte.", out)
        self.assertIn("[^c1-3]: Entre estos autores figuran varios.", out)
        self.assertNotIn("<sup>3</sup>", out)

    def test_plain_definition_and_lowercase_glued_reference(self):
        md = "# Cap\n\nLos ciclos hegemónicos2 son amplios.\n\n2 Modelski descarta el concepto de hegemonía.\n"
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 1)
        self.assertIn("hegemónicos[^c1-2] son", out)

    def test_figure_numbers_are_not_references(self):
        md = "# Cap\n\nEn la gráfica I.1 se expone el modelo.\n\n<sup>1</sup> Nota sin referencia en el texto.\n"
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 0)
        self.assertEqual(rep.unresolved, [(5, 1)])
        self.assertEqual(out, md)  # unresolved notes are left untouched

    def test_numbering_per_chapter_gives_unique_labels(self):
        md = (
            "# Uno\n\nTexto.1 Más.\n\n<sup>1</sup> Nota del capítulo uno.\n\n"
            "# Dos\n\nOtro texto.1 Más.\n\n<sup>1</sup> Nota del capítulo dos.\n"
        )
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 2)
        self.assertIn("[^c1-1]: Nota del capítulo uno.", out)
        self.assertIn("[^c2-1]: Nota del capítulo dos.", out)
        # Notes stay inside their own chapter.
        self.assertLess(out.index("[^c1-1]:"), out.index("# Dos"))

    def test_paragraph_split_by_note_is_rejoined(self):
        md = "# Cap\n\nEl texto sigue.4 y continúa en la\n\n<sup>4</sup> Una nota al pie de página.\n\nsiguiente página.\n"
        out, _ = link_footnotes(md)
        self.assertIn("continúa en la siguiente página.", out)

    def test_detached_and_heading_references(self):
        md = (
            "# MARCO TEÓRICO DEL DESARROLLO CAPITALISTA1\n\nTexto.\n\n<sup>1</sup> Versión revisada del artículo.\n\n"
            "Las economías emergentes; 2 previamente, gran parte.\n\n<sup>2</sup> En 1980 los mercados emergentes.\n"
        )
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 2)
        self.assertIn("CAPITALISTA[^c1-1]", out)
        self.assertIn("emergentes;[^c1-2] previamente", out)

    def test_acronyms_are_not_references(self):
        md = "# Cap\n\nLa cumbre del G7 y el CO2 importan.\n\n<sup>7</sup> Nota sin llamada visible aquí.\n"
        _, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 0)

    def test_scopes_follow_numbering_not_heading_levels(self):
        # marker often emits chapters as "###" plus a stray "#" figure title.
        md = (
            "### UNO\n\nTexto.1 Sigue.2 Más.\n\n# GRÁFICA I.1\n\nOtra parte.3 Fin.\n\n"
            "<sup>1</sup> Primera nota del capítulo uno.\n\n<sup>2</sup> Segunda nota del capítulo uno.\n\n"
            "<sup>3</sup> Tercera nota del capítulo uno.\n\n"
            "### DOS\n\nTexto nuevo.1 Fin.\n\n<sup>1</sup> Primera nota del capítulo dos.\n"
        )
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 4)
        for label in ("c1-1", "c1-2", "c1-3", "c2-1"):
            self.assertIn(f"[^{label}]:", out)
            self.assertEqual(out.count(f"[^{label}]"), 2)

    def test_last_chapter_notes_stay_before_bibliography(self):
        md = (
            "### UNO\n\nTexto.1 Fin.\n\n<sup>1</sup> Nota del capítulo uno larga.\n\n"
            "### DOS\n\nTexto.1 Fin.\n\n<sup>1</sup> Nota del capítulo dos larga.\n" + BIB
        )
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 2)
        self.assertLess(out.index("[^c2-1]:"), out.index("# BIBLIOGRAFÍA"))
        full, _ = postprocess_text(md)
        self.assertIn("[^c2-1]: Nota del capítulo dos larga.", full)
        self.assertNotIn('<span id="ref-', full.split("[^c2-1]:", 1)[1].split("\n", 1)[0])

    def test_new_scope_reference_found_after_previous_notes(self):
        # The "1" in chapter one's notes must not be taken as chapter two's call.
        md = (
            "# Uno\n\nTexto.1 Fin.\n\n<sup>1</sup> Nota uno, véase el año 1 de la serie.\n\n"
            "Cuerpo del dos.1 Fin.\n\n<sup>1</sup> Nota del segundo capítulo.\n"
        )
        out, rep = link_footnotes(md)
        self.assertEqual(rep.linked, 2)
        self.assertIn("Cuerpo del dos.[^c2-1] Fin.", out)

    def test_idempotent(self):
        md = "# Cap\n\nUn acuerdo.3 Fin.\n\n<sup>3</sup> Nota al pie suficientemente larga.\n"
        once, _ = link_footnotes(md)
        twice, rep = link_footnotes(once)
        self.assertEqual(once, twice)
        self.assertEqual(rep.linked, 0)


BIB = """
# BIBLIOGRAFÍA

- Breznitz, D., y M. Murphree (2011). Run of The Red Queen. New Haven: Yale.
- Banco Mundial (2020). Indicadores del Desarrollo. Washington.
- ——— (2019). Informe sobre el Desarrollo Mundial 2019. Washington.
- Comisión Económica para América Latina y el Caribe [CEPAL] (2018). Datos.
- Glasner, D. (ed.) (1997). Business Cycles and Depressions. Nueva York.
- Schumpeter, J. A. ([1939] 2002). Ciclos económicos. Zaragoza.
- Van Gelderen (1996). Springtide. Londres.
"""


class CitationTests(unittest.TestCase):
    def link(self, sentence):
        out, rep = link_citations(sentence + "\n" + BIB)
        return out.split("\n", 1)[0], rep

    def test_narrative_and_parenthetical(self):
        line, _ = self.link("Como dicen Breznitz y Murphree (2011) y el Banco Mundial (2019).")
        self.assertIn("Breznitz y Murphree ([2011](#ref-breznitz-2011))", line)
        self.assertIn("Banco Mundial ([2019](#ref-banco-mundial-2019))", line)

    def test_multiple_citations_in_one_group(self):
        line, _ = self.link("Véase (Banco Mundial, 2020; CEPAL, 2018).")
        self.assertIn("Banco Mundial, [2020](#ref-banco-mundial-2020)", line)
        self.assertIn("CEPAL, [2018](#ref-comision-economica-para-america-latina-y-el-caribe-2018)", line)

    def test_editor_original_year_and_particles(self):
        line, _ = self.link("Glasner (1997), Schumpeter (2002) y Gelderen (1996).")
        self.assertIn("[1997](#ref-glasner-1997)", line)
        self.assertIn("[2002](#ref-schumpeter-2002)", line)
        self.assertIn("[1996](#ref-van-gelderen-1996)", line)

    def test_misspelled_first_author_uses_unique_coauthor(self):
        line, _ = self.link("Según Breznittz y Murphree (2011).")
        self.assertIn("[2011](#ref-breznitz-2011)", line)

    def test_non_citations_untouched(self):
        for sentence in ("Facebook (2004) creció.", "El periodo (1983-2008) fue largo.", "En 2020 hubo crisis."):
            line, _ = self.link(sentence)
            self.assertEqual(line, sentence)

    def test_entries_anchored_and_idempotent(self):
        once, rep = link_citations("Breznitz (2011).\n" + BIB)
        self.assertEqual(rep.entries, 7)
        self.assertIn('- <span id="ref-breznitz-2011"></span>Breznitz', once)
        twice, rep2 = link_citations(once)
        self.assertEqual(once, twice)
        self.assertEqual(rep2.linked, 0)

    def test_footnote_definitions_in_bibliography_ignored(self):
        out, rep = link_citations("Breznitz (2011).\n" + BIB + "\n[^c9-1]: Smith, J. (2001). Nota.\n")
        self.assertEqual(rep.entries, 7)
        self.assertIn("[^c9-1]: Smith, J. (2001). Nota.", out)

    def test_no_bibliography(self):
        out, rep = link_citations("Breznitz (2011).")
        self.assertFalse(rep.section_found)
        self.assertEqual(out, "Breznitz (2011).")


class PipelineTests(unittest.TestCase):
    def test_full_pipeline(self):
        md = "# CICLO <sup>Y</sup> CRISIS\n\nTexto de Breznitz (2011).1 Fin.\n\n<sup>1</sup> Nota que cita a Glasner (1997).\n" + BIB
        out, report = postprocess_text(md)
        self.assertIn("# CICLO Y CRISIS", out)
        self.assertIn("[^c1-1]: Nota que cita a Glasner ([1997](#ref-glasner-1997)).", out)
        self.assertEqual(len(report), 3)  # headings, footnotes, citations


if __name__ == "__main__":
    unittest.main()
