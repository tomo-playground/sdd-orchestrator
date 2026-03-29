# SP-117 상세 설계: v-pred → epsilon 체크포인트 전환

## 변경 파일 요약

| 파일 | 변경 |
|------|------|
| `alembic/versions/xxx_epsilon_checkpoint.py` | 마이그레이션: sd_models INSERT + StyleProfile 업데이트 |
| `config.py` | CFG 4.5→7.0, CFG Rescale 0.2→0.0, 주석 업데이트 |
| `services/sd_client/comfyui/__init__.py` | 기본 CFG 주석 업데이트 |

---

## DoD 1: DB sd_models 테이블에 epsilon 체크포인트 등록

### 구현 방법
- `alembic/versions/` 에 새 마이그레이션 파일 생성
- `sd_models` 테이블에 epsilon 체크포인트 INSERT
- 기존 v-pred 체크포인트는 `is_active=False`로 비활성화 (삭제 아님)

### 동작 정의
```sql
-- before: v-pred만 활성
sd_models: [{id: 5, name: 'noobaiXLNAIXL_vPred10Version.safetensors', display_name: 'NoobAI-XL V-Pred 1.0', is_active: true}]

-- after: epsilon 활성, v-pred 비활성
sd_models: [
  {id: 5, name: 'noobaiXLNAIXL_vPred10Version.safetensors', display_name: 'NoobAI-XL V-Pred 1.0', is_active: false},
  {id: 6, name: 'noobaiXL_epsPred11.safetensors', display_name: 'NoobAI-XL Epsilon 1.1', is_active: true}
]
```

### 엣지 케이스
- v-pred 체크포인트 파일은 삭제하지 않음 (롤백 대비)
- 기존 스토리보드의 이미지는 영향 없음 (이미 생성된 이미지)

### 영향 범위
- StyleProfile.sd_model_id FK 참조 변경 필요 (DoD 2에서 처리)

### 테스트 전략
- 마이그레이션 upgrade/downgrade 테스트

### Out of Scope
- v-pred 체크포인트 파일 삭제
- 다른 StyleProfile(id=2 Realistic 등) 변경

---

## DoD 2: StyleProfile sd_model_id 변경

### 구현 방법
- 동일 마이그레이션에서 StyleProfile id=3 (Flat Color Anime)의 `sd_model_id`를 새 epsilon 모델 ID로 UPDATE

### 동작 정의
```sql
-- before
style_profiles: [{id: 3, name: 'Flat Color Anime', sd_model_id: 5}]

-- after
style_profiles: [{id: 3, name: 'Flat Color Anime', sd_model_id: 6}]
```

### 엣지 케이스
- StyleProfile의 `default_cfg_scale`이 NULL이면 config.py 전역값 사용 → config.py 변경으로 커버됨
- StyleProfile에 `default_cfg_scale`이 설정되어 있으면 그 값이 우선 → DB에서 확인 후 필요시 업데이트

### 테스트 전략
- StyleProfile id=3 조회 시 새 체크포인트명 반환 확인

---

## DoD 3: ComfyUI 워크플로우 v-pred 전용 설정 제거/조정

### 구현 방법
- `config.py`: `SD_CFG_RESCALE` 기본값 `0.2` → `0.0` (epsilon은 CFG Rescale 불필요)
- `config.py`: `SD_DEFAULT_CFG_SCALE` 기본값 `4.5` → `7.0`
- `config.py`: 주석 업데이트 (NoobAI-XL V-Pred → Epsilon)
- `services/sd_client/comfyui/__init__.py:512`: 기본 CFG 주석 업데이트

### 동작 정의
```python
# before
SD_DEFAULT_CFG_SCALE = 4.5
SD_CFG_RESCALE = 0.2  # V-Pred 전용

# after
SD_DEFAULT_CFG_SCALE = 7.0
SD_CFG_RESCALE = 0.0  # Epsilon은 불필요
```

### 엣지 케이스
- StyleProfile.default_cfg_scale이 설정된 경우 → 그 값이 config 전역값보다 우선
- `apply_sampler_to_payload()`에서 `SD_CFG_RESCALE > 0` 가드가 있으므로 0.0이면 자동 스킵

### 영향 범위
- 모든 이미지 생성(캐릭터+배경)에 CFG 7.0 적용
- 환경변수로 오버라이드 가능 (기존 구조 유지)

### 테스트 전략
- `apply_sampler_to_payload()` 호출 시 CFG Rescale이 payload에 포함되지 않음 확인
- config 값 변경 확인

### Out of Scope
- ComfyUI 워크플로우 JSON 파일 수정 (코드에서 동적 생성)
- sampler/scheduler 변경 (Euler + normal 유지)

---

## DoD 4: CFG scale 조정

DoD 3에 통합. StyleProfile.default_cfg_scale 확인 필요:

```sql
SELECT id, name, default_cfg_scale FROM style_profiles WHERE id = 3;
```

- NULL이면 config.py 전역값(7.0) 자동 적용
- 값이 있으면 마이그레이션에서 7.0으로 UPDATE

---

## DoD 5-7: 이미지 생성 테스트 + 호환성 확인

### 테스트 전략
- 배경 5종(office, convenience_store, subway, cafe, bedroom) 생성 → 색감 자연스러움 확인
- 캐릭터 씬 3종 생성 → 기존 대비 품질 열화 없음 확인
- flat_color LoRA + detailer LoRA 동작 확인
- ControlNet openpose 동작 확인

### 판정 기준
- 배경: 파란빛/극단 색면 없음
- 캐릭터: 프롬프트 반영 정상, 얼굴/의상 디테일 유지

---

## IP-Adapter v-pred 전용 설정 (확인 필요)

`config.py:842-843`:
```python
DEFAULT_IP_ADAPTER_GUIDANCE_END_VPRED = 0.5
DEFAULT_IP_ADAPTER_WEIGHT_VPRED = 0.5
```

이 설정이 epsilon에서도 동일하게 적용 가능한지 확인 필요.
- 변수명에 `VPRED`가 있지만 기능적으로는 IP-Adapter weight/guidance 범용 설정
- epsilon에서는 weight를 약간 올려도 될 수 있음 (v-pred보다 CFG가 안정적)
- 이번 태스크에서는 기존값 유지, 추후 튜닝

### Out of Scope
- IP-Adapter weight 재튜닝
- 변수명 리네이밍 (VPRED → 범용)
