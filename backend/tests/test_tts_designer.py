
import pytest
from unittest.mock import MagicMock, patch
from services.creative_pipeline import run_pipeline
from services.creative_qc import validate_tts_design
from services.video.utils import calculate_scene_durations
from schemas import VideoScene

def test_validate_tts_design_success():
    """Test validation of correct TTS design output."""
    valid_output = [
        {
            "scene_id": 1,
            "voice_design_prompt": "A happy young man laughing",
            "pacing": {"head_padding": 0.5, "tail_padding": 0.5}
        }
    ]
    res = validate_tts_design(valid_output)
    assert res["ok"] is True
    assert res["checks"]["tts_design_present"] == "PASS"

def test_validate_tts_design_missing_prompt():
    """Test validation with missing voice_design_prompt."""
    invalid_output = [
        {
            "scene_id": 1,
            "pacing": {"head_padding": 0.5}
        }
    ]
    res = validate_tts_design(invalid_output)
    assert res["ok"] is False
    assert any("missing voice_design_prompt" in issue for issue in res["issues"])

def test_calculate_scene_durations_with_padding():
    """Test duration calculation including head and tail padding."""
    scenes = [
        VideoScene(
            image_url="http://test.com/1.png",
            script="Hello world",
            duration=3.0,
            head_padding=1.0,
            tail_padding=1.0
        )
    ]
    tts_valid = [True]
    tts_durations = [2.0]
    speed_multiplier = 1.0
    tts_padding = 0.8
    
    # Expected: max(3.0, 1.0(head) + 2.0(tts) + 1.0(tail) + 0.8(default_pad)) = 4.8
    durations = calculate_scene_durations(scenes, tts_valid, tts_durations, speed_multiplier, tts_padding)
    assert durations[0] == 4.8

def test_calculate_scene_durations_no_tts():
    """Test duration when TTS is not valid (should use base duration)."""
    scenes = [VideoScene(image_url="http://test.com/1.png", duration=3.0)]
    durations = calculate_scene_durations(scenes, [False], [0.0], 1.0, 0.8)
    assert durations[0] == 3.0

def test_build_audio_filters_adelay():
    """Test that build_audio_filters correctly incorporates head_padding into adelay."""
    from services.video.builder import VideoBuilder
    from services.video.filters import build_audio_filters
    from schemas import VideoRequest
    
    request = VideoRequest(
        scenes=[
            VideoScene(image_url="test.png", head_padding=0.5)
        ],
        transition_type="fade"
    )
    builder = VideoBuilder(request)
    builder.transition_dur = 0.5
    builder.scene_durations = [3.0]
    
    # Run filters
    build_audio_filters(builder)
    
    # Check filters: 0.5(transition) + 0.5(head_pad) = 1000ms
    assert len(builder.filters) > 0
    assert "adelay=1000|1000" in builder.filters[0]

@patch("services.creative_pipeline._run_llm_step")
def test_pipeline_structure(mock_run_llm_step):
    """Verify tts_designer is in the correct pipeline position."""
    from services.creative_pipeline import PIPELINE_STEPS
    steps = [s.name for s in PIPELINE_STEPS]
    assert "tts_designer" in steps
    assert steps.index("tts_designer") > steps.index("cinematographer")
    assert steps.index("tts_designer") < steps.index("sound_designer")

def test_send_to_studio_mapping():
    """Test mapping of tts_design data from CreativeSession to Studio Scene."""
    from services.creative_studio import _build_scene
    
    mock_scene_data = {
        "order": 0,
        "script": "Test script",
        "tts_design": {
            "voice_design_prompt": "Emotional voice",
            "pacing": {"head_padding": 1.1, "tail_padding": 2.2}
        }
    }
    
    scene = _build_scene(mock_scene_data, storyboard_id=1, characters={}, fallback_char_id=None)
    
    assert scene.voice_design_prompt == "Emotional voice"
    assert scene.head_padding == 1.1
    assert scene.tail_padding == 2.2

def test_tts_priority_logic():
    """Verify that voice_design_prompt takes priority in TTS generation."""
    # This logic lives in services/video/scene_processing.py
    # We can mock the builder and check how it resolves voice_design
    from services.video.scene_processing import _get_voice_design_for_scene
    
    class MockReq:
        voice_design_prompt = "Global prompt"
        
    class MockScene:
        voice_design_prompt = "Scene specific prompt"
        speaker = "A"
        
    class MockBuilder:
        request = MockReq()
        
    # Case 1: Scene prompt exists
    voice = _get_voice_design_for_scene(MockBuilder(), MockScene(), preset_voice_design="Preset", clean_script="Test")
    assert voice == "Scene specific prompt"
    
    # Case 2: Only Global prompt exists
    MockScene.voice_design_prompt = None
    voice = _get_voice_design_for_scene(MockBuilder(), MockScene(), preset_voice_design="Preset", clean_script="Test")
    assert voice == "Global prompt"
    
    # Case 3: Fallback to Preset (Narrator)
    MockReq.voice_design_prompt = None
    voice = _get_voice_design_for_scene(MockBuilder(), MockScene(), preset_voice_design="Preset", clean_script="Test")
    assert voice == "Preset"

if __name__ == "__main__":
    pytest.main([__file__])
