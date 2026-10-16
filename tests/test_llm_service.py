"""
Tests for ResilientClaudeService with a fake Anthropic client.

Skipped automatically when marker-pdf / anthropic are not installed (e.g. in
the lightweight CI job); run locally inside the project's virtualenv.
"""
import tempfile
import unittest
from types import SimpleNamespace

try:
    import anthropic
    import httpx
    from PIL import Image
    from pydantic import BaseModel

    from modules import llm_service
    from modules.llm_resilience import FatalLLMError

    HAVE_DEPS = True
except ImportError:  # pragma: no cover - depends on environment
    HAVE_DEPS = False


def _http_error(cls, status, headers=None):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status, headers=headers or {}, request=request)
    return cls(f"HTTP {status}", response=response, body=None)


class FakeMessages:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.with_raw_response = self

    def create(self, **kwargs):
        self.calls += 1
        self.requests = getattr(self, "requests", []) + [kwargs]
        o = self.outcomes.pop(0)
        if isinstance(o, BaseException):
            raise o
        if isinstance(o, SimpleNamespace):  # a full message
            message = o
        elif isinstance(o, dict):  # tool call answer
            message = SimpleNamespace(
                content=[SimpleNamespace(type="tool_use", name="x", input=o)], stop_reason="tool_use"
            )
        else:
            message = SimpleNamespace(content=[SimpleNamespace(type="text", text=o)], stop_reason="end_turn")
        return SimpleNamespace(headers={}, parse=lambda: message)


