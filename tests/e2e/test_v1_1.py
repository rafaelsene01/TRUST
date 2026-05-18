"""TRUST v1.1 tests — Sources & UX.

Covers:
  - source_cache: TTL, hit, miss, expiry, invalidation
  - http_adapter: content normalisation, auth header building, cache integration
  - notion_adapter: ID extraction, block-to-markdown conversion (offline)
  - progress_reporter: phase tracking, summary output
  - grounding_loader: notion/http adapter dispatch (mocked)
  - volatile sources: hash change does not produce errors

These tests run fully offline — no real Notion/HTTP calls are made.
Network-dependent paths are covered by integration tests (not in CI by default).

Run:
    python -m pytest tests/e2e/test_v1_1.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.source_cache import CacheEntry, SourceCache
from adapters.http_adapter import HttpAdapter, _html_to_text, _build_auth_header
from adapters.notion_adapter import NotionAdapter, _extract_page_id, _block_to_markdown
from core.progress_reporter import ProgressReporter


# ---------------------------------------------------------------------------
# source_cache
# ---------------------------------------------------------------------------


def test_cache_miss_returns_none() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache")
        result = cache.get("my-source", "doc.md")
        assert result is None
    print("  ✓ cache miss returns None")


def test_cache_put_and_get() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=60)
        cache.put("notion", "page:abc123", "# Hello", "sha_abc")
        entry = cache.get("notion", "page:abc123")
        assert entry is not None
        assert entry.content == "# Hello"
        assert entry.sha256 == "sha_abc"
        assert entry.source_id == "notion"
    print("  ✓ cache put and get")


def test_cache_expiry() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=0)
        # TTL=0 → expires immediately
        cache.put("source", "doc.md", "content", "sha")
        # Manually set expires_at to past
        entry_path = list((Path(tmp) / "cache").rglob("*.json"))[0]
        data = json.loads(entry_path.read_text())
        past = (datetime.now(tz=timezone.utc) - timedelta(minutes=5)).isoformat()
        data["expires_at"] = past
        entry_path.write_text(json.dumps(data))

        result = cache.get("source", "doc.md")
        assert result is None, "Expired entry should return None"
    print("  ✓ cache expiry evicts entry")


def test_cache_invalidate() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=60)
        cache.put("s", "d.md", "c", "h")
        assert cache.get("s", "d.md") is not None
        removed = cache.invalidate("s", "d.md")
        assert removed is True
        assert cache.get("s", "d.md") is None
    print("  ✓ cache invalidation removes entry")


def test_cache_stats() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=60)
        cache.put("s1", "a.md", "c", "h")
        cache.put("s1", "b.md", "c", "h")
        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["expired_entries"] == 0
    print("  ✓ cache stats counts entries correctly")


# ---------------------------------------------------------------------------
# http_adapter — offline tests
# ---------------------------------------------------------------------------


def test_html_to_text_strips_tags() -> None:
    html = "<h1>Title</h1><p>Hello <b>world</b></p>"
    text = _html_to_text(html)
    assert "Title" in text
    assert "Hello" in text
    assert "<" not in text
    print("  ✓ html_to_text strips HTML tags")


def test_html_entities_decoded() -> None:
    html = "<p>&lt;script&gt; &amp; &quot;test&quot;</p>"
    text = _html_to_text(html)
    assert "<script>" in text
    assert "&" in text
    assert '"test"' in text
    print("  ✓ html_to_text decodes HTML entities")


def test_build_auth_header_bearer() -> None:
    import os
    os.environ["TEST_TOKEN_123"] = "my-secret-token"
    try:
        name, value = _build_auth_header({"type": "bearer", "token_env": "TEST_TOKEN_123"})
        assert name == "Authorization"
        assert value == "Bearer my-secret-token"
    finally:
        del os.environ["TEST_TOKEN_123"]
    print("  ✓ build_auth_header: bearer token")


def test_build_auth_header_bearer_missing_env() -> None:
    import pytest
    with pytest.raises(ValueError, match="Next action"):
        _build_auth_header({"type": "bearer", "token_env": "TRUST_TEST_NONEXISTENT_VAR_XYZ"})
    print("  ✓ build_auth_header: missing env raises actionable ValueError")


def test_build_auth_header_none_for_no_auth() -> None:
    result = _build_auth_header({})
    assert result is None
    print("  ✓ build_auth_header: empty config returns None")


def test_http_adapter_uses_cache_on_hit() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=60)
        cache.put("my-wiki", "page/architecture", "# Architecture\n\ncached content", "sha123")

        adapter = HttpAdapter(
            base_url="https://wiki.example.com",
            cache=cache,
        )
        doc = adapter.read("page/architecture", source_id="my-wiki")

        assert doc.content == "# Architecture\n\ncached content"
        assert doc.status_code == 200  # cache hit sets 200
    print("  ✓ http_adapter returns cached content without network call")


def test_http_adapter_normalises_html() -> None:
    """HttpAdapter strips HTML when content_type is text/html."""
    adapter = HttpAdapter(base_url="https://example.com")

    # Patch _fetch to return HTML
    with patch.object(adapter, "_fetch", return_value=(
        "<h1>Architecture</h1><p>Our system uses microservices.</p>",
        "text/html",
        200,
    )):
        doc = adapter.read("arch", source_id="test")
        assert "<h1>" not in doc.content
        assert "Architecture" in doc.content
    print("  ✓ http_adapter normalises HTML to plain text")


def test_http_adapter_normalises_json() -> None:
    """HttpAdapter wraps JSON in a Markdown code block."""
    adapter = HttpAdapter(base_url="https://api.example.com")

    with patch.object(adapter, "_fetch", return_value=(
        '{"title": "API Contracts", "version": "2"}',
        "application/json",
        200,
    )):
        doc = adapter.read("contracts", source_id="test")
        assert "```json" in doc.content
        assert "API Contracts" in doc.content
    print("  ✓ http_adapter wraps JSON in Markdown code block")


# ---------------------------------------------------------------------------
# notion_adapter — offline tests
# ---------------------------------------------------------------------------


def test_extract_page_id_bare_uuid() -> None:
    pid = _extract_page_id("a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")
    assert pid == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    print("  ✓ notion: extracts bare 32-char page ID")


def test_extract_page_id_with_prefix() -> None:
    pid = _extract_page_id("page:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4")
    assert pid == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    print("  ✓ notion: extracts ID from page: prefix")


def test_extract_page_id_from_url() -> None:
    url = "https://www.notion.so/My-Page-a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    pid = _extract_page_id(url)
    assert pid == "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
    print("  ✓ notion: extracts ID from Notion URL")


def test_extract_page_id_invalid_raises() -> None:
    import pytest
    with pytest.raises(ValueError):
        _extract_page_id("not-a-valid-id")
    print("  ✓ notion: invalid path raises ValueError")


def test_block_to_markdown_paragraph() -> None:
    block = {"type": "paragraph", "paragraph": {"rich_text": [{"plain_text": "Hello world"}]}}
    md = _block_to_markdown(block)
    assert "Hello world" in md
    print("  ✓ notion: paragraph block → markdown")


def test_block_to_markdown_headings() -> None:
    for level, prefix in ((1, "# "), (2, "## "), (3, "### ")):
        btype = f"heading_{level}"
        block = {"type": btype, btype: {"rich_text": [{"plain_text": "My Heading"}]}}
        md = _block_to_markdown(block)
        assert md.startswith(prefix), f"Expected '{prefix}', got: {md!r}"
    print("  ✓ notion: heading_1/2/3 blocks → # / ## / ###")


def test_block_to_markdown_code() -> None:
    block = {
        "type": "code",
        "code": {
            "language": "python",
            "rich_text": [{"plain_text": "x = 1"}],
        }
    }
    md = _block_to_markdown(block)
    assert "```python" in md
    assert "x = 1" in md
    print("  ✓ notion: code block → fenced markdown code")


def test_block_to_markdown_unsupported() -> None:
    block = {"type": "synced_block", "synced_block": {}}
    md = _block_to_markdown(block)
    assert "unsupported" in md.lower() or md == ""
    print("  ✓ notion: unsupported block emits comment or empty string")


def test_notion_adapter_uses_cache() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        cache = SourceCache(Path(tmp) / "cache", ttl_minutes=60)
        cache.put(
            "notion-docs",
            "page:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
            "# Architecture\n\nCached page content.",
            "sha_cached",
        )
        adapter = NotionAdapter(token_env="TRUST_TEST_NOTION_TOKEN", cache=cache)

        doc = adapter.read(
            "page:a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4",
            source_id="notion-docs",
        )
        assert doc.content == "# Architecture\n\nCached page content."
        assert doc.sha256 == "sha_cached"
    print("  ✓ notion: adapter returns cached content without API call")


# ---------------------------------------------------------------------------
# progress_reporter
# ---------------------------------------------------------------------------


def test_progress_reporter_phase_done() -> None:
    reporter = ProgressReporter(verbose=False)
    with reporter.phase("Grounding", total_steps=3) as p:
        p.step("Loading doc 1")
        p.step("Loading doc 2")
        p.step("Loading doc 3")

    assert len(reporter._phases) == 1
    assert reporter._phases[0].status == "done"
    assert reporter._phases[0].steps_done == 3
    print("  ✓ progress_reporter: phase completes with correct step count")


def test_progress_reporter_phase_halted() -> None:
    reporter = ProgressReporter(verbose=False)
    try:
        with reporter.phase("Agents", total_steps=6) as p:
            p.step("Agent 1")
            raise RuntimeError("simulated HALT")
    except RuntimeError:
        pass

    assert reporter._phases[0].status == "halted"
    print("  ✓ progress_reporter: exception sets phase status to halted")


def test_progress_reporter_skip_phase() -> None:
    reporter = ProgressReporter(verbose=False)
    reporter.skip_phase("Traceability", reason="disabled in config")
    assert reporter._phases[0].status == "skipped"
    print("  ✓ progress_reporter: skip_phase records skipped status")


def test_progress_reporter_summary() -> None:
    reporter = ProgressReporter(verbose=True)
    with reporter.phase("Phase A", total_steps=2) as p:
        p.step("step 1")
        p.step("step 2")
    reporter.skip_phase("Phase B")
    # Should not raise
    reporter.summary()
    print("  ✓ progress_reporter: summary runs without error")


# ---------------------------------------------------------------------------
# grounding_loader: volatile hash change is not an error
# ---------------------------------------------------------------------------


def test_volatile_hash_change_is_not_error() -> None:
    """validate_grounding_dod should not add errors for volatile sources that changed SHA."""
    from core.models import GroundingDoc, GroundingManifest

    manifest = GroundingManifest()
    manifest.docs.append(GroundingDoc(
        source_id="notion-arch",
        path="page:abc123",
        content="# New content",
        sha256="new_sha",
        bytes_read=500,
        sections=["new-content"],
        volatile=True,
    ))

    from core.grounding_loader import validate_grounding_dod
    ok, errors = validate_grounding_dod(
        manifest,
        min_total_bytes=100,
        previous_sha_map={"notion-arch:page:abc123": "old_sha"},
    )

    assert ok, f"Should not HALT for volatile hash change, got errors: {errors}"
    print("  ✓ grounding_loader: volatile source hash change does not trigger errors")


def test_non_volatile_hash_change_is_warned_not_errored() -> None:
    """Non-volatile hash change emits a warning but not a DoD error."""
    from core.models import GroundingDoc, GroundingManifest

    manifest = GroundingManifest()
    manifest.docs.append(GroundingDoc(
        source_id="in-setup",
        path="06-security-policy.md",
        content="# Updated policy",
        sha256="new_sha",
        bytes_read=1000,
        sections=["updated-policy"],
        volatile=False,
    ))

    from core.grounding_loader import validate_grounding_dod
    ok, errors = validate_grounding_dod(
        manifest,
        min_total_bytes=100,
        previous_sha_map={"in-setup:06-security-policy.md": "old_sha"},
    )

    # Non-volatile SHA change is a warning, not a DoD error
    assert ok, f"Non-volatile hash change should warn, not error. Got: {errors}"
    print("  ✓ grounding_loader: non-volatile hash change warns but does not error")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def main() -> int:
    print("\n" + "=" * 60)
    print("TRUST v1.1 — Sources & UX Test")
    print("=" * 60)

    tests = [
        # source_cache
        ("cache miss returns None", test_cache_miss_returns_none),
        ("cache put and get", test_cache_put_and_get),
        ("cache expiry evicts", test_cache_expiry),
        ("cache invalidation", test_cache_invalidate),
        ("cache stats", test_cache_stats),
        # http_adapter
        ("html_to_text strips tags", test_html_to_text_strips_tags),
        ("html entities decoded", test_html_entities_decoded),
        ("auth header bearer", test_build_auth_header_bearer),
        ("auth header missing env raises", test_build_auth_header_bearer_missing_env),
        ("auth header none for no-auth", test_build_auth_header_none_for_no_auth),
        ("http_adapter: cache hit", test_http_adapter_uses_cache_on_hit),
        ("http_adapter: normalise HTML", test_http_adapter_normalises_html),
        ("http_adapter: normalise JSON", test_http_adapter_normalises_json),
        # notion_adapter
        ("notion: extract bare ID", test_extract_page_id_bare_uuid),
        ("notion: extract page: prefix", test_extract_page_id_with_prefix),
        ("notion: extract from URL", test_extract_page_id_from_url),
        ("notion: invalid path raises", test_extract_page_id_invalid_raises),
        ("notion: paragraph block", test_block_to_markdown_paragraph),
        ("notion: heading blocks", test_block_to_markdown_headings),
        ("notion: code block", test_block_to_markdown_code),
        ("notion: unsupported block", test_block_to_markdown_unsupported),
        ("notion: cache hit", test_notion_adapter_uses_cache),
        # progress_reporter
        ("reporter: phase done", test_progress_reporter_phase_done),
        ("reporter: phase halted", test_progress_reporter_phase_halted),
        ("reporter: skip phase", test_progress_reporter_skip_phase),
        ("reporter: summary", test_progress_reporter_summary),
        # grounding_loader: volatile
        ("grounding: volatile hash no-error", test_volatile_hash_change_is_not_error),
        ("grounding: non-volatile hash warns only", test_non_volatile_hash_change_is_warned_not_errored),
    ]

    passed = 0
    failed = 0
    for name, fn in tests:
        print(f"  Testing: {name}")
        try:
            fn()
            passed += 1
        except Exception as exc:
            import traceback
            print(f"  ✗ FAILED: {exc}")
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
