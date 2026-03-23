# SP-061 상세 설계: 대사 품질 통합 체크 (Review L2)

## 개요

대사 품질 검증을 **2개 위치**에 분산 배치한다:
- **Review 노드** (`_review_validators.py`): script/speaker만 사용하는 검증 (A-2, A-3, B-1, B-2)
- **Finalize 노드** (`finalize.py`): `context_tags.emotion` 의존 검증 (A-1)

이유: Review는 Writer 직후에 실행되어 `context_tags`가 아직 없다. `context_tags.emotion`은 Cinematographer가 생성하므로, emotion 기반 검증은 Cinematographer 이후인 Finalize에서 실행한다.

모든 검증은 순수 함수(Gemini 호출 없음, DB 접근 없음)이다.

---

## DoD A-1: 감정 중복 연속 → **Finalize 노드에 배치**

### 구현 방법
- `finalize.py`에 `_validate_emotion_continuity(scenes: list[dict]) -> None` 함수를 추가한다.
- 각 speaker별로 연속 씬을 순회하며 `context_tags.emotion` 값을 비교한다.
- emotion 값은 `str | list[str]` 가능 (Gemini 배열 응답 방어 — 커밋 3159ffeb 참조). `_coerce_str()` 헬퍼로 정규화한다.
- 감정 중복 감지 시 WARNING 로그를 출력한다 (Finalize는 errors/warnings를 ReviewResult에 추가하지 않으므로 로그 + state에 `finalize_warnings` 기록).
- 실행 위치: `finalize_node()` 그룹 2 끝 (`_inject_writer_plan_emotions()` 이후, emotion 값이 확정된 시점).

### 동작 정의
1. scenes를 순서대로 순회하면서 speaker별 연속 emotion 시퀀스를 추적한다.
2. 동일 speaker가 연속 2씬 이상 동일 emotion → WARNING 로그: `"[Finalize] 씬 {start}~{end}: {speaker}의 감정 '{emotion}'이 {count}씬 연속 중복"`
3. 동일 speaker가 연속 3씬 이상 → 추가로 `logger.error` 레벨 로그 (렌더링은 차단하지 않음)
4. emotion이 비어있거나 None인 씬은 연속 카운트를 끊는다.

### 엣지 케이스
- context_tags 자체가 None/없는 씬 → 연속 카운트 리셋
- emotion이 list인 경우 → 첫 번째 요소만 사용
- speaker가 "Narrator"인 씬도 동일 로직 적용
- 전체 씬이 1개인 경우 → 검출 없음

### 영향 범위
- `finalize.py` (함수 추가 + 호출 1줄)
- SP-062와 동일 파일이지만 다른 함수 — 머지 충돌 없음

### 테스트 전략
- 2씬 연속 동일 emotion → WARNING 로그 발생 확인
- 3씬 연속 동일 emotion → ERROR 로그 발생 확인
- emotion 중간에 다른 emotion → 리셋 확인
- emotion이 None인 씬이 끼어있을 때 → 연속 끊김 확인
- emotion이 list인 경우 → 정상 비교 확인

### Out of Scope
- emotion 허용값 검증 (SP-062 범위)
- Review 시점에서의 emotion 검증 (context_tags 미존재)
- Revise 루프 연동 (Finalize는 최종 단계이므로 Revise로 되돌리지 않음 — 로그 기록만)

---

## DoD A-2: Speaker 교번 단절

### 구현 방법
- `validate_dialogue_quality()` 내에서 speaker 연속 카운트를 추적한다.
- `structure`가 `"monologue"` 또는 `"narrated_dialogue"`이면 이 검증을 건너뛴다.
  - monologue: 본래 단일 speaker
  - narrated_dialogue: Narrator 연속이 자연스러운 구조

### 동작 정의
1. scenes를 순서대로 순회하면서 이전 씬의 speaker와 비교한다.
2. 동일 speaker가 3씬 이상 연속이면 WARNING: `"씬 {start}~{end}: {speaker}가 {count}씬 연속 독백 — 대화 교번 필요"`
3. structure가 `"dialogue"`일 때만 적용한다.

