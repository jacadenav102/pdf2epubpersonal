"""Unit tests for modules/llm_resilience.py (stdlib only, no network, no real sleeping)."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from modules.llm_resilience import (
    FatalLLMError,
    LLMStats,
    RateLimiter,
    ResponseCache,
    backoff_delay,
    cache_key,
    call_with_retries,
    classify_error,
    parse_retry_after,
)


class FakeClock:
    def __init__(self, start=1_000_000.0):
        self.now = start
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class FakeResponse:
    def __init__(self, headers):
        self.headers = headers


class FakeAPIError(Exception):
    def __init__(self, status_code, headers=None):
        super().__init__(f"HTTP {status_code}")
        self.status_code = status_code
        self.response = FakeResponse(headers or {})


class APITimeoutError(Exception):
    """Same class name as the Anthropic SDK's timeout error."""


def limiter(clock, **kw):
    return RateLimiter(clock=clock.time, sleep=clock.sleep, **kw)


class RateLimiterTests(unittest.TestCase):
    def test_rpm_spacing(self):
        c = FakeClock()
        rl = limiter(c, rpm=30)  # one request every 2 s
        for _ in range(3):
            rl.acquire()
        self.assertAlmostEqual(sum(c.sleeps), 4.0)

    def test_unlimited_by_default(self):
        c = FakeClock()
        rl = limiter(c)
        for _ in range(10):
            rl.acquire()
        self.assertEqual(c.sleeps, [])

    def test_cooldown_blocks_all_callers(self):
        c = FakeClock()
        rl = limiter(c)
        rl.cooldown(12)
        self.assertAlmostEqual(rl.acquire(), 12)

    def test_cooldown_is_capped(self):
        c = FakeClock()
        rl = limiter(c, max_pause=30)
        rl.cooldown(10_000)
        self.assertAlmostEqual(rl.acquire(), 30)

    def test_proactive_pause_on_low_quota(self):
        c = FakeClock()
        rl = limiter(c)
        reset = datetime.fromtimestamp(c.now, tz=timezone.utc) + timedelta(seconds=20)
        headers = {
            "anthropic-ratelimit-output-tokens-limit": "8000",
            "anthropic-ratelimit-output-tokens-remaining": "500",
            "anthropic-ratelimit-output-tokens-reset": reset.isoformat().replace("+00:00", "Z"),
        }
        self.assertAlmostEqual(rl.update_from_headers(headers), 20, places=3)
        self.assertAlmostEqual(rl.acquire(), 20, places=3)

    def test_no_pause_with_plenty_of_quota(self):
        c = FakeClock()
        rl = limiter(c)
        headers = {
            "anthropic-ratelimit-requests-limit": "50",
            "anthropic-ratelimit-requests-remaining": "40",
            "anthropic-ratelimit-requests-reset": "2099-01-01T00:00:00Z",
        }
        self.assertEqual(rl.update_from_headers(headers), 0.0)
        self.assertEqual(rl.update_from_headers(None), 0.0)


class HelperTests(unittest.TestCase):
    def test_parse_retry_after(self):
        self.assertEqual(parse_retry_after({"retry-after": "7"}), 7.0)
        self.assertEqual(parse_retry_after({"retry-after-ms": "1500"}), 1.5)
        self.assertIsNone(parse_retry_after({"retry-after": "soon"}))
        self.assertIsNone(parse_retry_after(None))

    def test_classify(self):
        self.assertEqual(classify_error(FakeAPIError(429)), "rate_limit")
        self.assertEqual(classify_error(FakeAPIError(529)), "retryable")
        self.assertEqual(classify_error(FakeAPIError(503)), "retryable")
        self.assertEqual(classify_error(FakeAPIError(401)), "fatal")
        self.assertEqual(classify_error(FakeAPIError(400)), "permanent")
        self.assertEqual(classify_error(APITimeoutError()), "retryable")
        self.assertEqual(classify_error(ValueError()), "permanent")

    def test_backoff_grows_and_is_capped(self):
        mid = lambda: 1.0  # noqa: E731 - no jitter reduction
        self.assertEqual(backoff_delay(1, 5, 120, mid), 5)
        self.assertEqual(backoff_delay(3, 5, 120, mid), 20)
        self.assertEqual(backoff_delay(10, 5, 120, mid), 120)
        self.assertEqual(backoff_delay(3, 5, 120, lambda: 0.0), 10)

    def test_cache_key_sensitivity(self):
        a = cache_key(model="m", prompt="p", images=["x"])
        self.assertEqual(a, cache_key(images=["x"], prompt="p", model="m"))
        self.assertNotEqual(a, cache_key(model="m2", prompt="p", images=["x"]))
        self.assertNotEqual(a, cache_key(model="m", prompt="p", images=["y"]))


