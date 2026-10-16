"""
Rate limiting, retries, response caching and failure accounting for LLM calls.

This module is provider-agnostic and stdlib-only so it can be unit-tested
without marker-pdf, the Anthropic SDK or network access. The Anthropic-specific
glue lives in modules/llm_service.py.

Why this exists: marker-pdf's built-in Claude service retries only twice
(3 s, then 6 s), ignores the ``retry-after`` header, uses a 30 s timeout and,
when it gives up, silently returns an empty result. On a long book this means
that hitting the API rate limit mid-run quietly drops LLM corrections.

Components:
* RateLimiter:    process-wide, thread-safe gate shared by marker's worker
                  threads. Supports a fixed requests-per-minute cap and
                  adaptive pauses driven by ``anthropic-ratelimit-*`` headers
                  and ``retry-after``.
* ResponseCache:  on-disk checkpoint of successful responses keyed by a hash
                  of everything that determines the answer (model, prompts,
                  images, schema). Re-running a failed conversion reuses them.
* LLMStats:       thread-safe counters reported at the end of a run.
* call_with_retries: retry loop with exponential backoff + jitter.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

# Statuses worth retrying: request timeout, conflict, rate limit, server errors,
# and Anthropic's 529 "overloaded".
RETRYABLE_STATUS = {408, 409, 429, 500, 502, 503, 504, 529}
FATAL_STATUS = {401, 403}  # bad/missing API key or no access: stop the run
RETRYABLE_EXCEPTION_NAMES = {"APITimeoutError", "APIConnectionError", "TimeoutError", "ConnectionError"}

# Header kinds reported by Anthropic: anthropic-ratelimit-<kind>-{limit,remaining,reset}
RATE_LIMIT_KINDS = ("requests", "tokens", "input-tokens", "output-tokens")


class FatalLLMError(RuntimeError):
    """An error that will not go away by retrying (e.g. invalid API key)."""


# --------------------------------------------------------------------------- #
# Stats
# --------------------------------------------------------------------------- #
@dataclass
class LLMStats:
    requests: int = 0          # calls made by marker to the service
    cache_hits: int = 0
    api_calls: int = 0         # HTTP attempts actually sent
    retries: int = 0
    rate_limited: int = 0      # 429 responses
    proactive_pauses: int = 0  # pauses triggered by low remaining quota
    invalid_responses: int = 0  # answered, but not valid JSON for the schema (after retries)
    repaired: int = 0          # free-text answers recovered by the lenient parser
    failures: int = 0          # gave up after all retries
    errors: list[str] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add(self, name: str, n: int = 1) -> None:
        with self._lock:
            setattr(self, name, getattr(self, name) + n)

    def error(self, message: str) -> None:
        with self._lock:
            self.failures += 1
            if len(self.errors) < 20:
                self.errors.append(message)

    @property
    def unsuccessful(self) -> int:
        """Calls whose correction was lost (gave up or unusable answer)."""
        return self.failures + self.invalid_responses

    def summary(self) -> str:
        return (
            f"{self.requests} LLM request(s): {self.cache_hits} from cache, "
            f"{self.api_calls} API call(s), {self.retries} retr(y/ies), "
            f"{self.rate_limited} rate-limited, {self.proactive_pauses} proactive pause(s), "
            f"{self.invalid_responses} invalid response(s), {self.failures} failure(s)"
            + (f", {self.repaired} repaired" if self.repaired else "")
        )


# --------------------------------------------------------------------------- #
# Rate limiter
# --------------------------------------------------------------------------- #
def _parse_reset(value: str | None, now: float) -> float | None:
    """Anthropic sends RFC 3339 timestamps for *-reset headers."""
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except ValueError:
        try:  # some proxies send seconds instead
            return now + float(value)
        except ValueError:
            return None


def parse_retry_after(headers) -> float | None:
    """Seconds to wait from 'retry-after-ms' / 'retry-after' headers, if any."""
    if not headers:
        return None
    try:
        ms = headers.get("retry-after-ms")
        if ms is not None:
            return max(0.0, float(ms) / 1000.0)
        ra = headers.get("retry-after")
        if ra is not None:
            return max(0.0, float(ra))
    except (TypeError, ValueError):
        return None
    return None


class RateLimiter:
    """
    Thread-safe gate in front of every API call.

    * rpm > 0 enforces a minimum interval of 60/rpm seconds between requests.
    * cooldown(seconds) pauses *all* threads (used for 429 / retry-after).
    * update_from_headers() pauses all threads until the quota resets when the
      remaining requests/tokens drop below `low_quota_fraction` of the limit.
    """

    def __init__(
        self,
        rpm: float = 0,
        low_quota_fraction: float = 0.15,
        max_pause: float = 120.0,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.rpm = rpm
        self.low_quota_fraction = low_quota_fraction
        self.max_pause = max_pause
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._next_slot = 0.0
        self._cooldown_until = 0.0

    def acquire(self) -> float:
        """Block until a request may be sent. Returns seconds waited."""
        waited = 0.0
        while True:
            with self._lock:
                now = self._clock()
                ready_at = max(self._cooldown_until, self._next_slot)
                if now >= ready_at:
                    if self.rpm and self.rpm > 0:
                        self._next_slot = max(now, self._next_slot) + 60.0 / self.rpm
                    return waited
                delay = ready_at - now
            delay = min(delay, self.max_pause)
            self._sleep(delay)
            waited += delay

    def cooldown(self, seconds: float) -> None:
        seconds = max(0.0, min(seconds, self.max_pause))
        with self._lock:
            self._cooldown_until = max(self._cooldown_until, self._clock() + seconds)

    def update_from_headers(self, headers) -> float:
        """Pause proactively when a quota is nearly exhausted. Returns pause (s)."""
        if not headers:
            return 0.0
        now = self._clock()
        pause_until = 0.0
        for kind in RATE_LIMIT_KINDS:
            try:
                limit = headers.get(f"anthropic-ratelimit-{kind}-limit")
                remaining = headers.get(f"anthropic-ratelimit-{kind}-remaining")
                if limit is None or remaining is None:
                    continue
                limit, remaining = float(limit), float(remaining)
            except (TypeError, ValueError):
                continue
            if limit <= 0 or remaining > limit * self.low_quota_fraction:
                continue
            reset = _parse_reset(headers.get(f"anthropic-ratelimit-{kind}-reset"), now)
            if reset and reset > now:
                pause_until = max(pause_until, reset)
        if pause_until > now:
            pause = min(pause_until - now, self.max_pause)
            self.cooldown(pause)
            return pause
        return 0.0


# --------------------------------------------------------------------------- #
# Response cache (checkpoint)
# --------------------------------------------------------------------------- #
CACHE_FORMAT_VERSION = 1


def cache_key(**parts) -> str:
    """Stable hash of everything that determines an LLM answer."""
    payload = json.dumps({"v": CACHE_FORMAT_VERSION, **parts}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ResponseCache:
    """One JSON file per successful response: <dir>/<key[:2]>/<key>.json."""

    def __init__(self, directory: str | os.PathLike | None):
        self.directory = Path(directory) if directory else None

    @property
    def enabled(self) -> bool:
        return self.directory is not None

    def _path(self, key: str) -> Path:
        return self.directory / key[:2] / f"{key}.json"

    def get(self, key: str):
        if not self.enabled:
            return None
        path = self._path(key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))["response"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError, OSError):
            return None

    def put(self, key: str, response, meta: dict | None = None) -> None:
        if not self.enabled or not response:
            return  # never cache failures or empty answers
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps({"response": response, "meta": meta or {}}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)  # atomic: an interrupted run never leaves a corrupt entry

    def __len__(self) -> int:
        if not self.enabled or not self.directory.exists():
            return 0
        return sum(1 for _ in self.directory.glob("*/*.json"))


# --------------------------------------------------------------------------- #
# Retry loop
# --------------------------------------------------------------------------- #
def classify_error(exc: BaseException) -> str:
    """'rate_limit' | 'retryable' | 'fatal' | 'permanent'."""
    status = getattr(exc, "status_code", None)
    if status == 429:
        return "rate_limit"
    if status in FATAL_STATUS:
        return "fatal"
    if status in RETRYABLE_STATUS:
        return "retryable"
    if type(exc).__name__ in RETRYABLE_EXCEPTION_NAMES or isinstance(exc, (TimeoutError, ConnectionError)):
        return "retryable"
    return "permanent"


def backoff_delay(attempt: int, base: float, max_delay: float, rng: Callable[[], float] = random.random) -> float:
    """Exponential backoff with full jitter in [0.5, 1.0] of the nominal delay."""
    nominal = min(max_delay, base * (2 ** max(0, attempt - 1)))
    return nominal * (0.5 + 0.5 * rng())


def call_with_retries(
    send: Callable[[], tuple[object, object]],
    limiter: RateLimiter,
    stats: LLMStats,
    max_retries: int = 8,
    base_delay: float = 5.0,
    max_delay: float = 120.0,
    sleep: Callable[[float], None] = time.sleep,
    rng: Callable[[], float] = random.random,
    describe: str = "LLM call",
):
    """
    Run `send()` (returns (result, headers)) with rate limiting and retries.

    Returns the result, or None after exhausting retries / on permanent errors.
    Raises FatalLLMError for authentication/permission errors.
    """
    total = max_retries + 1
    for attempt in range(1, total + 1):
        limiter.acquire()
        stats.add("api_calls")
        try:
            result, headers = send()
            if limiter.update_from_headers(headers) > 0:
                stats.add("proactive_pauses")
            return result
        except Exception as exc:  # noqa: BLE001 - classified below
            kind = classify_error(exc)
            if kind == "fatal":
                raise FatalLLMError(f"{describe}: {exc}") from exc
            if kind == "permanent" or attempt == total:
                stats.error(f"{describe}: {type(exc).__name__}: {exc}"[:300])
                return None
            headers = getattr(getattr(exc, "response", None), "headers", None)
            wait = parse_retry_after(headers)
            if kind == "rate_limit":
                stats.add("rate_limited")
                wait = wait if wait is not None else backoff_delay(attempt, base_delay, max_delay, rng)
                limiter.cooldown(wait)  # pause every thread, not just this one
            else:
                wait = wait if wait is not None else backoff_delay(attempt, base_delay, max_delay, rng)
                if getattr(exc, "status_code", None) == 529:
                    limiter.cooldown(wait)  # API overloaded: back off globally
                else:
                    sleep(wait)
            stats.add("retries")
    return None
