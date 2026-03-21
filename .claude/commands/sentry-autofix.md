# /sentry-autofix $ARGUMENTS

GitHub Issue(label:sentry)를 읽고 자동 수정 PR을 생성합니다.

## 사용법

```
/sentry-autofix #123       ← 특정 Issue 수정
/sentry-autofix            ← label:sentry 중 미수정 Issue 전체
```

## 실행 내용

### 1. Issue 조회
- `$ARGUMENTS`에 Issue 번호가 있으면 해당 Issue만
- 없으면 `gh issue list --label sentry --state open`에서 PR이 없는 Issue 전체

### 2. Issue별 자동 수정 (순차)
각 Issue에 대해:

1. Issue 본문의 스택트레이스 읽기
2. 원인이 되는 코드 탐색 (`Grep`, `Read`)
3. **실패 테스트 작성 (TDD)** — 버그를 재현하는 테스트
4. 테스트 실행 → RED 확인
5. 코드 수정 → 테스트 GREEN 확인
6. `fix/sentry-{issue번호}` 브랜치에서 커밋 + push
7. PR 생성 (`Fixes #{issue번호}` 포함)
8. 수정 불가 시 Issue에 `needs-manual-fix` 라벨 추가 + 코멘트

### 3. 결과 보고
- 수정 성공: PR 링크 출력
- 수정 실패: 사유 출력

## 제약
- DB 스키마 변경이 필요한 에러는 자동 수정 대상에서 제외
- 외부 서비스 장애(SD WebUI, MinIO 등)는 코드 수정 불가 → 코멘트만
- 동시 실행 금지 — 순차 처리
