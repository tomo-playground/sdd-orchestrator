# /vrt Command

Visual Regression Test를 실행하는 원자적 명령입니다.

## 사용법

```
/vrt [options]
```

### Options

| Option | 설명 |
|--------|------|
| (없음) | 전체 VRT 실행 |
| `--update` | 기준 스냅샷 업데이트 |
| `--component <name>` | 특정 컴포넌트만 테스트 |

## 실행 내용

### 전체 테스트
```bash
cd frontend && npm run test:vrt
```

### 스냅샷 업데이트
```bash
cd frontend && npm run test:vrt -- --update-snapshots
```

### 특정 컴포넌트
```bash
cd frontend && npm run test:vrt -- --grep "<name>"
```

## 출력 형식

```markdown
## VRT 결과

✅ 통과: 34/36
❌ 실패: 2/36

### 실패 항목
1. SceneCard - 자막 위치 변경 감지
2. RenderSettings - 버튼 색상 변경 감지

### 액션
- 의도된 변경이면: `/vrt --update`
- 버그이면: 코드 수정 필요
```

## 관련 파일
- `frontend/tests/vrt/`
- `frontend/playwright.config.ts`
