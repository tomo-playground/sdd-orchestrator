"""observability 모듈 순수 함수 단위 테스트."""

from __future__ import annotations

import time
from unittest.mock import MagicMock

from services.agent.observability import (
    LLMCallResult,
    _current_root_span,
    _current_trace_id,
    _pipeline_start_time,
    _safe_extract_text,
    _to_hex32,
    end_root_span,
    get_pipeline_elapsed_sec,
    record_score,
    update_root_span,
)


class TestToHex32:
    def test_uuid_to_hex(self):
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        assert _to_hex32(uuid_str) == "550e8400e29b41d4a716446655440000"

    def test_already_hex(self):
        hex_str = "550e8400e29b41d4a716446655440000"
        assert _to_hex32(hex_str) == hex_str

    def test_empty_string(self):
        assert _to_hex32("") == ""


class TestSafeExtractText:
    def test_normal_response(self):
        part = MagicMock()
        part.text = "Hello world"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        assert _safe_extract_text(response) == "Hello world"

    def test_multiple_parts(self):
        part1 = MagicMock()
        part1.text = "Hello "
        part2 = MagicMock()
        part2.text = "world"
        content = MagicMock()
        content.parts = [part1, part2]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]

        assert _safe_extract_text(response) == "Hello world"

    def test_no_candidates(self):
        response = MagicMock()
        response.candidates = []
        assert _safe_extract_text(response) == ""

    def test_none_candidates(self):
        response = MagicMock()
        response.candidates = None
        assert _safe_extract_text(response) == ""

    def test_no_parts(self):
        candidate = MagicMock()
        candidate.content = MagicMock()
        candidate.content.parts = None
        response = MagicMock()
        response.candidates = [candidate]
        assert _safe_extract_text(response) == ""

    def test_part_without_text_attr(self):
        part = MagicMock(spec=[])  # no text attribute
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        assert _safe_extract_text(response) == ""

    def test_exception_fallback(self):
        response = MagicMock()
        response.candidates = None
        response.text = "fallback text"
        # Force candidates check to work (returns None), so fallback to response.text
        assert _safe_extract_text(response) == ""


class TestLLMCallResult:
    def test_record_extracts_text(self):
        result = LLMCallResult()
        part = MagicMock()
        part.text = "response text"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        response.usage_metadata = None

        result.record(response)
        assert result.output == "response text"
        assert result.usage is None

    def test_record_extracts_usage(self):
        result = LLMCallResult()
        part = MagicMock()
        part.text = "text"
        content = MagicMock()
        content.parts = [part]
        candidate = MagicMock()
        candidate.content = content
        response = MagicMock()
        response.candidates = [candidate]
        meta = MagicMock()
        meta.prompt_token_count = 100
        meta.candidates_token_count = 50
        meta.total_token_count = 150
        response.usage_metadata = meta

        result.record(response)
        assert result.usage == {"input": 100, "output": 50, "total": 150}

    def test_default_values(self):
        result = LLMCallResult()
        assert result.generation is None
        assert result.output == ""
        assert result.usage is None


