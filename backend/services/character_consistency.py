"""Character Consistency Resolver — centralizes all consistency decisions.

Analyzes a character's resources (LoRA, Reference Image, IP-Adapter settings)
and determines the optimal consistency strategy before the generation pipeline runs.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from config import (
    DEFAULT_IP_ADAPTER_WEIGHT,
    DEFAULT_LORA_WEIGHT,
    DEFAULT_REFERENCE_ONLY_WEIGHT,
    FALLBACK_STYLE_LORA_WEIGHT_MAX,
    logger,
)
from services.controlnet import load_reference_image


@dataclass(frozen=True)
class ConsistencyRequest:
    """Frontend-provided consistency parameters (groups IP-Adapter + Reference-only)."""

    use_ip_adapter: bool = False
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float | None = None
    use_reference_only: bool = False
    reference_only_weight: float = DEFAULT_REFERENCE_ONLY_WEIGHT


@dataclass(frozen=True)
class ConsistencyStrategy:
    """Immutable result of character consistency resolution."""

    # LoRAs
    style_loras: tuple[dict, ...] = ()
    style_lora_source: str = "none"  # "style_profile" | "character_fallback" | "none"

    # IP-Adapter
    ip_adapter_enabled: bool = False
    ip_adapter_reference: str | None = None
    ip_adapter_weight: float = DEFAULT_IP_ADAPTER_WEIGHT
    ip_adapter_model: str | None = None
    ip_adapter_guidance_start: float | None = None
    ip_adapter_guidance_end: float | None = None

    # Reference-only (skipped when IP-Adapter is active)
    reference_only_enabled: bool = False
    reference_only_weight: float = DEFAULT_REFERENCE_ONLY_WEIGHT

    # Meta
    quality_score: str = "low"  # "high" | "medium" | "low"
    warnings: tuple[str, ...] = ()


class CharacterConsistencyResolver:
    """Resolves the optimal consistency strategy for a character."""

    def __init__(self, db: Session):
        self.db = db

    def resolve(
        self,
        character,
        *,
        style_profile_loras: list[dict] | None = None,
        req: ConsistencyRequest | None = None,
    ) -> ConsistencyStrategy:
        """Analyze character resources and return optimal strategy."""
        if character is None:
            return ConsistencyStrategy()

        if req is None:
            req = ConsistencyRequest()
        warnings: list[str] = []

        # 1. Resolve style LoRAs (StyleProfile > character fallback)
        style_loras, style_source = self._resolve_style_loras(character, style_profile_loras)

        # 2. Resolve IP-Adapter
        ip_enabled, ip_ref, ip_weight, ip_model, ip_g_start, ip_g_end = self._resolve_ip_adapter(
            character,
            use_ip_adapter=req.use_ip_adapter,
            ip_adapter_reference=req.ip_adapter_reference,
            ip_adapter_weight=req.ip_adapter_weight,
            warnings=warnings,
        )

        # 3. Resolve Reference-only (mutually exclusive with IP-Adapter)
        ref_only_enabled = self._resolve_reference_only(
            use_reference_only=req.use_reference_only,
            ip_adapter_enabled=ip_enabled,
        )

        # 4. Assess quality
        has_character_lora = self._has_character_lora(character)
        quality = self._assess_quality(
            has_character_lora=has_character_lora,
            ip_adapter_enabled=ip_enabled,
            has_style_lora=len(style_loras) > 0,
            warnings=warnings,
        )

        return ConsistencyStrategy(
            style_loras=tuple(style_loras),
            style_lora_source=style_source,
            ip_adapter_enabled=ip_enabled,
            ip_adapter_reference=ip_ref,
            ip_adapter_weight=ip_weight,
            ip_adapter_model=ip_model,
            ip_adapter_guidance_start=ip_g_start,
            ip_adapter_guidance_end=ip_g_end,
            reference_only_enabled=ref_only_enabled,
            reference_only_weight=req.reference_only_weight,
            quality_score=quality,
            warnings=tuple(warnings),
        )

    def _resolve_style_loras(
        self,
        character,
        style_profile_loras: list[dict] | None,
    ) -> tuple[list[dict], str]:
        """Decide style LoRA source: StyleProfile or character fallback."""
        if style_profile_loras:
            return list(style_profile_loras), "style_profile"

        # Fallback: extract style LoRAs from character
        if character.loras:
            from models.lora import LoRA

            fallback = []
            for lora_info in character.loras:
                lora_id = lora_info.get("lora_id")
                lora_obj = self.db.query(LoRA).filter(LoRA.id == lora_id, LoRA.is_active.is_(True)).first()
                if lora_obj and lora_obj.lora_type == "style":
                    weight = lora_info.get("weight")
                    if weight is None:
                        weight = float(lora_obj.optimal_weight or lora_obj.default_weight or DEFAULT_LORA_WEIGHT)
                    fallback.append(
                        {
                            "name": lora_obj.name,
                            "weight": min(weight, FALLBACK_STYLE_LORA_WEIGHT_MAX),  # Cap fallback weight
                            "trigger_words": lora_obj.trigger_words or [],
                        }
                    )
            if fallback:
                return fallback, "character_fallback"

        return [], "none"

    def _resolve_ip_adapter(
        self,
        character,
        *,
        use_ip_adapter: bool,
        ip_adapter_reference: str | None,
        ip_adapter_weight: float | None,
        warnings: list[str],
    ) -> tuple[bool, str | None, float, str | None, float | None, float | None]:
        """Decide IP-Adapter settings. Auto-enable if reference image exists.

        Returns:
            (enabled, reference, weight, model, guidance_start, guidance_end)
        """
        guidance_start = getattr(character, "ip_adapter_guidance_start", None)
        guidance_end = getattr(character, "ip_adapter_guidance_end", None)

        # Already fully specified
        if use_ip_adapter and ip_adapter_reference:
            weight = ip_adapter_weight or character.ip_adapter_weight or DEFAULT_IP_ADAPTER_WEIGHT
            model = self._resolve_ip_adapter_model(character)
            return True, ip_adapter_reference, weight, model, guidance_start, guidance_end

        # Auto-enable: check if character has a reference image
        from config import IP_ADAPTER_AUTO_ENABLE  # noqa: PLC0415

        if not IP_ADAPTER_AUTO_ENABLE:
            return False, None, DEFAULT_IP_ADAPTER_WEIGHT, None, None, None

        ref_image = load_reference_image(character.name, db=self.db)
        if ref_image:
            # Auto-enable: character weight takes priority (user didn't explicitly set)
            weight = character.ip_adapter_weight or ip_adapter_weight or DEFAULT_IP_ADAPTER_WEIGHT
            model = self._resolve_ip_adapter_model(character)
            logger.info(
                "✨ [Resolver] Auto-enabled IP-Adapter for '%s' (weight=%.2f, model=%s)",
                character.name,
                weight,
                model,
            )
            return True, character.name, weight, model, guidance_start, guidance_end

        # No reference image available
        if use_ip_adapter:
            warnings.append(f"캐릭터 '{character.name}'의 참조 이미지가 없어 IP-Adapter를 사용할 수 없습니다.")
        return False, None, DEFAULT_IP_ADAPTER_WEIGHT, None, None, None

    @staticmethod
    def _resolve_ip_adapter_model(character) -> str | None:
        """Resolve IP-Adapter model: character > group.style_profile > default.

        Priority:
        1. 캐릭터 명시값 (character.ip_adapter_model)
        2. 그룹 스타일 프로필 기본값 (group.style_profile.default_ip_adapter_model)
        3. 글로벌 기본값 (None → downstream defaults to clip(NOOB-IPA-MARK1))
        """
        char_model = getattr(character, "ip_adapter_model", None)
        if char_model:
            return char_model

        # Character → Group → StyleProfile (ownership cascade)
        group = getattr(character, "group", None)
        if group:
            style_profile = getattr(group, "style_profile", None)
            if style_profile:
                default_model = getattr(style_profile, "default_ip_adapter_model", None)
                if default_model:
                    return default_model

        return None

    @staticmethod
    def _resolve_reference_only(
        *,
        use_reference_only: bool,
        ip_adapter_enabled: bool,
    ) -> bool:
        """Reference-only is skipped when IP-Adapter is active."""
        if use_reference_only and ip_adapter_enabled:
            logger.info("🎨 [Resolver] Reference-only skipped — IP-Adapter takes priority")
            return False
        return use_reference_only

    @staticmethod
    def _has_character_lora(character) -> bool:
        """Check if character has any character-type LoRA."""
        if not character.loras:
            return False
        return any(lora_info.get("lora_type") != "style" for lora_info in character.loras)

    @staticmethod
    def _assess_quality(
        *,
        has_character_lora: bool,
        ip_adapter_enabled: bool,
        has_style_lora: bool,
        warnings: list[str],
    ) -> str:
        """Assess expected consistency quality."""
        if has_character_lora and ip_adapter_enabled:
            return "high"
        if has_character_lora or ip_adapter_enabled:
            return "medium"
        warnings.append(
            "캐릭터에 LoRA와 참조 이미지가 없어 일관성이 낮을 수 있습니다. "
            "캐릭터 LoRA 등록 또는 참조 이미지 생성을 권장합니다."
        )
        return "low"
