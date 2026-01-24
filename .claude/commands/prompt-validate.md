# /prompt-validate Command

SD 프롬프트 문법을 검증하는 원자적 명령입니다.

## 사용법

```
/prompt-validate "<prompt>"
```

## 검증 항목

### 1. 순서 검증
```
올바른 순서:
[Quality] → [Subject] → [Identity] → [Clothing] → [Pose] → [Environment] → [LoRA]

예시:
masterpiece, best quality, 1girl, solo, blue hair, school uniform, sitting, classroom, <lora:name:1.0>
```

### 2. LoRA 위치
- LoRA 태그는 **반드시 맨 마지막**에 위치
- 형식: `<lora:name:weight>`

### 3. 중복 검사
- 같은 의미의 태그 반복 감지
- 예: `blue hair, blue_hair` (중복)

### 4. 충돌 검사
Exclusive 그룹 내 다중 선택 감지:
- hair_length: `long hair` vs `short hair`
- time: `day` vs `night`
- shot_type: `close-up` vs `full body`

### 5. 의존성 검사
Requires 규칙 확인:
- `twintails` → `long hair` 필요
- `ponytail` → `long hair` 또는 `medium hair` 필요

### 6. 가중치 범위
- 권장: 0.5 ~ 1.5
- 경고: 범위 초과 시

## 출력 형식

### 통과
```markdown
## 프롬프트 검증 결과

✅ **통과**

### 분석
- 태그 수: 12개
- LoRA: eureka_v9 (weight: 1.0)
- 순서: 정상

### 구조
| Category | Tags |
|----------|------|
| Quality | masterpiece, best quality |
| Subject | 1girl, solo |
| Identity | blue hair, purple eyes |
| Clothing | school uniform |
| Pose | sitting, smile |
| Environment | classroom |
| LoRA | <lora:eureka_v9:1.0> |
```

### 실패
```markdown
## 프롬프트 검증 결과

❌ **실패** (3개 문제)

### 문제점
1. **순서 오류**: LoRA가 맨 앞에 위치
   - 현재: `<lora:...>, masterpiece, ...`
   - 수정: `masterpiece, ..., <lora:...>`

2. **충돌**: hair_length 그룹에서 다중 선택
   - 감지: `long hair`, `short hair`
   - 수정: 하나만 선택

3. **의존성 누락**: twintails는 long hair 필요
   - 감지: `twintails` (long hair 없음)
   - 수정: `long hair` 추가

### 수정된 프롬프트
```
masterpiece, best quality, 1girl, solo, long hair, twintails, ...
```
```

## 관련 파일
- `.claude/agents/prompt-engineer.md` - 프롬프트 규칙 상세
- `frontend/app/constants/index.ts` - 키워드 정의
