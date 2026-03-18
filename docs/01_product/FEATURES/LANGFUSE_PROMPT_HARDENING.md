# Phase 36: LangFuse Prompt Quality Hardening

**상태**: 완료
**착수일**: 2026-03-18
**목표**: LangFuse 등록 프롬프트 33개 전수 분석 후 업계 표준 준수 + 코드↔프롬프트 정합성 확보

---

## 배경

프롬프트 엔지니어 에이전트의 2회 정밀 분석 결과, 33건의 개선 사항 발견:
- CRITICAL 2건 / HIGH 10건 / MEDIUM 14건 / LOW 7건
- 핵심 문제: 코드↔프롬프트 가중치 불일치, 무효 Danbooru 태그 권장, System/User 중복, CoT 미활용

## Sprint 구성

### Sprint A: CRITICAL (2건)

| # | 항목 | 설명 | 수정 대상 |
|---|------|------|----------|
| A-1 | Narrative 가중치 동기화 | 코드(`review.py`): Hook=30%, Speaker Tone=20%, Script-Image Sync=10% vs `pipeline/review/unified` 프롬프트: Hook=35%, Speaker Tone=10%, Script-Image Sync=15%. Gemini 채점 기준과 코드 재계산 기준 불일치 → 통과/실패 뒤집힘 | `pipeline/review/unified` LangFuse 프롬프트 |
| A-2 | 무효 Danbooru 태그 6개 수정 | `profile_standing`(0), `leaning_wall`(0), `standing_looking_up`(0), `sitting_eating`(0), `warm_lighting`(0), `blue_hour`(0) → 유효 태그 조합으로 교체 | `pipeline/cinematographer`, `storyboard/narrated` LangFuse 프롬프트 |

### Sprint B: HIGH (10건)

| # | 항목 | 설명 | 수정 대상 |
|---|------|------|----------|
| B-1 | 저빈도 태그 대체 | `golden_hour`(61)→`sunset`, `face_focus`(0)→`portrait`, `office_desk`(0)→`desk`, `tired`(0)→`half-closed_eyes` | LangFuse 프롬프트 + `_context_tag_utils.py` |
| B-2 | Writer↔Cinematographer context_tags 일관성 | Writer는 `expression`/`mood` 생성, Cinematographer는 금지하고 `emotion` 사용. FastTrack 시 미보정 | `storyboard/*` + `pipeline/cinematographer` 프롬프트 |
| B-3 | `concept-architect` 변수 확인 | `{{focus_instruction}}` 바인딩 여부 코드 확인 + 미사용 시 제거 | `tool/concept-architect` 프롬프트 + 코드 |
| B-4 | `edit-scenes` injection 방어 | 사용자 `instruction` 직접 삽입, sanitization 미확인 | 코드(호출부) 확인 + 필요시 방어 추가 |
| B-5 | `bishoujo`↔`bishounen` 대체 관계 수정 | 의미 다른 태그를 대체로 제시 → 대체 관계 제거 | `pipeline/cinematographer` 프롬프트 |
| B-6 | System/User 중복 제거 (4개) | `director`, `tts-designer`, `review/reflection`, `analyze-topic` 중복 제거 | 4개 LangFuse 프롬프트 |
| B-7 | `bird's_eye_view`(106)→`from_above` | 극저빈도 대체 | `pipeline/cinematographer` 프롬프트 |
| B-8 | `backlighting`/`backlit` 중복 통일 | 별칭 관계 태그 하나로 통일 | `pipeline/cinematographer` 프롬프트 |

### Sprint C: MEDIUM (14건)

