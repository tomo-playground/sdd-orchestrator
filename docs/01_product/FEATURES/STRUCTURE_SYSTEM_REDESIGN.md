# Structure 시스템 재설계 — 다양한 영상 구조 지원

> 작성: 2026-03-22 | 상태: **설계 완료**
> 선행 조건: 없음 (SP-020, SP-021보다 먼저 착수)
> 후속: SP-021 (Speaker 동적 역할)은 이 작업 완료 후 착수

---

## 1. 배경

### 현재 문제

파이프라인이 **모놀로그 형태로만** 작품을 생성한다.

- `DEFAULT_STRUCTURE = "monologue"` → 사용자가 명시 선택하지 않으면 항상 모놀로그
- Chat UI(메인 흐름)에 structure 선택 UI가 없음
- Director Plan이 dialogue를 추천해도 `character_b_id` 없으면 조용히 monologue로 강등
- `scene_mode="multi"` (2인 동시 출연) = Dead Code (DB 0건)
- Auto/Guided/FastTrack 3모드의 실질적 차이 불명확

### 근본 원인

각 structure의 **"완성된 영상이 어떻게 달라야 하는지"** 제품 명세가 없다. 코드에 4가지 structure가 정의되어 있지만, 사용자가 접근할 경로가 없고, 파이프라인 분기가 불완전하다.

---

## 2. 설계 원칙

### 2-1. Structure와 Tone 분리

**Structure** = 파이프라인이 다르게 동작하는 분기점 (speaker 수, 캐릭터 배정, TTS 분기, 이미지 구성)
**Tone** = 프롬프트의 톤/분위기 (LangFuse 프롬프트 선택에 영향)

```
structure (파이프라인 분기)        tone (프롬프트 톤)
├── monologue (독백)              ├── intimate (담담)
├── dialogue (대화형)             ├── emotional (감정적)
└── narrated_dialogue (나레이션)   ├── dynamic (역동적)
                                  ├── humorous (유머)
                                  └── suspense (서스펜스)
```

- 기존 `confession` structure → 제거. `monologue + emotional` 조합으로 대체
- 조합 가능: `dialogue + humorous` = 코미디 대화, `narrated_dialogue + suspense` = 공포 나레이션
- tone 목록은 확장 가능 (LangFuse 프롬프트 추가로 대응)

### 2-2. 소크라테스 질문 방식 (Concept First)

사용자가 structure 용어를 몰라도 된다. **자연어 의도 → 시스템이 최적 structure 매칭.**

시스템이 만들 수 있는 것(3가지 structure)은 고정. 질문으로 사용자의 의도를 파악하여 고정된 선택지 중 최적을 도출한다.

### 2-3. 모드 단순화

| 모드 | 역할 |
|------|------|
| **Guided** | Intake 질문 + 모든 노드 실행 + 반복(Critic 핑퐁, Director 검수) + 사용자 승인 게이트 |
| **FastTrack** | 기본값 사용 + 모든 노드 실행하되 **반복 1회로 제한** + 자동 승인 |

- **Auto 모드 폐지** — 현재 FastTrack과 실질적 차이 없음
- Auto의 미래 방향(트렌드 기반 자율 생성)은 별도 FEATURES 명세로 분리

---

## 3. Structure 정의 (3종)

### 3-1. Monologue (독백)

| 항목 | 사양 |
|------|------|
| Speaker | A (1명) |
| 캐릭터 | 1명 |
| 씬 구성 | 모든 씬에 동일 캐릭터 |
| TTS | 단일 음성 |
| scene_mode | 항상 "single" |
| 용도 | 독백, 에세이, 고백, 교훈, 일기 |

### 3-2. Dialogue (대화형)

| 항목 | 사양 |
|------|------|
| Speaker | A, B (2명) |
| 캐릭터 | 2명 필수 |
| 씬 구성 | A/B 교대 (각 30% 이상). 핵심 장면에서 scene_mode="multi" (2인 동시 출연, 최대 1-2씬) |
| TTS | Speaker별 다른 음성 (character voice_preset) |
| scene_mode | "single" (교대 컷) + "multi" (2인 동시 출연) |
| 용도 | 대화, 논쟁, 인터뷰, 코미디 |

### 3-3. Narrated Dialogue (나레이션 대화)

| 항목 | 사양 |
|------|------|
| Speaker | Narrator, A, B (3명) |
| 캐릭터 | 2명 필수 + Narrator (Group의 narrator_voice_preset) |
| 씬 구성 | ~1/3 Narrator + ~1/3 A + ~1/3 B. Narrator가 도입/마무리 담당 |
| TTS | Narrator=Group voice preset, A/B=Character voice preset |
| scene_mode | Narrator 씬은 "single" (배경/분위기), A/B 씬은 교대 + "multi" 가능 |
| 용도 | 드라마, 다큐, 동화, 역사 이야기 |