### 엣지 케이스
- speaker가 None/빈 문자열인 씬 → 연속 카운트 리셋
- Narrator 씬이 A/B 사이에 끼어있을 때 → A-Narrator-A는 A 연속 아님 (Narrator가 끊음)
- 전체 씬이 2개 이하 → 3씬 연속 불가능이므로 검출 없음

### 영향 범위
- `_review_validators.py` (같은 함수 내)

### 테스트 전략
- dialogue 구조에서 A가 3씬 연속 → WARNING
- dialogue 구조에서 A가 2씬 연속 → WARNING 없음
- monologue 구조 → 검증 건너뜀 확인
- narrated_dialogue 구조 → 검증 건너뜀 확인
- Narrator가 사이에 끼어서 A 연속이 끊기는 케이스

### Out of Scope
- Speaker 비율 검증 (이미 `validate_scenes()`에 존재)

---

## DoD A-3: 인접 씬 스크립트 유사도

### 구현 방법
- `_jaccard_similarity(text_a, text_b)` 헬퍼 함수를 추가한다.
- 한국어 토큰화: 공백 기준 split (형태소 분석기 사용 안 함 — 외부 의존성 추가 금지).
- 인접 2씬의 script를 비교하여 Jaccard 유사도 계산.

### 동작 정의
1. `_jaccard_similarity(a, b)`: 각 문자열을 공백으로 split하여 토큰 셋 생성 → `|A ∩ B| / |A ∪ B|` 반환.
2. scenes를 순서대로 순회하며 `scenes[i].script`와 `scenes[i+1].script`를 비교한다.
3. Jaccard 유사도 >= 0.7이면 WARNING: `"씬 {i+1}~{i+2}: 스크립트 유사도 {sim:.0%} — 대사 차별화 필요"`
4. 빈 script(None/"") 쌍은 건너뛴다.

### 엣지 케이스
- 한쪽 script가 None/빈 문자열 → 비교 건너뜀
- 양쪽 모두 빈 문자열 → 건너뜀 (빈 스크립트는 이미 A-1의 `_validate_single_scene`에서 ERROR)
- 단어 1~2개만 있는 초단문 → Jaccard가 쉽게 1.0 나올 수 있지만, 짧은 스크립트 자체가 이미 WARNING 대상이므로 중복 경고 수용
- 토큰이 0개인 경우 (공백만 등) → 유사도 0.0 반환 (division by zero 방어)

### 영향 범위
- `_review_validators.py` (헬퍼 함수 + 호출)

### 테스트 전략
- 동일 스크립트 → 유사도 1.0 → WARNING
- 완전히 다른 스크립트 → 유사도 < 0.7 → WARNING 없음
- 70% 경계값 테스트 (정확히 0.7 → WARNING)
- 빈 스크립트 쌍 → 건너뜀 확인
- `_jaccard_similarity` 단위 테스트 (순수 함수)

### Out of Scope
- 형태소 분석기 기반 토큰화 (외부 의존성 추가 필요)
- 비인접 씬 간 유사도 (n-gram window)

---

## DoD B-1: 클리셰 감지

### 구현 방법
- `config.py`에 `DIALOGUE_CLICHE_PATTERNS: list[str]` 상수를 추가한다.
- 정규식 패턴 리스트 (한국어 쇼츠 대본 클리셰).
- `re.search(pattern, script)` 로 매칭하여 씬당 매칭 개수를 카운트한다.

### 동작 정의
1. `config.py`에 초기 클리셰 패턴 정의:
   ```python
   DIALOGUE_CLICHE_PATTERNS: list[str] = [
       r"심쿵",
       r"소름\s*돋",
       r"레전드",
       r"역대급",
       r"미쳤",
       r"대박",
       r"실화",
       r"ㄹㅇ",
       r"갓",
       r"킹",
       r"찐이",
       r"어떻게\s*이런",
       r"말이\s*돼\?",
       r"세상에",
       r"헐",
   ]
   ```
