"""Tests for ComfyUI workflow_runner — async queue + poll + download."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from services.sd_client.comfyui.workflow_runner import (
    _POLL_INITIAL,
    _POLL_MAX,
    _POLL_MULTIPLIER,
    queue_prompt,
    run_workflow,
    wait_for_result,
)


def _mock_response(json_data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.content = b"fake_image_bytes"
    resp.raise_for_status = MagicMock()
    return resp


class TestQueuePrompt:
    """queue_prompt() — submit workflow to ComfyUI."""

    @pytest.mark.asyncio
    async def test_returns_prompt_id(self):
        client = AsyncMock()
        client.post.return_value = _mock_response({"prompt_id": "abc-123"})

        result = await queue_prompt(client, {"nodes": {}})
        assert result == "abc-123"
        client.post.assert_called_once_with("/prompt", json={"prompt": {"nodes": {}}})

    @pytest.mark.asyncio
    async def test_comfyui_error_raises(self):
        client = AsyncMock()
        client.post.return_value = _mock_response({"error": "invalid workflow"})

        with pytest.raises(RuntimeError, match="ComfyUI queue error"):
            await queue_prompt(client, {})

    @pytest.mark.asyncio
    async def test_no_prompt_id_raises(self):
        client = AsyncMock()
        client.post.return_value = _mock_response({"status": "ok"})

        with pytest.raises(RuntimeError, match="no prompt_id"):
            await queue_prompt(client, {})

    @pytest.mark.asyncio
    async def test_connect_error_no_retry(self):
        """ConnectError should raise immediately without retry."""
        client = AsyncMock()
        client.post.side_effect = httpx.ConnectError("refused")

        with pytest.raises(httpx.ConnectError):
            await queue_prompt(client, {})
        assert client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self):
        """Should retry on transient HTTP errors up to 3 times."""
        client = AsyncMock()
        client.post.side_effect = [
            httpx.ReadTimeout("timeout"),
            httpx.ReadTimeout("timeout"),
            _mock_response({"prompt_id": "retry-ok"}),
        ]

        with patch("services.sd_client.comfyui.workflow_runner._RETRY_DELAYS", [0.01, 0.01, 0.01]):
            result = await queue_prompt(client, {})
        assert result == "retry-ok"
        assert client.post.call_count == 3


class TestWaitForResult:
    """wait_for_result() — poll /history and download images."""

    @pytest.mark.asyncio
    async def test_success_download(self):
        """Should poll history and download images."""
        history_resp = _mock_response({
            "prompt-1": {
                "status": {"status_str": "success"},
                "outputs": {
                    "save_node": {
                        "images": [{"filename": "img.png", "subfolder": "", "type": "output"}]
                    }
                },
            }
        })
        img_resp = MagicMock()
        img_resp.content = b"\x89PNG_fake"
        img_resp.raise_for_status = MagicMock()

        client = AsyncMock()
        client.get.side_effect = [history_resp, img_resp]

        with patch("services.sd_client.comfyui.workflow_runner.COMFYUI_QUEUE_TIMEOUT", 10):
            images = await wait_for_result(client, "prompt-1", "save_node")

        assert len(images) == 1
        assert images[0] == b"\x89PNG_fake"

    @pytest.mark.asyncio
    async def test_execution_error_raises(self):
        """Should raise RuntimeError on execution error."""
        history_resp = _mock_response({
            "prompt-1": {
                "status": {"status_str": "error"},
                "node_errors": {"node_1": "bad node"},
            }
        })
        client = AsyncMock()
        client.get.return_value = history_resp

        with patch("services.sd_client.comfyui.workflow_runner.COMFYUI_QUEUE_TIMEOUT", 10):
            with pytest.raises(RuntimeError, match="execution error"):
                await wait_for_result(client, "prompt-1", "save_node")

    @pytest.mark.asyncio
    async def test_timeout_raises(self):
        """Should raise TimeoutError if result never appears."""
        client = AsyncMock()
        client.get.return_value = _mock_response({})

        with patch("services.sd_client.comfyui.workflow_runner.COMFYUI_QUEUE_TIMEOUT", 0.1):
            with pytest.raises(TimeoutError, match="timeout"):
                await wait_for_result(client, "prompt-1", "save_node")

    def test_adaptive_polling_constants(self):
        """Verify adaptive polling configuration values."""
        assert _POLL_INITIAL == 0.5
        assert _POLL_MULTIPLIER == 1.5
        assert _POLL_MAX == 5.0


class TestRunWorkflow:
    """run_workflow() — end-to-end queue + wait."""

    @pytest.mark.asyncio
    async def test_integration(self):
        """Should queue, wait, and return images."""
        client = AsyncMock()
        queue_resp = _mock_response({"prompt_id": "int-1"})
        history_resp = _mock_response({
            "int-1": {
                "status": {"status_str": "success"},
                "outputs": {
                    "save": {"images": [{"filename": "out.png", "subfolder": "", "type": "output"}]}
                },
            }
        })
        img_resp = MagicMock()
        img_resp.content = b"image_data"
        img_resp.raise_for_status = MagicMock()

        client.post.return_value = queue_resp
        client.get.side_effect = [history_resp, img_resp]

        with patch("services.sd_client.comfyui.workflow_runner.COMFYUI_QUEUE_TIMEOUT", 10):
            images = await run_workflow(client, {"nodes": {}}, "save")

        assert images == [b"image_data"]