class TestEndRootSpan:
    def test_ends_and_clears_span(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        end_root_span()

        mock_span.end.assert_called_once()
        assert _current_root_span.get() is None

    def test_noop_when_no_span(self):
        _current_root_span.set(None)
        end_root_span()  # 예외 없이 통과

    def test_idempotent(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        end_root_span()
        end_root_span()  # 두 번째 호출도 안전

        mock_span.end.assert_called_once()

    def test_swallows_exception(self):
        mock_span = MagicMock()
        mock_span.end.side_effect = RuntimeError("connection lost")
        _current_root_span.set(mock_span)

        end_root_span()  # 예외 삼키고 정상 종료
        assert _current_root_span.get() is None


class TestUpdateRootSpan:
    def test_updates_input(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        update_root_span(input_data={"topic": "test"})

        mock_span.update.assert_called_once_with(input={"topic": "test"})
        _current_root_span.set(None)

    def test_updates_output(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        update_root_span(output_data={"scenes": []})

        mock_span.update.assert_called_once_with(output={"scenes": []})
        _current_root_span.set(None)

    def test_noop_when_no_span(self):
        _current_root_span.set(None)
        update_root_span(input_data={"topic": "test"})  # 예외 없이 통과

    def test_swallows_exception(self):
        mock_span = MagicMock()
        mock_span.update.side_effect = RuntimeError("connection lost")
        _current_root_span.set(mock_span)

        update_root_span(input_data={"topic": "test"})  # 예외 삼키고 정상 종료
        _current_root_span.set(None)

    def test_noop_when_no_data(self):
        mock_span = MagicMock()
        _current_root_span.set(mock_span)

        update_root_span()  # input_data=None, output_data=None

        mock_span.update.assert_not_called()
        _current_root_span.set(None)


class TestRecordScore:
    """record_score() 헬퍼 단위 테스트."""

    def _setup_mocks(self):
        """전역 상태를 mock으로 설정하고 원본 값을 반환."""
        import services.agent.observability as obs

        orig_client = obs._langfuse_client
        orig_initialized = obs._initialized
        orig_trace = _current_trace_id.get()

        mock_client = MagicMock()
        obs._langfuse_client = mock_client
        obs._initialized = True
        _current_trace_id.set("abcdef1234567890abcdef1234567890")

        return mock_client, orig_client, orig_initialized, orig_trace

    def _teardown(self, orig_client, orig_initialized, orig_trace):
        """전역 상태 원복."""
        import services.agent.observability as obs

        obs._langfuse_client = orig_client
        obs._initialized = orig_initialized
        _current_trace_id.set(orig_trace)

    def test_success_numeric(self):
        """NUMERIC Score 정상 기록."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("revision_count", 2)

            mock_client.create_score.assert_called_once_with(
                trace_id="abcdef1234567890abcdef1234567890",
                name="revision_count",
                value=2,
                data_type="NUMERIC",
                comment=None,
            )
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_success_boolean_true(self):
        """BOOLEAN True -> int(1) 변환."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("first_pass", True)

            mock_client.create_score.assert_called_once_with(
                trace_id="abcdef1234567890abcdef1234567890",
                name="first_pass",
                value=1,
                data_type="BOOLEAN",
                comment=None,
            )
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_success_boolean_false(self):
        """BOOLEAN False -> int(0) 변환."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("first_pass", False)

            mock_client.create_score.assert_called_once_with(
                trace_id="abcdef1234567890abcdef1234567890",
                name="first_pass",
                value=0,
                data_type="BOOLEAN",
                comment=None,
            )
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_skip_when_value_none(self):
        """value=None -> 즉시 return, create_score 미호출."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("revision_count", None)

            mock_client.create_score.assert_not_called()
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_skip_when_not_initialized(self):
        """LangFuse 비활성 (client=None) -> 즉시 return."""
        import services.agent.observability as obs

        orig_client = obs._langfuse_client
        orig_initialized = obs._initialized
        orig_trace = _current_trace_id.get()
        try:
            obs._initialized = True
            obs._langfuse_client = None
            _current_trace_id.set("abcdef1234567890abcdef1234567890")

            record_score("revision_count", 2)
            # create_score 호출 불가 (client가 None)
        finally:
            obs._langfuse_client = orig_client
            obs._initialized = orig_initialized
            _current_trace_id.set(orig_trace)

    def test_skip_when_no_trace_id(self):
        """trace_id=None -> 즉시 return."""
        import services.agent.observability as obs

        orig_client = obs._langfuse_client
        orig_initialized = obs._initialized
        orig_trace = _current_trace_id.get()
        try:
            mock_client = MagicMock()
            obs._langfuse_client = mock_client
            obs._initialized = True
            _current_trace_id.set(None)

            record_score("revision_count", 2)

            mock_client.create_score.assert_not_called()
        finally:
            obs._langfuse_client = orig_client
            obs._initialized = orig_initialized
            _current_trace_id.set(orig_trace)

    def test_exception_does_not_raise(self):
        """create_score() 예외 시 파이프라인 미중단."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            mock_client.create_score.side_effect = RuntimeError("network error")

            record_score("revision_count", 2)  # 예외 삼키고 정상 종료
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_data_type_auto_inferred(self):
        """LANGFUSE_SCORE_CONFIGS에서 data_type 자동 추론."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("narrative_overall", 0.8)

            mock_client.create_score.assert_called_once_with(
                trace_id="abcdef1234567890abcdef1234567890",
                name="narrative_overall",
                value=0.8,
                data_type="NUMERIC",
                comment=None,
            )
        finally:
            self._teardown(orig_client, orig_init, orig_trace)

    def test_comment_passed(self):
        """comment 파라미터 전달 검증."""
        mock_client, orig_client, orig_init, orig_trace = self._setup_mocks()
        try:
            record_score("narrative_overall", 0.8, comment='{"hook":0.9}')

            mock_client.create_score.assert_called_once_with(
                trace_id="abcdef1234567890abcdef1234567890",
                name="narrative_overall",
                value=0.8,
                data_type="NUMERIC",
                comment='{"hook":0.9}',
            )
        finally:
            self._teardown(orig_client, orig_init, orig_trace)


class TestGetPipelineElapsedSec:
    """get_pipeline_elapsed_sec() 테스트."""

    def test_returns_none_when_not_set(self):
        """_pipeline_start_time 미설정 시 None."""
        orig = _pipeline_start_time.get()
        try:
            _pipeline_start_time.set(None)
            assert get_pipeline_elapsed_sec() is None
        finally:
            _pipeline_start_time.set(orig)

    def test_returns_elapsed_time(self):
        """설정 후 경과 시간 반환."""
        orig = _pipeline_start_time.get()
        try:
            _pipeline_start_time.set(time.monotonic() - 10)
            elapsed = get_pipeline_elapsed_sec()
            assert elapsed is not None
            assert 9.5 < elapsed < 11.0
        finally:
            _pipeline_start_time.set(orig)
