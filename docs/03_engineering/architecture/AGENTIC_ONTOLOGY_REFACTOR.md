# 🎬 Agentic 파이프라인 연출 온톨로지 고도화 (Refactoring Guide)

**목적**: LLM 프롬프트에 과적된 자연어 매핑 규칙(Rule)을 파이썬 코드 기반 결정론적(Deterministic) 온톨로지로 분리  
**대상자**: Claude (개발/구현 참조용)  
**상태**: Draft / 제안 단계

---

## 1. 문제 정의 (As-Is의 한계)

현재 `backend/templates/creative/cinematographer.j2`를 비롯한 주요 프롬프트 템플릿은 지나치게 방대한 제약 조건("금지어", "Danbooru 태그 규칙", "감정-카메라 강제 매핑")을 자연어로 안고 있습니다.

1. **환각 리스크와 방어 코드 양산**: LLM은 본질적으로 확률 모델이므로, `cinematic_shadows` 같은 금지된 태그를 100% 안 쓴다는 보장이 없습니다. 이를 막기 위해 백엔드에서 다시 정규표현식과 Validation 과정을 거치며 수많은 방어 코드가 양산되고 있습니다.
2. **"Agentic" 철학과의 어긋남**: Agentic AI는 에이전트(LLM)가 상위 수준의 의도(Intent)를 추론하고 시스템(Tool/Code)이 구체적인 행동(Action)을 매핑할 때 가장 강력합니다. 현재는 에이전트에게 250줄짜리 단순 타이핑(문법 검사기 역할)을 강제하고 있습니다.
3. **비용 및 지연 시간 (Latency)**: 긴 프롬프트와 반복적인 응답 스키마 제어는 불필요한 토큰 체류와 속도 저하를 유발합니다.

---

## 2. 해결 방향 (To-Be 아키텍처)

- **추론(LLM의 영역)**: LLM은 대본의 전체 맥락, 기승전결(Narrative Role), 캐릭터의 내면 **감정(Emotion)과 의도를 좁혀진 범주(Enum) 안에서 분류/추출하는 역할**만 수행합니다.
- **실행(온톨로지 엔진의 영역)**: 파이썬 기반 시스템이 LLM이 반환한 `(Emotion: sad, Role: climax)` 같은 구조화된 데이터를 받아 **미리 정의된 완벽한 SDXL/Danbooru 태그 세트와 카메라 워킹(Ken Burns)으로 100% 무결점 변환**합니다.

> 💡 **진행 현황 (2026-02-27 업데이트)**:
> 1단계로 파이프라인의 후처리 노드(`Finalize Node`) 쪽에 강력한 백엔드 규칙을 신설했습니다.
> - **Tag Alias 자동 변환**: DB의 `tag_aliases` 테이블을 연동하여 LLM이 `holding_object`나 `wide-eyed` 같은 비표준/모호한 태그를 생성해도 백엔드가 자동으로 교정(또는 제거)합니다.
> - **프롬프트 충돌 감지/제거**: 새로운 `_prompt_conflict_resolver.py` 모듈이 Positive 안의 모순 태그(예: day vs night)와 Positive↔Negative 간의 충돌을 감지하여 안전하게 클렌징합니다.
> - **Tag 중복 제거 헬퍼**: `merge_tags_dedup()`을 통해 LLM 응답 후 중구난방이던 콤마(,)와 여백, 대소문자를 일관되게 정규화합니다.

이러한 후처리 엔진(Ontology Validation)이 완성되었으므로, 이제 앞 단의 **프롬프트 생성(LLM) 단계의 규제를 대폭 풀어주는 작업(비효율 제거)**이 다음 스텝입니다.
---

## 3. 구현 단계 가이드 (Action Items for Claude)

Claude가 이 문서를 읽고 바로 개발에 들어갈 수 있도록 단계별 목표를 명세합니다.

