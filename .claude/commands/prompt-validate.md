# /prompt-validate Command

SD 프롬프트 문법을 검증하는 원자적 명령입니다.

## 사용법

```
/prompt-validate "<prompt>"
```

## 검증 항목

### 1. 순서 검증 (V3 12-Layer)
```
올바른 순서 (12-Layer):
[Quality(0)] → [Subject(1)] → [Identity(2)] → [Body(3)] → [MainCloth(4)] →
[DetailCloth(5)] → [Accessory(6)] → BREAK → [Expression(7)] → [Action(8)] →
[Camera(9)] → [Environment(10)] → [Atmosphere(11)]
```

### 2. LoRA 위치
- LoRA 태그는 **반드시 맨 마지막**에 위치
- 형식: `<lora:name:weight>`

### 3. 중복 검사
- 같은 의미의 태그 반복 감지

### 4. 충돌 검사 (DB-driven `tag_rules`)
태그 레벨 및 카테고리 레벨 충돌 감지

### 5. 의존성 검사 (DB-driven `tag_rules`)
Requires 규칙 확인

### 6. 가중치 범위
- 권장: 0.5 ~ 1.5

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
| ... | ... |
```

### 실패
```markdown
## 프롬프트 검증 결과

❌ **실패** (N개 문제)

### 문제점
1. **순서 오류**: ...
2. **충돌**: ...

### 수정된 프롬프트
...
```

## 관련 파일
- `docs/03_engineering/backend/PROMPT_SPEC.md` - 프롬프트 설계 규칙
- `docs/03_engineering/backend/PROMPT_PIPELINE.md` - 프롬프트 파이프라인
- `backend/services/prompt/composition.py` - PromptBuilder (12-Layer)
- `backend/services/keywords/validation.py` - 태그 검증 로직