---

## 4. Tone 시스템

### 4-1. 정의

Tone은 스크립트 생성 프롬프트의 분위기를 결정한다. Structure와 독립적으로 조합 가능.

| tone ID | 한국어 | 설명 | LangFuse 프롬프트 영향 |
|---------|--------|------|----------------------|
| `intimate` | 담담 | 차분하고 내면적인 이야기 | 기본 톤 |
| `emotional` | 감정적 | 고백, 눈물, 깊은 감정 | 기존 confession 프롬프트 흡수 |
| `dynamic` | 역동적 | 빠른 전개, 긴장감 | 짧은 씬, 빠른 전환 |
| `humorous` | 유머 | 웃긴 상황, 가벼운 톤 | 코미디 연출 |
| `suspense` | 서스펜스 | 공포, 미스터리, 긴장 | 어두운 분위기, 반전 |

### 4-2. 적용 방식

- Intake 질문에서 tone을 파악하거나 사용자가 직접 선택
- Writer 노드에서 structure별 LangFuse 프롬프트 + tone 변수를 함께 주입
- 기존 `StructureMeta.tone` 필드 → DB 저장 가능한 사용자 선택 옵션으로 전환

---

## 5. Intake 노드 (소크라테스 질문)

### 5-1. 위치

```
[Intake] → structure/tone/캐릭터 확정
    ↓
[Director Plan] → 확정된 정보 기반 실행 계획 수립
    ↓
[Director Plan Gate] → 사용자 승인
    ↓
[Writer] → ...
```

- Director Plan **앞에** 별도 노드로 추가
- Guided 모드 전용. FastTrack에서는 건너뜀

### 5-2. 질문 흐름 (결정 트리)

```
사용자: "학교 괴담 영상 만들어줘"

Intake Q1: "어떤 형태의 영상을 상상하고 계세요?"
    - 한 명이 이야기를 들려주는 느낌?
    - 두 캐릭터가 대화하는 느낌?
    - 나레이터가 설명하면서 캐릭터가 대사하는 느낌?

→ "두 명이 대화" 선택 시:

Intake Q2: "어떤 분위기를 원하세요?"
    - 긴장감 있는 공포?
    - 가벼운 유머?
    - 감정적인 드라마?

→ "공포" 선택 시:

Intake Q3: "캐릭터를 골라볼까요?" (시리즈 캐릭터 목록 제시)
    - 미도리 (여, 활발)
    - 하루 (남, 차분)
    - 새로 만들기

→ 최종 확인:
    - 주제: 학교 괴담
    - 구조: 대화형 (미도리 ↔ 하루)
    - 분위기: 서스펜스
    "시나리오를 만들어볼까요?"
```

### 5-3. 구현 방식

- LangGraph 노드 + `interrupt()` 루프
- 한 노드 안에서 질문 → 답변 → 다음 질문을 반복 (충분한 정보가 모이면 탈출)
- LLM이 사용자 답변을 분석하여 결정 트리를 좁혀감
- 이미 토픽에서 의도가 명확하면 ("두 사람이 싸우는 이야기") 질문 축소 가능

### 5-4. 출력

```python
# Intake 노드 → state에 저장
{
    "structure": "dialogue",        # 확정된 structure
    "tone": "suspense",             # 확정된 tone
    "character_id": 5,              # Speaker A 캐릭터
    "character_b_id": 8,            # Speaker B 캐릭터
    "intake_summary": "학교 괴담, 대화형, 서스펜스, 미도리↔하루"
}
```

---

## 6. 모드별 파이프라인 동작

### 6-1. Guided 모드

| 노드 | 동작 |
|------|------|
| **Intake** | 소크라테스 질문으로 structure/tone/캐릭터 확정 |
| Director Plan | 실행 + 사용자 승인 |
| Research | 실행 |
| Writer | 실행 |
| Critic | 피드백 → 수정 → 재검토 (N회 반복) |
| Cinematographer 팀 | 4 에이전트 실행 |
| Director 검수 | 피드백 → 재촬영 (N회 반복) |
| TTS Designer | 실행 |

### 6-2. FastTrack 모드

| 노드 | 동작 |
|------|------|
| **Intake** | 건너뜀 (기본값: monologue + intimate) |
| Director Plan | 실행 + 자동 승인 |
| Research | 실행 |
| Writer | 실행 |
| Critic | **1회 검토 → 바로 승인** |
| Cinematographer 팀 | 4 에이전트 실행 |
| Director 검수 | **1회 → 바로 승인** |
| TTS Designer | 실행 |