| # | 항목 | 설명 |
|---|------|------|
| C-1 | `nervous_smile` 예시 수정 | compound expression 금지 규칙과 모순. `nervous` + `smile` 분리 |
| C-2 | `holding_object` 표현 정확화 | 존재하지 않는 태그 금지 → `holding 단독 대신 holding_phone 등 구체 태그 사용` 표현 |
| C-3 | `ip_adapter_weight` 규칙/예시 모순 | 규칙은 `null`, 예시는 `0.0`. 예시를 `null`로 통일 |
| C-4 | 한국어 emotion 별칭 오매핑 2건 | `"호기심"→"confused"` → `"curious"`, `"감동"→"grieving"` → `"touched"` |
| C-5 | ControlNet pose 형식 구분 명시 | 공백(pose 파일명) vs 언더바(Danbooru 태그) 혼용 해소 |
| C-6 | `edit-scenes` 출력에 `context_tags` 추가 | 편집 씬의 emotion→expression 파생 지원 |
| C-7 | `scene-expand` 출력에 `context_tags` 추가 | 확장 씬의 cinematographer 호환 |
| C-8 | `review/evaluate` + `review/narrative` 레거시 정리 | `review/unified` 사용 중이면 deprecated 처리 |
| C-9 | `dialogue` 조건부 변수 JSON 안전성 | `{{multi_scene_mode_field}}` 빈 문자열 시 JSON 유효성 확인 |
| C-10 | Storyboard 공통 규칙 파셜 추출 | 4개 storyboard 공통 70% → `shared/partial-*` 5개 신규 |
| C-11 | CoT 도입 (cinematographer) | 15개 규칙 동시 적용 → 7단계 Processing Steps 추가 |
| C-12 | `1girl` 예시 정리 | sanitization 변환 혼동 방지 → 예시에서 제거 또는 주석 |
| C-13 | 변수 형식 통일 | `{{ var }}` vs `{{var}}` → 하나로 통일 |
| C-14 | `storyboard/dialogue` 예시에 `cinematic` 필드 추가 | cinematographer 호환 |

### Sprint D: LOW + 체계 수립 (7건)

| # | 항목 | 설명 |
|---|------|------|
| D-1 | `staging` 라벨 도입 | A/B 테스트용 프롬프트 라벨 체계 |
| D-2 | `tags` 필드 활용 | 카테고리/도메인 태그 추가 |
| D-3 | `config` 필드 활용 | 권장 모델/temperature 기록 |
| D-4 | System 메시지 간결 프롬프트 보강 | `review/evaluate`, `concept-architect` 등 4개 |
| D-5 | `validate-image-tags` 이미지 입력 명시 | 멀티모달 입력 방법 문서화 |
| D-6 | Markdown 테이블 과다 프롬프트 간소화 | cinematographer 6+테이블 최적화 |
| D-7 | 버전 관리 가이드 작성 | production/staging/deprecated 운영 절차 |

---

## LangFuse 프롬프트 버전 관리 가이드 (D-7)

### 라벨 체계
| 라벨 | 용도 |
|------|------|
| `production` | 현재 프로덕션 사용 중 (코드가 이 라벨로 fetch) |
| `latest` | 최신 버전 (production과 동일 버전 유지) |
| `deprecated` | 더 이상 사용하지 않음 (unified로 대체된 경우 등) |

### 운영 절차
1. **수정 시**: 현재 production 내용 fetch → 변경 → 새 버전 생성 (production+latest)
2. **A/B 테스트 시**: staging 라벨 도입 후, 코드에서 라벨 분기 (향후)
3. **폐기 시**: production 라벨 제거 + deprecated 라벨 추가

### tags 분류 체계
- 카테고리: `pipeline`, `storyboard`, `tool`, `shared`
- 도메인: `danbooru`, `tts`, `bgm`, `review`, `creative`, `script`

### config 활용
- `model`: 권장 Gemini 모델 (예: `gemini-2.5-flash`)
- `temperature`: 권장 temperature (review=0.3, creative=0.8, script=0.7)

---

## 완료 기준 (DoD)

- [x] CRITICAL 2건 수정 + 코드↔프롬프트 가중치 일치 검증
- [x] HIGH 10건 수정 + 무효 태그 0개 달성
- [x] MEDIUM 14건 수정 (9완료 + 5이슈없음/이관)
- [x] LOW 7건 수정 (D-6 SKIP, C-10/C-13 이관)
- [ ] 기존 테스트 전체 PASS (regression 없음)