class RetryTests(unittest.TestCase):
    def run_calls(self, outcomes, **kw):
        """outcomes: list of exceptions or results, consumed one per attempt."""
        c = FakeClock()
        rl = limiter(c)
        stats = LLMStats()
        it = iter(outcomes)

        def send():
            o = next(it)
            if isinstance(o, BaseException):
                raise o
            return o, {}

        result = call_with_retries(send, rl, stats, sleep=c.sleep, rng=lambda: 1.0, base_delay=2, **kw)
        return result, stats, c

    def test_rate_limit_then_success_honors_retry_after(self):
        result, stats, c = self.run_calls([FakeAPIError(429, {"retry-after": "9"}), "ok"])
        self.assertEqual(result, "ok")
        self.assertEqual((stats.rate_limited, stats.retries, stats.failures), (1, 1, 0))
        self.assertAlmostEqual(sum(c.sleeps), 9)

    def test_overloaded_and_timeouts_are_retried(self):
        result, stats, _ = self.run_calls([FakeAPIError(529), APITimeoutError(), FakeAPIError(502), "ok"])
        self.assertEqual(result, "ok")
        self.assertEqual(stats.retries, 3)

    def test_gives_up_after_max_retries(self):
        result, stats, _ = self.run_calls([FakeAPIError(429)] * 4, max_retries=3)
        self.assertIsNone(result)
        self.assertEqual((stats.api_calls, stats.failures), (4, 1))
        self.assertEqual(len(stats.errors), 1)

    def test_permanent_error_not_retried(self):
        result, stats, _ = self.run_calls([FakeAPIError(400), "never"])
        self.assertIsNone(result)
        self.assertEqual((stats.api_calls, stats.retries, stats.failures), (1, 0, 1))

    def test_auth_error_is_fatal(self):
        with self.assertRaises(FatalLLMError):
            self.run_calls([FakeAPIError(401)])


class CacheTests(unittest.TestCase):
    def test_roundtrip_and_resume(self):
        with tempfile.TemporaryDirectory() as d:
            cache = ResponseCache(d)
            self.assertIsNone(cache.get("ab" * 32))
            cache.put("ab" * 32, {"corrected_html": "<table/>"}, meta={"schema": "TableSchema"})
            # A new instance (e.g. a re-run) sees the checkpoint.
            again = ResponseCache(d)
            self.assertEqual(again.get("ab" * 32), {"corrected_html": "<table/>"})
            self.assertEqual(len(again), 1)

    def test_failures_are_not_cached(self):
        with tempfile.TemporaryDirectory() as d:
            cache = ResponseCache(d)
            cache.put("cd" * 32, {})
            cache.put("ef" * 32, None)
            self.assertEqual(len(cache), 0)

    def test_disabled(self):
        cache = ResponseCache(None)
        cache.put("ab" * 32, {"x": 1})
        self.assertIsNone(cache.get("ab" * 32))
        self.assertFalse(cache.enabled)


if __name__ == "__main__":
    unittest.main()
