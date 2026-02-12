"""Test Pydantic max_length validation on schemas."""

import pytest
from pydantic import ValidationError

from schemas import (
    SceneGenerateRequest,
    StoryboardBase,
    StoryboardRequest,
    StoryboardScene,
)


class TestStoryboardRequestMaxLength:
    def test_topic_within_limit(self):
        req = StoryboardRequest(topic="짧은 주제")
        assert req.topic == "짧은 주제"

    def test_topic_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardRequest(topic="x" * 501)

    def test_description_within_limit(self):
        req = StoryboardRequest(topic="ok", description="d" * 2000)
        assert len(req.description) == 2000

    def test_description_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardRequest(topic="ok", description="d" * 2001)


class TestStoryboardBaseMaxLength:
    def test_title_within_limit(self):
        sb = StoryboardBase(title="t" * 200)
        assert len(sb.title) == 200

    def test_title_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardBase(title="t" * 201)

    def test_caption_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardBase(title="ok", caption="c" * 501)

    def test_description_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardBase(title="ok", description="d" * 2001)


class TestStoryboardSceneMaxLength:
    def test_script_within_limit(self):
        scene = StoryboardScene(scene_id=1, script="s" * 1000)
        assert len(scene.script) == 1000

    def test_script_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardScene(scene_id=1, script="s" * 1001)

    def test_image_prompt_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardScene(scene_id=1, script="ok", image_prompt="p" * 2001)

    def test_negative_prompt_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            StoryboardScene(scene_id=1, script="ok", negative_prompt="n" * 2001)


class TestSceneGenerateRequestMaxLength:
    def test_prompt_within_limit(self):
        req = SceneGenerateRequest(prompt="p" * 4000)
        assert len(req.prompt) == 4000

    def test_prompt_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            SceneGenerateRequest(prompt="p" * 4001)

    def test_negative_prompt_exceeds_limit(self):
        with pytest.raises(ValidationError, match="string_too_long"):
            SceneGenerateRequest(prompt="ok", negative_prompt="n" * 2001)
