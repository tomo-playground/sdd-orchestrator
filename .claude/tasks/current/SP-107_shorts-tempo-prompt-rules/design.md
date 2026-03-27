# SP-107 상세 설계: Shorts Tempo Prompt Rules

## 변경 대상 요약

| 대상 | 유형 | 설명 |
|------|------|------|
| LangFuse `pipeline/writer/planning` | 프롬프트 system 메시지 | Tempo Rules 블록 추가 |
| LangFuse `storyboard/default` | 프롬프트 system 메시지 | Shorts Tempo Rules 블록 추가 |
| `prompt_builders_writer.py` | 코드 수정 | `build_korean_rules_block()` 에 템포 규칙 병합 |

> **코드 변경 최소화 원칙**: 정적 규칙은 LangFuse 프롬프트에서 관리 (CLAUDE.md 원칙).
> 단, `build_korean_rules_block()`에 이미 "1문장 ≤ 15자 권장" 등 한국어 스크립트 규칙이 하드코딩되어 있음.
> 이 함수의 기존 규칙과 새 템포 규칙이 충돌하지 않도록 동기화 필요.

---

## DoD 항목별 설계

### M1. Writer Planning 프롬프트에 Tempo Rules 블록 추가

**구현 방법**
- LangFuse UI → `pipeline/writer/planning` → system 메시지 끝에 아래 블록 추가
- LangFuse API를 통한 프로그래밍 업데이트 (sdd-run 자동화용)

**추가할 텍스트**:
```
## Tempo Rules (CRITICAL for Korean Shorts)

씬당 글자 수 목표:
- Hook 씬: 6~10자 (임팩트, 한 호흡)
- 정보 씬: 11~14자 (핵심만 압축)
- 전환 씬: 4~8자 (감탄사, 연결)
- 클라이맥스 씬: 최대 18자 (예외적으로 허용)
- 14자 초과 씬은 반드시 분리 검토

씬 길이 리듬 패턴:
- 짧음(6~10자) → 보통(11~14자) 교대 반복
- 3씬 연속 같은 길이 금지
- 클라이맥스 직전 씬은 반드시 짧게(6~8자)

Hook 설계 원칙:
- 씬 1은 절대 인사/예고 금지
- 결론을 씬 1에 배치, 이유는 씬 2~3에
- 숫자 훅 / 역설 훅 / 상황 특정 훅 우선

scene_distribution 가이드 (duration별):
- 15초: intro 1, rising 2~3, climax 1, resolution 1
- 30초: intro 2, rising 4~5, climax 3, resolution 1
- 45초: intro 2, rising 6, climax 4, resolution 2
- 60초: intro 2, rising 8, climax 5, resolution 2~3
```

**동작 정의**
- Before: Writer Planning이 씬 배분/Hook을 자유롭게 결정
- After: 템포 규칙에 따라 짧은 씬 위주로 설계, Hook은 결론 선행

**엣지 케이스**
- LangFuse 미연결 시: 기존 fallback 시스템 프롬프트에 템포 규칙 없음 → graceful degradation (기존 동작 유지)
- 일본어/영어: 한국어 특화 규칙이므로 다른 언어에는 "adapt the character counts to your language" 한 줄 추가

**영향 범위**: Writer Planning 출력(hook_strategy, emotional_arc, scene_distribution)이 달라짐 → 하위 Scriptwriter에 전파

**테스트 전략**: 스토리보드 1개 재생성하여 scene_distribution과 hook_strategy 변화 확인 (수동)

**Out of Scope**: fallback 시스템 프롬프트 수정 (LangFuse 미연결은 개발 환경 전용)

---

### M2. Scriptwriter 프롬프트에 Shorts Tempo Rules 블록 추가

**구현 방법**

