"""Agent 공통 유틸리티."""

from __future__ import annotations

import hashlib


def topic_key(topic: str) -> str:
    """토픽 문자열을 12자리 MD5 해시로 변환한다 (Memory Store 네임스페이스용)."""
    return hashlib.md5(topic.encode()).hexdigest()[:12]
