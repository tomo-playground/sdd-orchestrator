# SP-131: 파이프라인 finalize 후 백엔드 DB 직접 저장

- **branch**: feat/SP-131_finalize-server-side-persist
- **priority**: P1
- **scope**: backend

## 배경

현재 스크립트 파이프라인의 씬 저장 흐름:
```
finalize 노드 완료 → SSE 이벤트 전송 → 프론트엔드 수신 → syncToGlobalStore → autoSave (2초) → PUT /storyboards/{id}
```

SSE 연결이 중간에 끊기면 (브라우저 탭 비활성, 네트워크 타임아웃, 15-20분 장시간 실행 등) finalize 이벤트가 유실되고, 씬이 DB에 저장되지 않는다.

**반복 발생 확인**: storyboard 1206에서 finalize 완료 (11:18:58, 9씬) 후 `PUT /storyboards/1206` 호출 0건. `stage_status=None`, `scenes=[]`.

## DoD

- [ ] `stream_graph_events()` 내에서 finalize 완료 시 (`final_output` 존재) 씬을 DB에 직접 저장
- [ ] `stage_status`를 `"script_done"` 또는 적절한 값으로 업데이트
- [ ] 프론트엔드 autoSave와 충돌 방지 (version 체크 또는 idempotent upsert)
- [ ] SSE 연결 끊김 후 프론트엔드 재접속 시 DB에서 씬 로드 가능
