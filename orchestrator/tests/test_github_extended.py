"""Unit tests for trigger_workflow and cancel_workflow tools."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest


class TestTriggerWorkflow:
    @pytest.mark.asyncio
    async def test_success(self):
        from orchestrator.tools.github import do_trigger_workflow

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_trigger_workflow("sentry-autofix.yml")

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_with_inputs(self):
        from orchestrator.tools.github import do_trigger_workflow

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ) as mock_exec:
            result = await do_trigger_workflow("sentry-autofix.yml", inputs={"issue_number": "42"})

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True
        # Verify -f flags were passed
        call_args = mock_exec.call_args[0]
        assert "-f" in call_args
        assert "issue_number=42" in call_args

    @pytest.mark.asyncio
    async def test_not_in_allowlist(self):
        from orchestrator.tools.github import do_trigger_workflow

        result = await do_trigger_workflow("dangerous-workflow.yml")

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
        assert "allowlist" in data["message"].lower() or "allowed" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_gh_error(self):
        from orchestrator.tools.github import do_trigger_workflow

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"workflow not found")
        mock_proc.returncode = 1

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_trigger_workflow("sdd-review.yml")

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False


class TestCancelWorkflow:
    @pytest.mark.asyncio
    async def test_success(self):
        from orchestrator.tools.github import do_cancel_workflow

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_cancel_workflow(12345)

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_already_completed(self):
        from orchestrator.tools.github import do_cancel_workflow

        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"cannot cancel completed run")
        mock_proc.returncode = 1

        with patch(
            "orchestrator.tools.github.asyncio.create_subprocess_exec",
            return_value=mock_proc,
        ):
            result = await do_cancel_workflow(12345)

        data = json.loads(result["content"][0]["text"])
        assert data["success"] is False
