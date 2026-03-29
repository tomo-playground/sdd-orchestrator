# SP-117: 배경 전용 LoRA 도입

- **status**: spec
- **priority**: P2
- **scope**: backend + prompt
- **assignee**: AI
- **created**: 2026-03-29

## 배경

캐릭터용 flat_color LoRA(`noobai_vpred_1_flat_color_v2`)가 배경(no_humans, scenery) 생성 시
극단적 파란빛/강렬한 색면을 유발하여 배경 품질이 저하되는 문제.

현재 `compose_for_background()`는 캐릭터용 StyleProfile LoRA를 그대로 배경에 적용하고 있음.

## 목표

배경 전용 LoRA를 도입하여, 배경 이미지가 자연스러운 색감과 디테일로 생성되도록 개선.

## DoD (Definition of Done)

- [ ] NOOB XL 호환 배경/scenery 전용 LoRA 탐색 및 선정 (Civitai)
- [ ] StyleProfile에 `bg_loras` 필드 추가 (또는 loras에 `bg_only` 플래그)
- [ ] `compose_for_background()`에서 캐릭터 LoRA 대신 배경 전용 LoRA 적용
- [ ] 배경 이미지 생성 테스트 — 자연스러운 색감 확인
- [ ] 기존 캐릭터 씬 이미지에 영향 없음 확인

## 참고

- 현재 StyleProfile id=3 (Flat Color Anime): `noobai_vpred_1_flat_color_v2:0.6`, `NOOB_vp1_detailer_by_volnovik_v1:0.35`
- `compose_for_background()`: `backend/services/prompt/composition.py:371`
- `_prepare_bg_prompt()`: `backend/services/stage/background_generator.py:37`