2. `validate_dialogue_quality()` 내에서 각 씬의 script를 모든 패턴과 비교한다.
3. 한 씬에서 2개 이상 패턴 매칭 → WARNING: `"씬 {idx}: 클리셰 표현 {count}개 감지 ({matched}) — 독창적 표현 권장"`
4. 매칭된 패턴 이름(원본 패턴의 일부)을 WARNING 메시지에 포함하여 Revise 노드가 구체적으로 수정 가능하게 한다.

### 엣지 케이스
- script가 None/빈 → 건너뜀
- 동일 패턴이 한 씬에서 여러 번 매칭 → 1회로 카운트 (패턴 종류 기준)
- 패턴이 다른 단어 내에 포함되는 경우 (예: "심쿵" in "심쿵이야") → 의도적으로 잡음 (클리셰 자체가 문제)
- 정규식 컴파일 에러 방어 → `re.compile` 시 에러면 해당 패턴 건너뜀 + 로그 경고

### 영향 범위
- `config.py` (상수 추가)
- `_review_validators.py` (로직 추가)

### 테스트 전략
- 클리셰 2개 포함 씬 → WARNING
- 클리셰 1개 포함 씬 → WARNING 없음 (2개 이상만)
- 클리셰 0개 → WARNING 없음
- `config.py` 패턴이 유효한 정규식인지 컴파일 테스트
- 패턴 변경 시 기존 테스트 영향 없음 (테스트는 직접 패턴 사용)

### Out of Scope
- 영어 클리셰 감지 (현재 한국어 only)
- 클리셰 패턴의 DB 관리 (config.py SSOT 유지)
- 자동 대체 표현 제안 (Revise 노드가 판단)

---

## DoD B-2: 문체 일관성

### 구현 방법
- `_detect_speech_level(text)` 헬퍼 함수를 추가한다.
- 한국어 반말/존댓말 지표 (spec 힌트 준용):
  - 반말 지표: 어절(공백 split) 끝이 `{"야","어","지","네","게","냐","을게","는데","잖아","거든","니까"}`
  - 존댓말 지표: 어절 끝이 `{"요","세요","습니다","ㅂ니다","ㅂ니까","겠습니다","시죠"}`
- 한 씬의 문장들에서 반말/존댓말 지표 횟수를 각각 카운트하여 dominant level을 결정한다.
- dialogue 구조에서만 적용 (monologue/narrated_dialogue는 Narrator 때문에 혼용이 자연스러울 수 있음).

### 동작 정의
1. `_detect_speech_level(script) -> str | None`: `"formal"` / `"informal"` / `None` (판정 불가) 반환.
   - 반말 지표 카운트와 존댓말 지표 카운트를 비교하여 다수결 결정.
   - 양쪽 모두 0이면 None.
2. dialogue 구조에서 동일 speaker의 씬들을 수집한다.
3. 각 씬의 speech level을 판정한다.
4. 한 speaker의 씬 중 formal이 3개 이상 **그리고** informal이 3개 이상이면 WARNING: `"speaker {speaker}: 반말({informal_count}씬)/존댓말({formal_count}씬) 혼용 — 문체 통일 필요"`
5. 판정 불가(None) 씬은 카운트에서 제외한다.

### 엣지 케이스
- 전체 씬이 5개 미만 → formal/informal 각 3개 이상 불가능이므로 자동 통과
- Narrator 씬은 speaker별 수집에서 제외 (Narrator는 문체 통일 대상이 아님)
- script가 None/빈 → speech level None → 카운트에서 제외
- 한 씬에 반말/존댓말이 혼재 → 다수결 기준 (동률이면 None)

### 영향 범위
- `_review_validators.py` (헬퍼 함수 + 호출)

