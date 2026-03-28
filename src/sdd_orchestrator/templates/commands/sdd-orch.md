# /sdd-orch Command

SDD 오케스트레이터 기동/중지/상태 확인 명령입니다.

## 실행 내용

```bash
bash /home/tomo/Workspace/shorts-producer/.claude/scripts/sdd-orch.sh $ARGUMENTS
```

## 사용법

```
/sdd-orch start    # 기동
/sdd-orch stop     # 중지
/sdd-orch status   # 상태 확인
/sdd-orch restart  # 재시작
```

## 동작
- `start`: 백그라운드 프로세스로 오케스트레이터 기동 (ORCH_AUTO_RUN=1, ORCH_AUTO_DESIGN=1)
- `stop`: PID 파일 기반 프로세스 종료
- `status`: 실행 상태 + 최근 로그 5줄 출력
- `restart`: stop → start

로그: `/tmp/orchestrator.log`
