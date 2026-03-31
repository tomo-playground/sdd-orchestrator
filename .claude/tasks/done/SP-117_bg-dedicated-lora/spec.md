# SP-117: v-pred → epsilon 체크포인트 전환

approved_at: 2026-03-29
priority: P2
scope: backend
assignee: AI
created: 2026-03-29

## 배경

NoobAI XL v-pred 체크포인트가 배경(no_humans, scenery) 생성 시 극단적 파란빛/어두운 이미지를 생성하는 문제.
v-prediction 모델의 알려진 이슈로, 캐릭터 없는 장면에서 색 공간 앵커가 없어 색이 수렴함.

실험 결과 NoobAI XL **epsilon 1.1** 체크포인트로 전환하면:
- 배경 색감이 자연스러움 (카페/침실 등 프롬프트 정상 반영)
- 기존 LoRA(flat_color, detailer) 100% 호환
- 캐릭터 이미지 품질도 양호

## 목표

체크포인트를 v-pred → epsilon으로 전환하여 배경/캐릭터 모두 자연스러운 색감으로 생성.

## DoD (Definition of Done)

- [ ] DB `sd_models` 테이블에 epsilon 체크포인트 등록
- [ ] StyleProfile id=3 (Flat Color Anime)의 `sd_model_id`를 epsilon 모델로 변경
- [ ] ComfyUI 워크플로우에서 v-pred 전용 설정(ModelSamplingDiscrete 등) 제거/분기
- [ ] CFG scale 조정 (v-pred 4.5 → epsilon 7.0)
- [ ] 배경 이미지 생성 테스트 — 자연스러운 색감 확인
- [ ] 캐릭터 씬 이미지 품질 확인 — 기존 대비 열화 없음
- [ ] 기존 LoRA(flat_color, detailer, openpose ControlNet) 호환성 확인

## 참고

- 실험 이미지: `.cp-images/bg_eps_*.png`, `.cp-images/bg_test_*.png` (v-pred vs epsilon 비교)
- epsilon 체크포인트: `/home/tomo/sd-models/checkpoints/noobaiXL_epsPred11.safetensors`
- v-pred 체크포인트: `noobaiXLNAIXL_vPred10Version.safetensors`
- Gemini 분석: v-pred의 no_humans 색 편향은 Zero-Terminal SNR + CFG color burning이 원인
