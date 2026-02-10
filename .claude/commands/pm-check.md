# /pm-check Command

PM 자율 점검 커맨드. 문서/로드맵/기능 명세의 정합성을 자동으로 체크합니다.

## 사용법

```
/pm-check [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 전체 점검 (아래 모든 항목 실행) |
| `docs` | 문서 크기(800줄)/링크 점검 |
| `roadmap` | 미결 항목, 상태 불일치, 날짜 최신성 감지 |
| `features` | 기능 명세 현황 + Tier 1 명세 누락 감지 |
| `dod` | DoD 4항목 체크리스트 출력 |

## 실행 내용

### 전체 점검 (기본)

아래 4개 점검을 순서대로 실행하고, 결과를 종합 보고합니다.

### docs -- 문서 건강성

1. `docs/` 내 모든 `.md` 파일의 줄 수를 확인합니다.
2. 800줄 초과 파일에 경고를 표시합니다.
3. 내부 링크(`[text](path)`) 대상 파일 존재 여부를 검사합니다.

### roadmap -- 로드맵 정합성

1. `docs/01_product/ROADMAP.md`를 읽어 "현재 진행 상태" 섹션의 날짜가 7일 이내인지 확인합니다.
2. 완료된 Phase 내에 `[ ]` (미완료 체크박스)가 남아있는지 검사합니다.
3. Tier 1-3 분류와 7-1/7-2 항목의 상태 불일치를 감지합니다.

### features -- 기능 명세 커버리지

1. `docs/01_product/FEATURES/` 디렉토리의 파일 목록을 조회합니다.
2. ROADMAP의 Tier 1 항목 중 FEATURES/ 명세가 없는 것을 감지합니다.
3. 각 명세 파일의 "상태:" 라인을 파싱하여 현황 테이블을 출력합니다.

### dod -- Definition of Done

`docs/01_product/PRD.md` S4에서 DoD 4항목을 읽어 체크리스트로 출력합니다:
- [ ] **Autopilot**: 주제 입력 후 '이미지 생성 완료'까지 멈춤 없이 진행되는가?
- [ ] **Consistency**: 캐릭터의 머리색/옷이 Base Prompt대로 유지되는가?
- [ ] **Rendering**: 최종 비디오 파일 생성, 소리(TTS+BGM) 정상 출력되는가?
- [ ] **UI Resilience**: 새로고침해도 Draft가 복구되는가?

## 출력 형식

```markdown
## PM 점검 보고

**점검 일시**: YYYY-MM-DD

### 문서 건강성
| 파일 | 줄 수 | 상태 |
|------|-------|------|
| ... | ... | OK/WARNING |

### 로드맵 정합성
- 상태 날짜: YYYY-MM-DD (OK 7일 이내 / WARNING 갱신 필요)
- 미결 항목: N건

### 기능 명세 커버리지
| Tier 1 항목 | FEATURES/ 명세 | 상태 |
|-------------|---------------|------|
| ... | ... | OK/MISSING |

### DoD 체크리스트
- [ ] Autopilot
- [ ] Consistency
- [ ] Rendering
- [ ] UI Resilience
```

## 관련 파일
- `docs/01_product/ROADMAP.md` - 로드맵
- `docs/01_product/PRD.md` - DoD 정의
- `docs/01_product/FEATURES/` - 기능 명세
- `.claude/agents/shorts-pm.md` - PM 에이전트
