"""Unit tests for Sentry scanning tool."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from sdd_orchestrator.tools.sentry import (
    _fetch_latest_stacktrace,
    _fetch_sentry_issues,
    _get_existing_sentry_ids,
    do_sentry_scan,
)

# Recent timestamp for firstSeen — always within lookback window
_RECENT_TS = (datetime.now(UTC) - timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%SZ")


class TestFetchSentryIssues:
    @pytest.mark.asyncio
    async def test_success(self):
        issue = {
            "id": "12345",
            "title": "ZeroDivisionError",
            "culprit": "api.views.render",
            "level": "error",
            "firstSeen": _RECENT_TS,
            "lastSeen": "2026-03-24T01:00:00Z",
            "count": "5",
            "permalink": "https://sentry.io/issues/12345/",
        }
        response = httpx.Response(200, json=[issue])
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        result = await _fetch_sentry_issues(client, "test-project", since_hours=2)
        assert len(result) == 1
        assert result[0]["id"] == "12345"
        client.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_timeout(self):
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = httpx.TimeoutException("read timeout")

        result = await _fetch_sentry_issues(client, "test-project", since_hours=2)
        assert result == []

    @pytest.mark.asyncio
    async def test_auth_error(self):
        response = httpx.Response(401, json={"detail": "Invalid token"})
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        result = await _fetch_sentry_issues(client, "test-project", since_hours=2)
        assert result == []

    @pytest.mark.asyncio
    async def test_rate_limit_retry(self):
        """429 with Retry-After → wait and retry once."""

        issue = {
            "id": "99",
            "title": "Err",
            "culprit": "x",
            "level": "error",
            "firstSeen": _RECENT_TS,
            "lastSeen": "2026-03-24T01:00:00Z",
            "count": "1",
            "permalink": "https://sentry.io/issues/99/",
        }
        rate_resp = httpx.Response(429, headers={"Retry-After": "1"}, json={})
        ok_resp = httpx.Response(200, json=[issue])

        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.side_effect = [rate_resp, ok_resp]

        with patch("sdd_orchestrator.tools.sentry.asyncio.sleep", new_callable=AsyncMock):
            result = await _fetch_sentry_issues(client, "test-project", since_hours=2)

        assert len(result) == 1
        assert client.get.call_count == 2


class TestFetchLatestStacktrace:
    @pytest.mark.asyncio
    async def test_success(self):
        event = {
            "entries": [
                {
                    "type": "exception",
                    "data": {
                        "values": [
                            {
                                "type": "ZeroDivisionError",
                                "value": "division by zero",
                                "stacktrace": {
                                    "frames": [
                                        {
                                            "filename": "app.py",
                                            "lineNo": 42,
                                            "function": "render",
                                        }
                                    ]
                                },
                            }
                        ]
                    },
                }
            ]
        }
        response = httpx.Response(200, json=event)
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        result = await _fetch_latest_stacktrace(client, "12345")
        assert "ZeroDivisionError" in result

    @pytest.mark.asyncio
    async def test_no_entries(self):
        response = httpx.Response(200, json={"entries": []})
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        result = await _fetch_latest_stacktrace(client, "12345")
        assert result == ""


class TestGetExistingSentryIds:
    @pytest.mark.asyncio
    async def test_parses_ids_from_gh(self):
        gh_output = json.dumps(
            [
                {"title": "[Sentry] Bug", "body": "sentry-id: 111\nDetails..."},
                {"title": "[Sentry] Err", "body": "sentry-id: 222\nMore"},
            ]
        )
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (gh_output.encode(), b"")
        mock_proc.returncode = 0

        with patch(
            "sdd_orchestrator.tools.sentry.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await _get_existing_sentry_ids()

        assert result == {"111", "222"}

    @pytest.mark.asyncio
    async def test_empty_on_gh_error(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error")
        mock_proc.returncode = 1

        with patch(
            "sdd_orchestrator.tools.sentry.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await _get_existing_sentry_ids()

        assert result == set()


class TestSentryScan:
    @pytest.mark.asyncio
    async def test_no_token(self):
        with patch("sdd_orchestrator.tools.sentry.SENTRY_AUTH_TOKEN", ""):
            result = await do_sentry_scan()

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert "error" in data

    @pytest.mark.asyncio
    async def test_dedup_skips_existing(self):
        issue = {
            "id": "111",
            "title": "Bug",
            "culprit": "x",
            "level": "error",
            "firstSeen": _RECENT_TS,
            "lastSeen": "2026-03-24T01:00:00Z",
            "count": "1",
            "permalink": "https://sentry.io/issues/111/",
        }

        with (
            patch("sdd_orchestrator.tools.sentry.SENTRY_AUTH_TOKEN", "test-token"),
            patch("sdd_orchestrator.tools.sentry.SENTRY_PROJECTS", ["test-project"]),
            patch(
                "sdd_orchestrator.tools.sentry._fetch_sentry_issues",
                new_callable=AsyncMock,
                return_value=[issue],
            ),
            patch(
                "sdd_orchestrator.tools.sentry._get_existing_sentry_ids",
                new_callable=AsyncMock,
                return_value={"111"},
            ),
            patch(
                "sdd_orchestrator.tools.sentry._create_github_issue",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            result = await do_sentry_scan()

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["skipped"] >= 1
        mock_create.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_and_triggers(self):
        issue = {
            "id": "999",
            "title": "NewBug",
            "culprit": "x",
            "level": "error",
            "firstSeen": _RECENT_TS,
            "lastSeen": "2026-03-24T01:00:00Z",
            "count": "1",
            "permalink": "https://sentry.io/issues/999/",
        }

        with (
            patch("sdd_orchestrator.tools.sentry.SENTRY_AUTH_TOKEN", "test-token"),
            patch("sdd_orchestrator.tools.sentry.SENTRY_PROJECTS", ["test-project"]),
            patch(
                "sdd_orchestrator.tools.sentry._fetch_sentry_issues",
                new_callable=AsyncMock,
                return_value=[issue],
            ),
            patch(
                "sdd_orchestrator.tools.sentry._fetch_latest_stacktrace",
                new_callable=AsyncMock,
                return_value="Traceback...",
            ),
            patch(
                "sdd_orchestrator.tools.sentry._get_existing_sentry_ids",
                new_callable=AsyncMock,
                return_value=set(),
            ),
            patch(
                "sdd_orchestrator.tools.sentry._create_github_issue",
                new_callable=AsyncMock,
                return_value=42,
            ) as mock_create,
            patch(
                "sdd_orchestrator.tools.sentry._trigger_autofix",
                new_callable=AsyncMock,
            ) as mock_trigger,
        ):
            result = await do_sentry_scan()

        text = result["content"][0]["text"]
        data = json.loads(text)
        assert data["created"] >= 1
        assert data["triggered"] >= 1
        assert mock_create.call_count >= 1
        assert mock_trigger.call_count >= 1


class TestFetchErrorCounts:
    """Tests for fetch_error_counts — lastSeen-based filtering for rollback."""

    @pytest.mark.asyncio
    async def test_includes_recent_lastseen(self):
        """Issues with recent lastSeen are included regardless of firstSeen."""
        from sdd_orchestrator.tools.sentry import fetch_error_counts

        recent_last_seen = (datetime.now(UTC) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old_first_seen = (datetime.now(UTC) - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {
            "id": "1",
            "title": "OldBug",
            "firstSeen": old_first_seen,  # 20 days ago — within 30-day SENTRY_LOOKBACK_ALL_HOURS window
            "lastSeen": recent_last_seen,  # recent activity
            "count": "10",
        }
        response = httpx.Response(200, json=[issue])
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        with patch("sdd_orchestrator.tools.sentry.SENTRY_PROJECTS", ["test-project"]):
            counts = await fetch_error_counts(client, since_hours=0.1)
        total = sum(counts.values())
        assert total == 1  # 1 active issue (count by issues, not cumulative events)

    @pytest.mark.asyncio
    async def test_excludes_stale_lastseen(self):
        """Issues with stale lastSeen are excluded even if firstSeen is within window."""
        from sdd_orchestrator.tools.sentry import fetch_error_counts

        recent_first_seen = (datetime.now(UTC) - timedelta(days=20)).strftime("%Y-%m-%dT%H:%M:%SZ")
        stale_last_seen = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        issue = {
            "id": "2",
            "title": "StaleBug",
            "firstSeen": recent_first_seen,  # within 30-day window — passes firstSeen filter
            "lastSeen": stale_last_seen,  # 1h ago — outside 0.1h lookback cutoff
            "count": "100",
        }
        response = httpx.Response(200, json=[issue])
        client = AsyncMock(spec=httpx.AsyncClient)
        client.get.return_value = response

        with patch("sdd_orchestrator.tools.sentry.SENTRY_PROJECTS", ["test-project"]):
            counts = await fetch_error_counts(client, since_hours=0.1)
        total = sum(counts.values())
        assert total == 0  # excluded because lastSeen is stale