**FastTrack 원칙**: 모든 노드를 실행하되, 반복(iteration)이 있는 곳은 1회로 끊고 다음으로 진행.

---

## 7. 2인 동시 출연 씬 (scene_mode="multi") 활성화

### 7-1. 현재 상태

- `MultiCharacterComposer` (BREAK 토큰 2인 합성) 완전 구현됨
- Finalize의 `_validate_scene_modes()`, `_auto_populate_scene_flags()` 완전 구현됨
- 실제 사용 0건 (DB에 scene_mode="multi" 없음)

### 7-2. 활성화 방안

1. **Cinematographer 프롬프트 강화** — `scene_mode: "multi"` 출력 빈도를 높임 (핵심 감정 장면에서 1-2씬)
2. **Finalize 보정 완화** — multi → single 강제 전환 조건을 완화
3. **ControlNet/IP-Adapter 비활성화 유지** — multi 씬은 LoRA+BREAK만으로 생성
4. **품질 모니터링** — 캐릭터 일관성 저하 시 ComfyUI 전환(SP-022/023) 후 개선

### 7-3. 제약

- multi 씬은 스토리보드당 최대 1-2개로 제한
- Narrator 씬은 multi 불가 (의미 모순)
- monologue structure에서는 multi 불가

---

## 8. 화자 표시

대화형 영상에서 시청자는 **이미지 전환 + TTS 음성 전환**으로 화자를 인식한다. 별도 이름 태그나 말풍선 오버레이는 추가하지 않는다.

---

## 9. confession 마이그레이션

### 9-1. DB 마이그레이션

```sql
-- storyboards.structure = 'confession' → 'monologue' 전환
UPDATE storyboards SET structure = 'monologue' WHERE structure = 'confession';
```

### 9-2. tone 필드 추가

- `storyboards` 테이블에 `tone: String(30), default="intimate"` 필드 추가
- 기존 confession 스토리보드는 `tone = 'emotional'`로 설정

### 9-3. LangFuse 프롬프트

- `storyboard/confession` 템플릿 → `storyboard/monologue` + `tone=emotional` 조건으로 흡수
- 프롬프트 내용 자체는 보존 (감정적 톤 특화 지시문)

### 9-4. 코드 정리

- `config.py`: `StructureMeta`에서 confession 제거, tone 옵션 목록 추가
- `presets.py`: confession 프리셋 → monologue + emotional 매핑으로 전환
- `coerce_structure_id()`: `"confession"` 입력 시 `"monologue"` 반환 (하위 호환)
- 테스트: confession 케이스를 monologue + emotional로 갱신

---

## 10. interaction_mode 정리

### 10-1. 변경

| 기존 | 변경 후 | 비고 |
|------|---------|------|
| `"guided"` | `"guided"` | 유지 |
| `"auto"` | `"fast_track"` | rename |
| `"hands_on"` | 제거 | 이미 폐기 상태 |

### 10-2. 하위 호환

- `coerce_interaction_mode()` 함수 추가: `"auto"` → `"fast_track"`, `"hands_on"` → `"guided"` 매핑
- DB/localStorage에 저장된 기존 값 자동 변환

---

## 11. 태스크 분할 (권장)

| 태스크 | 범위 | 선행 |
|--------|------|------|
| **A** | confession 제거 + tone 필드 추가 + DB 마이그레이션 + 코드/테스트 정리 | 없음 |
| **B** | interaction_mode rename (auto → fast_track) + FastTrack 반복 1회 제한 로직 | 없음 |
| **C** | Intake 노드 구현 (Guided 모드 소크라테스 질문) | A 완료 후 |
| **D** | scene_mode="multi" 활성화 (프롬프트 강화 + Finalize 완화) | 없음 |

A와 B는 독립 병렬 가능. C는 A 완료 후 착수. D는 독립.

---

## 12. 후속 연계

| 태스크 | 관계 |
|--------|------|
| SP-020 (Enum ID 정규화) | confession 제거로 structure enum 단순화 → 시너지 |
| SP-021 (Speaker 동적 역할) | Structure 재설계 완료 후 착수 (선행 조건) |
| SP-046 (Cinematographer 팀 분해) | multi 씬 활성화와 연계 가능 |
| SP-022/023 (ComfyUI + 캐릭터 일관성 V3) | multi 씬 품질 개선 후속 |
| Auto 모드 트렌드 기반 자율 생성 | 별도 FEATURES 명세로 분리 (미착수) |
