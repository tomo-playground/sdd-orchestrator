"""Jinja2 템플릿 → LangFuse Prompt Management 일괄 업로드.

사용법:
    cd backend && python scripts/upload_prompts_to_langfuse.py

동작:
    1. templates/ 디렉토리의 모든 .j2 파일을 읽음
    2. A등급: chat 타입 (system + user 메시지 분리)
    3. B등급: text 타입 (가시성 전용)
    4. LangFuse API로 업로드 (production 라벨)

옵션:
    --dry-run: 업로드 없이 매핑만 출력
    --grade A: A등급만 업로드
    --grade all: 전체 업로드 (기본값)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# backend/ 를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config_pipelines import (  # noqa: E402
    CREATIVE_LEADER_MODEL,
    DIRECTOR_MODEL,
    REVIEW_MODEL,
)
from services.agent.langfuse_prompt import LANGFUSE_MANAGED_TEMPLATES  # noqa: E402

# 노드별 모델 매핑 (config_pipelines.py SSOT)
NODE_MODEL_MAP: dict[str, str] = {
    "director": DIRECTOR_MODEL,
    "director-plan": DIRECTOR_MODEL,
    "director-checkpoint": DIRECTOR_MODEL,
    "director-evaluate": DIRECTOR_MODEL,
    "review-unified": REVIEW_MODEL,
    "review-evaluate": REVIEW_MODEL,
    "review-reflection": REVIEW_MODEL,
    "narrative-review": REVIEW_MODEL,
    "concept-architect": CREATIVE_LEADER_MODEL,
}
DEFAULT_MODEL = "gemini-2.5-flash"

MANAGED_PATHS: set[str] = set(LANGFUSE_MANAGED_TEMPLATES)

# A등급 프롬프트의 system_instruction (노드 하드코딩에서 추출)
# 빈 문자열 = 역할이 템플릿에 내장 (system 메시지 없이 업로드)
SYSTEM_INSTRUCTIONS: dict[str, str] = {
    "location-planner": (
        "You are a Location Planner for short-form video scripts. "
        "Output only valid JSON with the locations array. No explanations."
    ),
    "material-analyst": (
        "You are a content analyst for short-form video production. "
        "Analyze reference materials and extract key insights."
    ),
    "scene-expand": (
        "You are a scene expansion specialist for short-form video scripts. "
        "Generate new scenes that seamlessly integrate with existing ones."
    ),
    "narrative-review": "You are a narrative quality evaluator specializing in short-form video storytelling.",
    "review-reflection": "You are a self-reflection agent that analyzes review failures and proposes fix strategies.",
    "review-evaluate": "You are a script quality evaluator for short-form video scenes.",
    "edit-scenes": (
        "You are a scene editor for short-form video scripts. "
        "Edit scenes according to the given instruction while preserving overall narrative coherence."
    ),
    "validate-image-tags": "You are an image analysis expert specializing in anime/illustration art.",
    # Preset-based (DB 우선, 이 값은 fallback/문서용)
    "concept-architect": "You are a Story Architect. Create compelling concepts for short-form videos. Respond only in valid JSON.",
    "reference-analyst": "You are a Reference Analyst. Analyze content patterns. Respond only in valid JSON.",
    "devils-advocate": "You are a Devil's Advocate. Criticize sharply but constructively. Respond only in valid JSON.",
    # 역할이 템플릿에 내장 (system 메시지 없음)
    "analyze-topic": "",
    "sound-designer": "",
    "copyright-reviewer": "",
    # --- B등급 Phase 2: include 없는 복잡 로직 ---
    "director": (
        "You are the Production Director using the ReAct Loop framework. "
        "Follow the Observe → Think → Act process. 모든 텍스트는 한국어로 작성. Respond only in valid JSON."
    ),
    "scriptwriter": (
        "You are an expert Scriptwriter for short-form video content. "
        "Convert concepts into scene-by-scene scripts with natural dialogue. Respond only in valid JSON."
    ),
    "director-plan": (
        "You are the Creative Director for a short-form video project. "
        "Establish creative direction, casting, and execution plan. 모든 텍스트는 한국어로 작성. Respond only in valid JSON."
    ),
    "writer-planning": (
        "You are a Script Planning Specialist. "
        "Create hook strategies, emotional arcs, scene distributions, and location maps. Respond only in valid JSON."
    ),
    "tts-designer": (
        "You are a TTS Designer for short-form video. "
        "Design emotional tonality and vocal expression for each scene. Respond only in valid JSON."
    ),
    "director-checkpoint": (
        "You are the Creative Director reviewing a script before production. "
        "Evaluate whether the script meets the creative direction. 모든 텍스트는 한국어로 작성. Respond only in valid JSON."
    ),
    "explain": (
        "You are a Creative Director explaining production decisions. "
        "Analyze all production results and explain creative choices. 모든 설명은 한국어로 작성. Respond only in valid JSON."
    ),
    "director-evaluate": (
        "You are a Creative Director evaluating concept proposals. "
        "Score each concept on hook, arc, feasibility, and originality. All text in Korean. Respond only in valid JSON."
    ),
    "review-unified": (
        "You are a unified review agent that evaluates technical quality, narrative strength, "
        "and self-reflection for short-form video scripts. Respond only in valid JSON."
    ),
    # --- include 제거 완료 (파셜→변수 전환) ---
    "cinematographer": (
        "You are a Cinematographer specializing in AI-generated visual design. "
        "Add Danbooru tags, camera angles, and environment to each scene. Respond only in valid JSON."
    ),
    "create-storyboard": (
        "You are a short-form video storyboarder. "
        "Generate scene-by-scene scripts with image prompts in Danbooru tag format. Respond only in valid JSON."
    ),
    "create-storyboard-confession": (
        "You are a short-form video storyboarder specializing in confession/lesson narratives. "
        "Generate scene-by-scene scripts with image prompts. Respond only in valid JSON."
    ),
    "create-storyboard-dialogue": (
        "You are a short-form video storyboarder specializing in two-character dialogue. "
        "Generate scene-by-scene scripts with image prompts. Respond only in valid JSON."
    ),
    "create-storyboard-narrated": (
        "You are a short-form video storyboarder specializing in narrated dialogue. "
        "Generate scene-by-scene scripts with Narrator + A/B speakers. Respond only in valid JSON."
    ),
}


def to_langfuse_name(template_path: str) -> str:
    """템플릿 경로 → LangFuse 프롬프트 이름."""
    name = template_path
    if name.startswith("creative/"):
        name = name[len("creative/") :]
    if name.startswith("_partials/"):
        name = "partial-" + name[len("_partials/") :]
    name = name.removesuffix(".j2")
    return name.replace("_", "-")


def _build_prompt_payload(lf_name: str, content: str, is_managed: bool) -> tuple[list | str, str]:
    """(prompt_data, type) 튜플을 반환한다.

    A등급: chat 타입 [system, user] / B등급: text 타입.
    """
    if not is_managed:
        return content, "text"

    sys_text = SYSTEM_INSTRUCTIONS.get(lf_name, "")
    messages: list[dict[str, str]] = []
    if sys_text:
        messages.append({"role": "system", "content": sys_text})
    messages.append({"role": "user", "content": content})
    return messages, "chat"


def collect_templates(templates_dir: Path, grade: str) -> list[tuple[str, str, str]]:
    """(relative_path, langfuse_name, content) 리스트를 반환한다."""
    results = []
    for j2_file in sorted(templates_dir.rglob("*.j2")):
        rel = str(j2_file.relative_to(templates_dir))
        if grade == "A" and rel not in MANAGED_PATHS:
            continue
        lf_name = to_langfuse_name(rel)
        content = j2_file.read_text(encoding="utf-8")
        results.append((rel, lf_name, content))
    return results


def upload(dry_run: bool = False, grade: str = "all") -> None:
    """LangFuse에 프롬프트를 업로드한다."""
    templates_dir = Path(__file__).resolve().parent.parent / "templates"
    if not templates_dir.exists():
        print(f"[ERROR] templates 디렉토리 없음: {templates_dir}")
        sys.exit(1)

    templates = collect_templates(templates_dir, grade)
    print(f"\n{'=' * 60}")
    print(f"  LangFuse Prompt Upload — {len(templates)}개 템플릿 ({grade}등급)")
    print(f"{'=' * 60}\n")

    for rel, lf_name, content in templates:
        model = NODE_MODEL_MAP.get(lf_name, DEFAULT_MODEL)
        is_a = rel in MANAGED_PATHS
        grade_label = "M" if is_a else "F"
        ptype = "chat" if is_a else "text"
        sys_text = SYSTEM_INSTRUCTIONS.get(lf_name, "")
        sys_info = f" sys={len(sys_text)}자" if sys_text else ""
        lines = content.count("\n") + 1
        print(f"  [{grade_label}:{ptype:4s}] {rel:45s} → {lf_name:30s} ({lines}줄{sys_info}, model={model})")

    if dry_run:
        print(f"\n  [DRY-RUN] 총 {len(templates)}개 — 업로드 건너뜀\n")
        return

    from langfuse import Langfuse

    lf = Langfuse()

    uploaded = 0
    skipped = 0
    errors = 0

    for rel, lf_name, content in templates:
        model = NODE_MODEL_MAP.get(lf_name, DEFAULT_MODEL)
        is_a = rel in MANAGED_PATHS
        prompt_data, prompt_type = _build_prompt_payload(lf_name, content, is_a)
        try:
            lf.create_prompt(
                name=lf_name,
                prompt=prompt_data,
                labels=["production"],
                config={"model": model},
                type=prompt_type,
            )
            uploaded += 1
            print(f"  ✓ {lf_name} ({prompt_type})")
        except Exception as e:
            err_str = str(e)
            if "already exists" in err_str.lower():
                skipped += 1
                print(f"  - {lf_name} (이미 존재)")
            else:
                errors += 1
                print(f"  ✗ {lf_name}: {err_str[:100]}")

    lf.flush()
    print(f"\n  결과: 업로드 {uploaded} / 스킵 {skipped} / 에러 {errors}\n")


def main():
    parser = argparse.ArgumentParser(description="Jinja2 → LangFuse Prompt 업로드")
    parser.add_argument("--dry-run", action="store_true", help="업로드 없이 매핑만 출력")
    parser.add_argument("--grade", choices=["A", "all"], default="all", help="업로드 대상 등급")
    args = parser.parse_args()
    upload(dry_run=args.dry_run, grade=args.grade)


if __name__ == "__main__":
    main()
