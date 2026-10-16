"""
Getting structured answers out of Claude reliably.

marker's prompts ask for JSON, but some of them also show an example answer in
a different layout ("comparison: ...  ```html ...```  analysis: ..."), and
JSON strings holding HTML often contain unescaped quotes or raw newlines. Two
complementary tools:

* tool_for_schema(): turn a pydantic schema into an Anthropic tool definition,
  so the request can force a tool call and the API returns already-parsed
  JSON (no escaping problems at all);
* lenient_parse(): best-effort recovery of a schema instance from free text
  (JSON embedded in prose/fences, raw control characters, or the
  "field: value" layout used in marker's examples).
"""
from __future__ import annotations

import copy
import json
import re
import typing

from pydantic import BaseModel, ValidationError

_FENCE_RE = re.compile(r"^\s*```[A-Za-z0-9_-]*\s*\n?(.*?)\n?\s*```\s*$", re.DOTALL)
_TOOL_NAME_RE = re.compile(r"[^A-Za-z0-9_-]")


# --------------------------------------------------------------------------- #
# Tool definitions
# --------------------------------------------------------------------------- #
def inline_schema_refs(schema: dict) -> dict:
    """Resolve local "$ref": "#/$defs/X" references (nested pydantic models)."""
    schema = copy.deepcopy(schema)
    defs = schema.pop("$defs", {}) or schema.pop("definitions", {})

    def resolve(node, depth=0):
        if depth > 20:  # recursive models: stop inlining
            return {"type": "object"}
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.split("/")[-1] in defs:
                target = resolve(defs[ref.split("/")[-1]], depth + 1)
                extra = {k: v for k, v in node.items() if k != "$ref"}
                return {**target, **resolve(extra, depth)}
            return {k: resolve(v, depth) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v, depth) for v in node]
        return node

    return resolve(schema)


def tool_name_for(schema: type[BaseModel]) -> str:
    return (_TOOL_NAME_RE.sub("_", f"submit_{schema.__name__}") or "submit_answer")[:64]


def tool_for_schema(schema: type[BaseModel]) -> dict:
    input_schema = inline_schema_refs(schema.model_json_schema())
    input_schema.setdefault("type", "object")
    input_schema.pop("title", None)
    return {
        "name": tool_name_for(schema),
        "description": "Submit your complete answer. Every field of the schema must be filled in.",
        "input_schema": input_schema,
    }


# --------------------------------------------------------------------------- #
# Validation helpers
# --------------------------------------------------------------------------- #
def validate_object(obj, schema: type[BaseModel]) -> dict | None:
    if not isinstance(obj, dict):
        return None
    try:
        return schema.model_validate(obj).model_dump()
    except ValidationError:
        return None


def _json_candidates(text: str):
    """Every JSON object embedded in text, outermost first."""
    decoder = json.JSONDecoder(strict=False)  # allow raw newlines/tabs inside strings
    i = text.find("{")
    while i != -1:
        try:
            obj, end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            i = text.find("{", i + 1)
            continue
        yield obj
        i = text.find("{", end)


def _flat_fields(schema: type[BaseModel]) -> dict[str, type] | None:
    """Field name -> type for schemas made only of str/int/float/bool fields."""
    out = {}
    for name, f in schema.model_fields.items():
        tp = f.annotation
        if typing.get_origin(tp) is typing.Union:
            args = [a for a in typing.get_args(tp) if a is not type(None)]
            tp = args[0] if len(args) == 1 else None
        if tp not in (str, int, float, bool):
            return None
        out[name] = tp
    return out


def _parse_labeled(text: str, schema: type[BaseModel]) -> dict | None:
    """Parse the 'field: value' layout shown in marker's prompt examples."""
    fields = _flat_fields(schema)
    if not fields:
        return None
    label = re.compile(
        r"^[ \t]*[*_]*(" + "|".join(map(re.escape, fields)) + r")[*_]*[ \t]*:[ \t]*",
        re.IGNORECASE | re.MULTILINE,
    )
    marks = list(label.finditer(text))
    if not marks:
        return None
    values: dict[str, str] = {}
    lower = {k.lower(): k for k in fields}
    for idx, m in enumerate(marks):
        name = lower[m.group(1).lower()]
        end = marks[idx + 1].start() if idx + 1 < len(marks) else len(text)
        value = text[m.end():end].strip()
        fence = _FENCE_RE.match(value)
        if fence:
            value = fence.group(1).strip()
        values.setdefault(name, value)
    # A fenced block right after a label-less "comparison" line is the html
    # in marker's examples ("comparison: ...\n```html\n...\n```").
    for name, value in list(values.items()):
        inner = re.search(r"```[A-Za-z]*\s*\n(.*?)\n\s*```", value, re.DOTALL)
        if inner:
            missing = [k for k, t in fields.items() if t is str and k not in values]
            if missing:
                values[missing[0]] = inner.group(1).strip()
                values[name] = value[: inner.start()].strip()
    for name, tp in fields.items():
        if name in values and tp in (int, float):
            num = re.search(r"-?\d+(?:\.\d+)?", values[name])
            values[name] = num.group(0) if num else values[name]
    return validate_object(values, schema)


def lenient_parse(text: str, schema: type[BaseModel]) -> dict | None:
    """Recover a schema instance from a free-text answer, or None."""
    if not text or not text.strip():
        return None
    stripped = text.strip()
    fence = _FENCE_RE.match(stripped)
    if fence:
        stripped = fence.group(1)
    for obj in _json_candidates(stripped):
        result = validate_object(obj, schema)
        if result is not None:
            return result
    return _parse_labeled(text, schema)
