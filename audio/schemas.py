"""Pydantic request/response models for Audio Server API."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- TTS ---
class TTSSynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize")
    instruct: str = Field("", description="Voice design prompt (English)")
    language: str = Field("korean", description="Target language")
    seed: int = Field(-1, description="Random seed (-1 = random)")
    temperature: float = Field(0.7, ge=0.01, le=2.0)
    top_p: float = Field(0.8, ge=0.0, le=1.0)
    repetition_penalty: float = Field(1.0, ge=0.0, le=5.0)
    max_new_tokens: int = Field(1024, ge=64, le=4096)


class TTSSynthesizeResponse(BaseModel):
    audio_base64: str = Field(..., description="WAV audio encoded as base64")
    sample_rate: int
    duration: float = Field(..., description="Audio duration in seconds")
    quality_passed: bool
    cache_hit: bool = False


# --- MusicGen ---
class MusicGenerateRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Music description prompt")
    duration: float = Field(30.0, ge=1.0, le=300.0)
    seed: int = Field(-1, description="Random seed (-1 = random)")


class MusicGenerateResponse(BaseModel):
    audio_base64: str = Field(..., description="WAV audio encoded as base64")
    sample_rate: int
    actual_seed: int
    duration: float
    cache_hit: bool = False


# --- Health ---
class ModelStatus(BaseModel):
    name: str
    loaded: bool
    device: str = "unknown"


class HealthResponse(BaseModel):
    status: str = Field(..., description="ok | loading | error")
    models: list[ModelStatus] = []
