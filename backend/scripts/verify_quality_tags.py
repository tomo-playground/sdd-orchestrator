"""실사풍 Style Profile quality tag 호환성 검증 스크립트.

테스트 시나리오:
  1. Anime StyleProfile → masterpiece, best_quality 포함 확인
  2. 순수 실사풍 default_positive 시뮬레이션 → anime fallback 미주입 확인
  3. StyleProfile 없는 경우 → fallback 주입 확인
  4. MultiCharacterComposer 동일 검증
  5. compose_for_reference 검증
  6. 스토리보드 438 실제 씬 프롬프트 검증

Usage:
  cd backend && python scripts/verify_quality_tags.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from services.prompt import split_prompt_tokens
from services.prompt.composition import PromptBuilder
from services.style_context import resolve_style_context_from_group

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results: list[tuple[str, bool]] = []


def check(name: str, condition: bool, detail: str = ""):
    status = PASS if condition else FAIL
    results.append((name, condition))
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    print(msg)


def main():
    db = SessionLocal()
    builder = PromptBuilder(db)

    print("\n═══ 실사풍 Style Profile Quality Tag 검증 ═══\n")

    # ── 1. Anime StyleProfile (스토리보드 438 = Flat Color Anime) ──
    print("▸ 시나리오 1: Anime StyleProfile (group_id=3)")
    ctx = resolve_style_context_from_group(3, db)
    assert ctx, "Group 3의 StyleContext가 없습니다"
    print(f"  StyleProfile: {ctx.profile_name}")
    print(f"  default_positive: {ctx.default_positive}")

    # Anime 프로필의 quality 태그가 scene_tags에 포함된 경우
    anime_quality_tokens = split_prompt_tokens(ctx.default_positive)
    scene_tags = anime_quality_tokens + ["1girl", "smile", "outdoors"]
    composed = builder.compose(scene_tags, style_loras=[])
    check(
        "Anime: masterpiece 포함",
        "masterpiece" in composed,
        f"prompt: {composed[:100]}...",
    )
    check(
        "Anime: best_quality 포함",
        "best_quality" in composed,
    )
    check(
        "Anime: masterpiece 중복 없음",
        composed.count("masterpiece") == 1,
        f"count={composed.count('masterpiece')}",
    )

    # ── 2. 순수 실사풍 시뮬레이션 ──
    print("\n▸ 시나리오 2: 순수 실사풍 quality 태그 (DB 프로필 미사용, 직접 주입)")
    realistic_tags = ["photorealistic", "raw_photo", "sharp_focus"]
    scene_tags_real = realistic_tags + ["1girl", "smile", "outdoors"]
    composed_real = builder.compose(scene_tags_real, style_loras=[])
    check(
        "Realistic: photorealistic 포함",
        "photorealistic" in composed_real,
        f"prompt: {composed_real[:120]}...",
    )
    check(
        "Realistic: masterpiece 미포함",
        "masterpiece" not in composed_real,
        "anime fallback이 주입되면 FAIL",
    )
    check(
        "Realistic: best_quality 미포함",
        "best_quality" not in composed_real,
    )

    # ── 3. StyleProfile 없는 경우 (빈 quality) ──
    print("\n▸ 시나리오 3: StyleProfile 없음 (quality 태그 없는 scene)")
    scene_tags_no_q = ["1girl", "smile", "outdoors"]
    composed_no_q = builder.compose(scene_tags_no_q, style_loras=[])
    check(
        "No StyleProfile: fallback masterpiece 주입",
        "masterpiece" in composed_no_q,
        f"prompt: {composed_no_q[:100]}...",
    )
    check(
        "No StyleProfile: fallback best_quality 주입",
        "best_quality" in composed_no_q,
    )

    # ── 4. MultiCharacterComposer ──
    print("\n▸ 시나리오 4: MultiCharacterComposer quality 검증")
    from models.character import Character
    from services.prompt.multi_character import MultiCharacterComposer

    char_a = db.query(Character).filter(Character.id == 8).first()  # Flat Color Girl
    char_b = db.query(Character).filter(Character.id == 12).first()  # Flat Color Boy
    if char_a and char_b:
        composer = MultiCharacterComposer(builder)

        # 4a. quality_tags 명시 전달
        mc_result = composer.compose(
            char_a,
            char_b,
            ["classroom"],
            quality_tags=["photorealistic", "raw_photo"],
        )
        check(
            "MultiChar explicit: photorealistic 포함",
            "photorealistic" in mc_result,
            f"prompt: {mc_result[:120]}...",
        )
        check(
            "MultiChar explicit: masterpiece 미포함",
            "masterpiece" not in mc_result,
        )

        # 4b. quality_tags 없이 (fallback)
        mc_fallback = composer.compose(char_a, char_b, ["classroom"])
        check(
            "MultiChar fallback: masterpiece 포함",
            "masterpiece" in mc_fallback,
        )

        # 4c. scene_tags에 quality 태그 포함 (자동 추출)
        mc_extract = composer.compose(
            char_a,
            char_b,
            ["photorealistic", "raw_photo", "classroom"],
        )
        check(
            "MultiChar extract: photorealistic 포함",
            "photorealistic" in mc_extract,
        )
        check(
            "MultiChar extract: masterpiece 미포함",
            "masterpiece" not in mc_extract,
            "scene_tags에서 quality 자동 추출",
        )
    else:
        print("  [SKIP] 캐릭터 8, 12가 DB에 없음")

    # ── 5. compose_for_reference ──
    print("\n▸ 시나리오 5: compose_for_reference quality 검증")
    if char_a:
        ref_anime = builder.compose_for_reference(char_a)
        check(
            "Reference default: masterpiece 포함 (fallback)",
            "masterpiece" in ref_anime,
            f"prompt: {ref_anime[:100]}...",
        )

        ref_real = builder.compose_for_reference(
            char_a,
            quality_tags=["photorealistic", "raw_photo"],
        )
        check(
            "Reference realistic: photorealistic 포함",
            "photorealistic" in ref_real,
            f"prompt: {ref_real[:100]}...",
        )
        check(
            "Reference realistic: masterpiece 미포함",
            "masterpiece" not in ref_real,
        )
    else:
        print("  [SKIP] 캐릭터 8이 DB에 없음")

    # ── 6. 스토리보드 438 실제 씬 ──
    print("\n▸ 시나리오 6: 스토리보드 438 실제 씬 프롬프트 재생성")
    from models.scene import Scene
    from services.image_generation_core import compose_scene_with_style
    from services.style_context import extract_style_loras

    style_loras = extract_style_loras(ctx)
    scene = db.query(Scene).filter(Scene.storyboard_id == 438, Scene.deleted_at.is_(None)).order_by(Scene.order).first()
    if scene:
        composed_438, neg_438, warns_438 = compose_scene_with_style(
            raw_prompt=scene.image_prompt or "",
            negative_prompt=scene.negative_prompt or "",
            character_id=12,
            storyboard_id=438,
            style_loras=style_loras,
            db=db,
            scene_id=scene.id,
        )
        print(f"  Scene #{scene.id} (order={scene.order})")
        print(f"  Composed: {composed_438[:150]}...")
        check(
            "SB438 씬: masterpiece 포함 (Anime 프로필)",
            "masterpiece" in composed_438,
        )
        check(
            "SB438 씬: masterpiece 1회만",
            composed_438.count("masterpiece") == 1,
            f"count={composed_438.count('masterpiece')}",
        )
        if warns_438:
            print(f"  ⚠️ Warnings: {warns_438}")
    else:
        print("  [SKIP] 스토리보드 438에 씬이 없음")

    # ── 결과 요약 ──
    db.close()
    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    failed = total - passed

    print(f"\n{'═' * 50}")
    print(f"  결과: {passed}/{total} PASS", end="")
    if failed:
        print(f", {failed} FAIL")
        for name, ok in results:
            if not ok:
                print(f"    ❌ {name}")
    else:
        print(" — 모두 통과!")
    print(f"{'═' * 50}\n")

    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
