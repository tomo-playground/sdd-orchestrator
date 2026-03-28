# /docs Command

문서 구조 조회 및 정합성 체크를 수행하는 원자적 명령입니다.

## 사용법

```
/docs [action]
```

### Actions

| Action | 설명 |
|--------|------|
| (없음) | 문서 구조 트리 및 파일 목록 출력 |
| `check` | 깨진 링크, 오래된 경로 참조 검사 |
| `features` | FEATURES/ 디렉토리 기능별 상태 요약 |
| `size` | 파일별 줄 수 확인 (800줄 초과 경고) |

## 실행 내용

### 조회 (기본)
```bash
find docs/ -name "*.md" | sort
```
문서 구조 트리를 카테고리별로 출력합니다.

### check
다음 항목을 검사합니다:
1. **깨진 내부 링크**: `[text](path)` 형식의 링크 대상 파일 존재 여부
2. **오래된 경로 참조**: 코드/문서 내 `docs/ROADMAP.md`, `docs/specs/` 등 옛 경로 잔존 여부
3. **CLAUDE.md 동기화**: 문서 구조 섹션과 실제 디렉토리 일치 여부

### features
```bash
# FEATURES/ 각 파일에서 "상태:" 라인 파싱
grep -r "상태:" docs/01_product/FEATURES/
```

출력:
```markdown
## 기능 명세 현황

| 파일 | 기능 | 상태 |
|------|------|------|
| SOFT_DELETE.md | Soft Delete | 미착수 |
| MULTI_CHARACTER.md | 다중 캐릭터 | 미착수 |
| ... | ... | ... |
```

### size
```bash
wc -l docs/**/*.md | sort -rn
```

800줄 초과 파일에 경고 표시:
```markdown
## 문서 크기 점검

| 파일 | 줄 수 | 상태 |
|------|-------|------|
| ROADMAP.md | 481 | ✅ OK |
| PROMPT_SPEC.md | 820 | ⚠️ 800줄 초과 (분할 필요) |
```

## 관련 파일
- `CLAUDE.md` - 문서 구조 섹션
- `docs/00_meta/DOCS_STRUCTURE_PLAN.md` - 문서 구조 원본 계획
- `docs/01_product/FEATURES/` - 기능 명세