### 테스트 전략
- A speaker가 formal 3씬 + informal 3씬 → WARNING
- A speaker가 formal 3씬 + informal 2씬 → WARNING 없음
- monologue 구조 → 검증 건너뜀
- `_detect_speech_level` 단위 테스트 (반말/존댓말/혼재/빈 문자열)

### Out of Scope
- 영어 문체 분석
- 형태소 분석기 기반 정밀 분석 (어절 끝 패턴만 사용)
- 씬 내부 문장 레벨 혼용 감지 (씬 단위 판정)

---

## 통합: 2개 위치 배치

### Review 노드 (`_review_validators.py`)

- `validate_dialogue_quality(scenes: list[dict], structure: str) -> tuple[list[str], list[str]]`
  - `(errors, warnings)` 튜플 반환.
  - 내부에서 **A-2, A-3, B-1, B-2**를 순차 호출하고 결과를 합산한다. (A-1은 제외 — Finalize에서 실행)
- `validate_scenes()` 함수의 **기존 for 루프 이후, passed 판정 이전**에 호출을 삽입한다.

```python
# validate_scenes() 기존 코드 말미 (line ~139)
dialogue_errors, dialogue_warnings = validate_dialogue_quality(scenes, structure)
errors.extend(dialogue_errors)
warnings.extend(dialogue_warnings)

passed = len(errors) == 0  # 기존 로직 유지
```

### Finalize 노드 (`finalize.py`)

- `_validate_emotion_continuity(scenes: list[dict]) -> None`
  - A-1 감정 중복 연속 검증. `context_tags.emotion` 기반.
  - `finalize_node()` 그룹 2 끝에 배치 (`_inject_writer_plan_emotions()` 이후).
  - 중복 감지 시 WARNING/ERROR 로그 출력 (렌더링 차단 없음).

### 엣지 케이스
- scenes가 빈 리스트 → dialogue 검증은 아무것도 안 잡음 (이미 씬 개수 부족 ERROR가 존재)
- `validate_dialogue_quality`에서 exception 발생 → 순수 함수이므로 예외 = 버그. `re.search` 실패 방어는 B-1에서 처리.
- A-1이 Finalize에서 실행되므로 Revise 루프에는 영향 없음 — 로그 기록만

### 영향 범위
- `_review_validators.py`: `validate_scenes()` 함수에 2줄 추가 + `validate_dialogue_quality()` 신규
- `finalize.py`: `_validate_emotion_continuity()` 함수 추가 + 호출 1줄
- `config.py`: `DIALOGUE_CLICHE_PATTERNS` 상수 추가

### 변경 파일 목록 (5개)
1. `backend/services/agent/nodes/_review_validators.py` — Review 검증 (A-2, A-3, B-1, B-2)
2. `backend/services/agent/nodes/finalize.py` — Finalize 검증 (A-1 감정 중복)
3. `backend/config.py` — `DIALOGUE_CLICHE_PATTERNS` 상수
4. `backend/tests/test_review_dialogue_quality.py` — Review 검증 테스트 (신규)
5. `backend/tests/test_finalize_emotion_continuity.py` — Finalize 감정 중복 테스트 (신규)

### 테스트 전략 (통합)
- Review: `validate_scenes()` 호출 시 A-2~B-2 결과가 errors/warnings에 포함되는지 확인
- Finalize: `_validate_emotion_continuity()` 호출 시 WARNING/ERROR 로그가 발생하는지 확인
- 기존 테스트 regression 확인
- dialogue 검증의 WARNING이 Revise 노드에서 소비 가능한 형태인지 메시지 포맷 확인

### Out of Scope
- `review.py` 수정 (호출 구조 변경 없음)
- Gemini 호출 추가 (비용/시간 증가 없음)
- Revise 노드의 피드백 파싱 로직 수정 (기존 errors/warnings 소비 경로 그대로 활용)

---

## 미결 질문

없음. spec이 충분히 명확하고, 모든 DoD 항목에 대해 구현 방향이 결정되었다.
