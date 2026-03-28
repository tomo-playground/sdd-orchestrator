# 트러블슈팅: ComfyUI 흰 이미지 생성 (2026-03-28)

## 증상
- Storyboard 1202 Direct 탭에서 10개 씬 중 4개가 100% 흰색 이미지
- 재생성해도 동일 씬에서 반복적으로 흰색 발생
- Auto-Regen이 `인물 미감지`로 감지하지만, seed 변경 재시도로 해결 안 됨

## 근본 원인

**PR #225 (ComfyUI 네이티브 정리)에서 weight emphasis strip 제거가 원인.**

```python
# 제거된 코드 (PR #225)
clean_prompt = re.sub(r"\(([^:()]+):[0-9.]+\)", r"\1", clean_prompt)
neg_prompt = re.sub(r"\(([^:()]+):[0-9.]+\)", r"\1", neg_prompt)
```

- `(brown_eyes:1.2)` → `brown_eyes`로 변환하는 코드
- "ComfyUI가 네이티브로 weight emphasis 지원하므로 불필요" 판단으로 제거
- 하지만 **noobaiXL v-pred + DynamicThresholding 조합**에서 weight emphasis가 생성 결과를 극도로 밝게 만듦 (min pixel=250, 사실상 흰색)

### 왜 일부 씬만 영향?
- weight emphasis 태그 개수/강도가 많은 씬에서 DynamicThresholding의 `mimic_scale: 7.0` vs `cfg: 4.5` 차이가 증폭
- 정상 씬: 상대적으로 단순한 프롬프트 또는 강한 시각적 단서 (sunlight, light_rays 등)

## 수정 내역 (7건)

| 커밋 | 내용 | 유형 |
|------|------|------|
| `c8ea70a2` | **weight emphasis strip 복원** | **근본 수정** |
| `3baa412f` | 워크플로우 JSON `_meta.variables` placeholder key 충돌 수정 | 버그 |
| `1cea88e4` | `{{checkpoint}}` 변수 조기 주입 (`inject_variables` 전) | 버그 |
| `6f0c6399` | Auto-Regen 흰 이미지 감지 (white pixel ratio > 95%) | 방어 |
| `330fb349` | `clear_cache` unload_models=True (캐시 오염 대응) | 방어 |
| `2ddff94f` | ComfyUI 최종 워크플로우 요약 로깅 (checkpoint, prompt, seed, cfg) | 가시성 |
| `39804d0d` | LoRA 적용 로깅 | 가시성 |

## 디버깅 과정

1. MinIO 이미지 확인 → 10개 중 4개 100% 흰색 (124~285KB, 빈 PNG)
2. ComfyUI output 직접 확인 → ComfyUI 레벨에서 이미 흰색
3. 생성 시간 6.6초 → 28 steps SDXL 정상 시간(15-25초) 대비 의심 → 캐시 히트 확인
4. `Unresolved workflow placeholders: ['checkpoint']` 경고 발견 → placeholder 치환 문제 수정
5. 워크플로우 `_meta.variables`에 `"{{seed}}": "시드"` 형태 → inject 시 `42: "시드"` → JSON 파싱 실패 수정
6. IP-Adapter 없이 직접 ComfyUI 테스트 → 정상 → IP-Adapter 의심
7. IP-Adapter weight 0.3 테스트 → 정상 → weight 문제 의심
8. 백엔드 경유 vs 직접 ComfyUI → 직접은 항상 정상 → 백엔드 파이프라인 차이 추적
9. **PR #225 diff 정밀 분석 → weight emphasis strip 제거 발견**
10. strip 복원 후 모든 씬 정상 생성 확인

## 재발 방지

- Auto-Regen에 흰 이미지 감지 추가 (white > 95% → critical failure)
- ComfyUI clear_cache에 model unload 포함
- KSampler/LoRA 적용 로깅으로 디버깅 가시성 확보
- weight emphasis strip 주석에 **제거 금지 사유** 명시

## 관련 파일

- `backend/services/sd_client/comfyui/__init__.py` — `_payload_to_variables()` weight strip
- `backend/services/sd_client/comfyui/workflows/scene_single.json` — `_meta.variables` 수정
- `backend/services/auto_regen.py` — `_is_blank_image()` 추가
- `backend/services/image_gen_pipeline.py` — 재시도 시 cache clear