**방법 A (권장): `build_korean_rules_block()` 함수에 템포 규칙 통합**
- 파일: `backend/services/agent/prompt_builders_writer.py:149-184`
- 이유: 이미 "1문장 ≤ 15자 권장" (line 163), "숏폼 도파민 문법" (line 162) 등 한국어 스크립트 규칙이 이 함수에 있음
- 기존 규칙 8번 "1문장 ≤ 15자 권장" → **"1문장 ≤ 14자 권장"** 으로 조정 (템포 규칙과 동기화)
- 새 규칙 추가:

```python
# build_korean_rules_block() 반환 문자열 끝에 추가:
"  12. **쇼츠 템포 규칙 (CRITICAL)**:\n"
"     - 한 씬 = 한 문장 = 한 정보. 쉼표 나열 금지\n"
"     - \"A이고 B입니다\" → 씬 분리: \"A예요\" + \"B예요\"\n"
"     - 씬 1은 바로 Hook 또는 결론. 인사/예고 절대 금지\n"
"     - \"오늘은 ~을 알려드릴게요\", \"안녕하세요\" 삭제\n"
"     - 마지막 씬(CTA): 10자 이하, 명령형\n"
"     - 정보 씬 2~3개마다 4~6자 감탄사 씬 삽입 권장\n"
"     - 예시: \"맞아요.\", \"진짜요?\", \"근데요.\"\n"
```

**방법 B (보조): LangFuse `storyboard/default` system 메시지에도 동일 규칙 추가**
- LangFuse UI → `storyboard/default` → system 메시지에 Shorts Tempo Rules 블록 추가
- 코드 빌더와 LangFuse 프롬프트 양쪽에 있으면 규칙 강화 효과

**동작 정의**
- Before: "1문장 ≤ 15자 권장" + 씬 분리 규칙 없음
- After: "1문장 ≤ 14자 권장" + 씬 분리/Hook/CTA/감탄사 규칙 주입

**엣지 케이스**
- `language != "korean"`: 기존과 동일하게 빈 문자열 반환 → 템포 규칙 미적용
- 기존 규칙 번호(6~11)와 충돌 없도록 12번부터 시작

**영향 범위**
- `generate_script()` → `builder_vars["korean_rules_block"]` → 모든 한국어 스토리보드 생성에 영향
- 4개 structure 모두 영향: default, dialogue, narrated, confession

**테스트 전략**
- `build_korean_rules_block("korean")` 반환값에 "쇼츠 템포 규칙" 포함 확인
- `build_korean_rules_block("english")` 반환값이 빈 문자열 확인
- 스토리보드 재생성 후 씬당 글자 수 평균 감소 확인 (수동)

**Out of Scope**: dialogue/narrated_dialogue structure별 분기 처리

---

### M3. 기존 스토리보드 1개 이상 재생성하여 씬당 글자 수 감소 확인

**구현 방법**: M1 + M2 적용 후 수동 검증

**테스트 전략**: 자동화 불가. `/sdd-run` 범위에서 제외, 수동 검증으로 대체.

---

## P1 (Should) 항목

### S1. 일본어/영어 버전 Tempo Rules

- `build_korean_rules_block()`과 동일 패턴으로 `build_japanese_rules_block()`, `build_english_rules_block()` 함수 추가
- 또는 기존 함수를 `build_language_rules_block(language)` 으로 리네임하여 언어별 분기

### S2. scene_distribution 기본값 duration별 명시

- M1에서 LangFuse 프롬프트에 이미 포함 (duration별 가이드)
- 추가 코드 변경 불필요

---

## 변경 요약

```
backend/services/agent/prompt_builders_writer.py:
  build_korean_rules_block():
    - 규칙 8: "1문장 ≤ 15자" → "1문장 ≤ 14자"
    - 규칙 12 추가: 쇼츠 템포 규칙 (씬 분리, Hook 금지 패턴, CTA, 감탄사)

LangFuse UI (pipeline/writer/planning):
  - system 메시지에 Tempo Rules 블록 추가

LangFuse UI (storyboard/default):
  - system 메시지에 Shorts Tempo Rules 블록 추가
```