@unittest.skipUnless(HAVE_DEPS, "marker-pdf/anthropic not installed")
class ResilientClaudeServiceTests(unittest.TestCase):
    def setUp(self):
        class Answer(BaseModel):
            corrected_html: str

        self.Answer = Answer
        self.tmp = tempfile.TemporaryDirectory()
        llm_service.reset_state()

    def tearDown(self):
        self.tmp.cleanup()

    def make_service(self, outcomes, cache=True):
        svc = llm_service.ResilientClaudeService(
            {
                "claude_api_key": "sk-ant-test",
                "claude_model_name": "claude-test",
                "llm_cache_dir": self.tmp.name if cache else "",
                "retry_wait_time": 0,
            }
        )
        fake = FakeMessages(outcomes)
        svc._client = SimpleNamespace(messages=fake)
        return svc, fake

    def call(self, svc, prompt="Fix this table", image=None):
        return svc(prompt, image, None, self.Answer)

    def test_retries_rate_limit_then_caches(self):
        svc, fake = self.make_service([
            _http_error(anthropic.RateLimitError, 429, {"retry-after": "0"}),
            '{"corrected_html": "<table></table>"}',
        ])
        image = Image.new("RGB", (8, 8), "white")
        self.assertEqual(self.call(svc, image=image), {"corrected_html": "<table></table>"})
        stats = llm_service.get_stats()
        self.assertEqual((stats.rate_limited, stats.retries, stats.failures), (1, 1, 0))

        # Same request again (same process) -> served from the checkpoint.
        self.assertEqual(self.call(svc, image=image)["corrected_html"], "<table></table>")
        self.assertEqual(fake.calls, 2)

        # A re-run (fresh state + new service) also resumes from the checkpoint.
        llm_service.reset_state()
        svc2, fake2 = self.make_service([])
        self.assertEqual(self.call(svc2, image=image)["corrected_html"], "<table></table>")
        self.assertEqual(fake2.calls, 0)
        self.assertEqual(llm_service.get_stats().cache_hits, 1)

        # A different image is a different request.
        other = Image.new("RGB", (8, 8), "black")
        svc3, fake3 = self.make_service(['{"corrected_html": "<table>x</table>"}'])
        self.assertEqual(self.call(svc3, image=other)["corrected_html"], "<table>x</table>")
        self.assertEqual(fake3.calls, 1)

    def test_overloaded_529_is_retried(self):
        svc, _ = self.make_service([
            _http_error(anthropic.InternalServerError, 529),
            '{"corrected_html": "ok"}',
        ])
        self.assertEqual(self.call(svc), {"corrected_html": "ok"})

    def test_exhausted_retries_return_empty_and_are_not_cached(self):
        svc, fake = self.make_service([_http_error(anthropic.RateLimitError, 429, {"retry-after": "0"})] * 9)
        self.assertEqual(self.call(svc), {})
        self.assertEqual(llm_service.get_stats().failures, 1)
        self.assertEqual(fake.calls, 9)  # 1 + 8 retries
        # Nothing was checkpointed, so a re-run will try again.
        svc2, fake2 = self.make_service(['{"corrected_html": "ok"}'])
        self.assertEqual(self.call(svc2), {"corrected_html": "ok"})
        self.assertEqual(fake2.calls, 1)

    def test_invalid_json_counts_as_unsuccessful(self):
        svc, fake = self.make_service(["not json", "still not json"])
        self.assertEqual(self.call(svc), {})
        stats = llm_service.get_stats()
        self.assertEqual((stats.invalid_responses, stats.unsuccessful), (1, 1))
        self.assertEqual(fake.calls, 2)  # asked once more before giving up

    def test_invalid_answer_is_asked_again(self):
        svc, fake = self.make_service(["sorry", {"corrected_html": "<table></table>"}])
        self.assertEqual(self.call(svc), {"corrected_html": "<table></table>"})
        self.assertEqual(llm_service.get_stats().unsuccessful, 0)

    def test_request_forces_tool_call(self):
        svc, fake = self.make_service([{"corrected_html": "ok"}])
        self.assertEqual(self.call(svc), {"corrected_html": "ok"})
        req = fake.requests[0]
        self.assertEqual(req["tool_choice"], {"type": "tool", "name": "submit_Answer"})
        self.assertEqual(req["tools"][0]["input_schema"]["required"], ["corrected_html"])

    def test_tools_can_be_disabled(self):
        svc, fake = self.make_service(['{"corrected_html": "ok"}'])
        svc.claude_use_tools = False
        self.assertEqual(self.call(svc), {"corrected_html": "ok"})
        self.assertNotIn("tools", fake.requests[0])

    def test_free_text_answers_are_repaired(self):
        html = '<table><tr><td colspan="2">a\nb</td></tr></table>'
        bad = 'Here you go:\n{"corrected_html": "' + html + '"}'
        svc, fake = self.make_service([bad, bad])
        # Unescaped quotes are invalid JSON; raw newline alone would be accepted.
        self.assertEqual(self.call(svc), {})
        self.assertEqual((fake.calls, llm_service.get_stats().failures), (2, 0))
        svc, _ = self.make_service(['Here you go:\n{"corrected_html": "<b>a\nb</b>"}'])
        self.assertEqual(self.call(svc, prompt="other"), {"corrected_html": "<b>a\nb</b>"})
        self.assertEqual(llm_service.get_stats().repaired, 1)

    def test_truncated_answer_retried_with_more_tokens(self):
        cut = SimpleNamespace(content=[SimpleNamespace(type="text", text='{"corrected_html": "<ta')],
                              stop_reason="max_tokens")
        svc, fake = self.make_service([cut, {"corrected_html": "ok"}])
        self.assertEqual(self.call(svc), {"corrected_html": "ok"})
        self.assertEqual(fake.requests[1]["max_tokens"], 2 * fake.requests[0]["max_tokens"])

    def test_auth_error_stops_all_further_calls(self):
        svc, fake = self.make_service([_http_error(anthropic.AuthenticationError, 401)])
        with self.assertRaises(FatalLLMError):
            self.call(svc)
        with self.assertRaises(FatalLLMError):
            self.call(svc, prompt="another block")
        self.assertEqual(fake.calls, 1)
        self.assertIsNotNone(llm_service.get_fatal_error())

    def test_cache_disabled(self):
        svc, fake = self.make_service(['{"corrected_html": "a"}', '{"corrected_html": "a"}'], cache=False)
        self.call(svc)
        self.call(svc)
        self.assertEqual(fake.calls, 2)


@unittest.skipUnless(HAVE_DEPS, "marker-pdf/anthropic not installed")
class MarkerIntegrationTests(unittest.TestCase):
    def test_marker_loads_service_with_config(self):
        import os
        from unittest import mock

        from marker.converters.pdf import PdfConverter

        from modules import pdf2md

        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            cfg, path = pdf2md.build_llm_config(True, "claude-test", cache_dir=d, concurrency=1, requests_per_minute=10)
            artifacts = {k: object() for k in
                         ["layout_model", "recognition_model", "table_rec_model", "detection_model", "ocr_error_model"]}
            conv = PdfConverter(artifact_dict=artifacts, config=cfg, llm_service=path)
        svc = conv.llm_service
        self.assertIsInstance(svc, llm_service.ResilientClaudeService)
        self.assertEqual((svc.claude_model_name, svc.max_retries, svc.llm_cache_dir), ("claude-test", 8, d))
        self.assertEqual(svc.timeout, 180)
        concurrencies = {p.max_concurrency for p in conv.processor_list if hasattr(p, "max_concurrency")}
        self.assertEqual(concurrencies, {1})


if __name__ == "__main__":
    unittest.main()