### 📌 Step 1: Pydantic 스키마 및 Enum 정의 (Structured Outputs 강제)
LLM이 반환해야 할 '핵심 정보'를 Enum으로 제한하여 묶어버립니다. (예: `schemas/creative.py` 등)
```python
from enum import Enum
from pydantic import BaseModel, Field

class SceneEmotion(str, Enum):
    happy = "happy"
    sad = "sad"
    tension = "tension"
    # ... 허용된 감정 30개로 고정

class NarrativeRole(str, Enum):
    hook = "hook"
    rising = "rising"
    climax = "climax"
    resolution = "resolution"

class CinematographerResponse(BaseModel):
    emotion_intent: SceneEmotion = Field(...)
    narrative_role: NarrativeRole = Field(...)
    core_action_object: str | None = Field(description="예: phone, book 등 핵심 사물(단일 태그)")
```

### 📌 Step 2: 연출 온톨로지 파이썬 모듈 신설 (`cinematography_ontology.py`)
LLM이 반환한 `(emotion_intent, narrative_role)` 조합을 실제 카메라 스펙과 이미지 프롬프트로 100% 매핑해주는 엔진을 작성합니다.
- **위치 제안**: `backend/services/creative/cinematography_ontology.py`
```python
ONTOLOGY_MAPPING = {
    "emotion": {
        "sad": {
            "camera_angles": ["from_above", "wide_shot"],
            "lighting": ["depth_of_field", "low_key"],
            "ken_burns": "zoom_out_center",
            "base_tags": "looking_down"
        },
        "tension": {
            # ...
        }
    },
    "narrative": {
        "hook": {"camera_angles": ["dutch_angle"], "weights": ...}
    }
}

class CinematographyOntology:
    @classmethod
    def build_scene_visuals(cls, intent: CinematographerResponse, environment: str) -> dict:
        # 1. intent.emotion_intent를 기반으로 ONTOLOGY_MAPPING에서 최적의 구도 확보
        # 2. image_prompt_ko 자동 생성 및 조립
        # 3. Danbooru 태그 조합 및 리턴 (에러 확률 0%)
        pass
```

### 📌 Step 3: `cinematographer.j2` 프롬프트 대폭 축소 (다이어트)
불필요한 자연어 규칙을 모두 날립니다. 최근 업데이트에서 `holding_object` 통제 등 일부 규칙이 개선되었으나, 여전히 감정과 카메라의 1:1 매핑 규칙이 길게 적혀있습니다.

**[기존 250줄짜리 프롬프트 예시]**
- *"카메라는 3가지 섞고.. 화난 감정엔 from_below 쓰고.. Danbooru 태그만 쓰고.. ❌ 절대 이런 태그 쓰지 마 ❌"* (대부분 삭제 요망)
  -> *사유: DB `tag_aliases`와 `_prompt_conflict_resolver.py`가 이미 백엔드에서 훌륭하게 잡아내고 있으므로 LLM에게 구구절절 설명할 필요가 없어졌습니다.*

**[새로운 프롬프트 방향성 (경량화)]**
- *"너는 감독관이다. 주어진 씬의 대본을 읽고 가장 알맞은 분위기(emotion_intent)와 주요 행위 객체(core_action_object)만 지정된 JSON Schema 대로 반환해라."*

### 📌 Step 4: 파이프라인(Agent/Node) 코드 연결
`backend/services/creative/cinematographer_node.py` (또는 관련 LangGraph 노드)를 업데이트하여 다음의 파이프라인(Chain)이 흐르도록 만듭니다.

1. `LLM (Gemini)` $\rightarrow$ `Pydantic (CinematographerResponse)` 리턴
2. `CinematographyOntology.build_scene_visuals(response)` $\rightarrow$ 최종 씬 데이터(프롬프트, 태그 등) 확정
3. `State`에 반영 및 다음 노드로 전달

---

## 4. 리뷰 및 점검 포인트 (DoD)
- [ ] `cinematographer.j2`의 프레임워크가 100줄 이내로 대폭 축소되었는가?
- [ ] 구조화된 Schema(Pydantic)를 통해 LLM이 환각 태그를 뱉을 수 있는 공간 자체가 차단되었는가?
- [ ] 과거 `cinematographer.j2`에 있던 [Gaze-Pose 연관 규칙, Emotion-Camera 연관 규칙]들이 파이썬 로직(`cinematography_ontology.py`) 으로 누락 없이 이전되었는가?
