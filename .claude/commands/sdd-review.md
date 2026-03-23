# /sdd-review Command

열린 PR의 코드 리뷰를 실행하는 SDD 명령입니다.

## 동작
1. 열린 PR 중 "Code review" 코멘트가 없는 PR 감지
2. `/code-review:code-review {PR번호}` 자동 실행
3. PR에 리뷰 코멘트 게시

## 전제 조건
- `gh` CLI 인증 완료
- 열린 PR이 있어야 함
