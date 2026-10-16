"""Tests for structured-answer helpers (need pydantic, installed with marker-pdf)."""
import unittest
from typing import List

try:
    from pydantic import BaseModel

    from modules.llm_parsing import inline_schema_refs, lenient_parse, tool_for_schema

    HAVE_DEPS = True
except ImportError:  # pragma: no cover
    HAVE_DEPS = False

if HAVE_DEPS:

    class TableSchema(BaseModel):  # same shape as marker's
        comparison: str
        corrected_html: str
        analysis: str
        score: int

    class Block(BaseModel):
        block_id: str
        level: int

    class Nested(BaseModel):
        analysis: str
        blocks: List[Block]


@unittest.skipUnless(HAVE_DEPS, "pydantic not installed")
class ToolSchemaTests(unittest.TestCase):
    def test_nested_refs_are_inlined(self):
        tool = tool_for_schema(Nested)
        self.assertEqual(tool["name"], "submit_Nested")
        schema = tool["input_schema"]
        self.assertNotIn("$defs", schema)
        self.assertNotIn("$ref", str(schema))
        self.assertEqual(schema["properties"]["blocks"]["items"]["properties"]["level"]["type"], "integer")

    def test_inline_keeps_plain_schema(self):
        s = TableSchema.model_json_schema()
        self.assertEqual(inline_schema_refs(s)["properties"], s["properties"])


@unittest.skipUnless(HAVE_DEPS, "pydantic not installed")
class LenientParseTests(unittest.TestCase):
    def test_marker_example_layout(self):
        text = (
            "comparison: The image shows a table with 2 rows.\n"
            "```html\n<table><tr><td class=\"x\">1</td></tr></table>\n```\n"
            "analysis: Fixed one cell.\nscore: 4"
        )
        out = lenient_parse(text, TableSchema)
        self.assertEqual(out["corrected_html"], '<table><tr><td class="x">1</td></tr></table>')
        self.assertEqual(out["comparison"], "The image shows a table with 2 rows.")
        self.assertEqual(out["score"], 4)

    def test_labeled_fields_with_fence(self):
        text = (
            "**comparison**: ok\n**corrected_html**:\n```html\nNo corrections needed.\n```\n"
            "**analysis**: none\n**score**: 5/5"
        )
        out = lenient_parse(text, TableSchema)
        self.assertEqual(out["corrected_html"], "No corrections needed.")
        self.assertEqual(out["score"], 5)

    def test_json_in_prose_and_fences_with_raw_newlines(self):
        text = 'Sure!\n```json\n{"analysis": "a\nb", "blocks": [{"block_id": "/p/1", "level": 2}]}\n```'
        out = lenient_parse(text, Nested)
        self.assertEqual(out["blocks"], [{"block_id": "/p/1", "level": 2}])

    def test_unrecoverable(self):
        self.assertIsNone(lenient_parse("I cannot read this image.", TableSchema))
        self.assertIsNone(lenient_parse("", TableSchema))
        self.assertIsNone(lenient_parse('{"comparison": "x"}', TableSchema))  # missing fields


if __name__ == "__main__":
    unittest.main()
