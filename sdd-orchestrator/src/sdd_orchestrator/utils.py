"""Shared utilities for the orchestrator."""

from __future__ import annotations

import logging

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, ClaudeSDKClient, TextBlock

logger = logging.getLogger(__name__)


async def query_agent(options: ClaudeAgentOptions, prompt: str) -> str:
    """Query a Claude agent and collect all response text blocks.

    Reusable across Lead Agent cycles and Designer sub-agent invocations.
    """
    collected: list[str] = []

    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)

        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        collected.append(block.text)
                        logger.info("agent_response_chunk chars=%d", len(block.text))
                        logger.debug("agent_response_preview=%r", block.text[:200])

    return "\n".join(collected) if collected else "(no response)"
