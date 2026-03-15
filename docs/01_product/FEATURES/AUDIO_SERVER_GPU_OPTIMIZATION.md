# Phase 34: GPU 순차 독점 실행 & BGM 고도화

**상태**: 계획
**우선순위**: P1
**선행 관계**: Phase 12 (AI BGM 도입) 완료, Phase 32 (TTS prebuild) 완료

---

## 배경

### 현재 한계

| 문제 | 설명 |
|------|------|
| **GPU 동시 점유** | Forge(8-12GB) 상시 + TTS(6.8GB) 상시 = 14.8-18.8GB → OOM 리스크 |
| **모델 간 VRAM 협상 없음** | Forge/TTS/Music이 독립적으로 GPU 사용 → 동시 요청 시 충돌 |
| **BGM 저품질** | MusicGen-small 32kHz 모노, 30초 제한 |
| **큰 모델 사용 불가** | 16GB 전체를 1개 모델이 쓸 수 없음 → 모델 크기 제한 |

### 현재 GPU 점유 상황

```
RTX 5080 (16GB VRAM):
  Forge (상시):  ████████████ 8-12GB  ← 반환 안 함
  TTS (상시):    ██████████ 6.8GB     ← 반환 안 함
  합계:          14.8-18.8GB → OOM ⚠️
```

### 목표 GPU 점유 패턴

```
어느 시점이든 GPU 점유 모델 = 최대 1개:
  Forge 사용 중:  ████████████ 12GB   ← 16GB 독점 가능
  TTS 사용 중:    ██████████ 6.8GB    ← 16GB 독점 가능
  Music 사용 중:  ███████████ 10GB    ← 16GB 독점 가능
```

---

## 설계 결정

### 채택: Forge API 연동 + Audio Server 내부 관리

```
┌──────────────── Backend (:8000) ────────────────┐
│  ┌────────────────────────────────────────────┐  │
│  │         GpuCoordinator (신규)              │  │
│  │  active: "forge" | "tts" | "music" | None  │  │
│  │  asyncio.Lock 기반 순차 보장               │  │
│  └─────────────┬──────────────┬───────────────┘  │
│                │              │                   │
│         ┌──────┴──────┐ ┌────┴──────┐            │
│         │forge_control│ │audio_client│            │
│         └──────┬──────┘ └────┬──────┘            │
└────────────────┼─────────────┼───────────────────┘
                 │             │
          ┌──────┴──────┐ ┌───┴────────────┐
          │ Forge :7860 │ │ Audio :8001    │
          │ 기존 API:   │ │ GpuModelCache  │
          │ /unload-    │ │ (asyncio.Lock) │
          │  checkpoint │ │ /gpu/unload    │
          │ /reload-    │ │ /gpu/status    │
          │  checkpoint │ └────────────────┘
          └─────────────┘
```

**순차 실행 흐름**:
```
[Generate 클릭]
  → GpuCoordinator.acquire("forge")
    → Audio /gpu/unload (TTS 언로드)
    → Forge /reload-checkpoint
  → Forge /txt2img (이미지 생성)
  → GpuCoordinator.release("forge")

[Preview TTS 클릭]
  → GpuCoordinator.acquire("tts")
    → Forge /unload-checkpoint (VRAM 반환)
  → Audio /tts/synthesize (TTS 로드 + 합성)
  → GpuCoordinator.release("tts")

[Render]  ← 파이프라인 자연 순차
  → acquire("forge") → 이미지 확인 → release
  → acquire("tts") → 씬 TTS 합성 → release
  → acquire("music") → BGM 생성 → release
  → FFmpeg (CPU) → 완료
```

### Tech Lead 리뷰 반영 사항

| 이슈 | 해결 |
|------|------|
| **B-1 Thread Pool Starvation** | `threading.Lock` → `asyncio.Lock` 전환 (event loop 블로킹 없음) |
| **B-2 TTS 배치 + Forge 동시** | Audio Server `asyncio.Semaphore(1)` 게이트 + GpuCoordinator |
| **W-1 TTL 레이스** | evict_if_idle에서 Lock 내 `_last_used` 이중 체크 |
| **W-2 에러 복구** | acquire 실패 시 `_active_model = None` 리셋 보장 |
| **W-3 Studio 동시 조작** | Frontend UI 가드 (이미지 생성 중 TTS 비활성화) |
| **W-4 Health 의미** | `"ready"` 상태 추가 (서버 준비, 모델 lazy) |

### ACE-Step 선정 근거

| 모델 | 샘플레이트 | 채널 | 최대 길이 | VRAM | 적합성 |
|------|-----------|------|---------|------|--------|
| MusicGen-small (현재) | 32kHz | 모노 | ~30초 | ~1.2GB | ❌ 저품질 |
| Stable Audio Open | 44.1kHz | 스테레오 | 47초 | ~8GB | ❌ 길이 부족 |
| **ACE-Step v1** | **44.1kHz** | **스테레오** | **4분** | **8-10GB** | **✅ 최적** |

ACE-Step: Apache 2.0, Diffusion 기반 10-30x 빠름, GitHub 4,200+ stars.
**리스크**: RTX 50xx Blackwell 호환성 — `--no_flash_attn` fallback 필요할 수 있음.

---

## Sprint A: GPU On-demand 아키텍처 (P0)

### A-1: `GpuModelCache` — asyncio.Lock 기반

**파일**: `audio/services/gpu_cache.py` (신규)

```python
class GpuModelCache:
    """GPU 모델 순차 독점 + TTL Warm Cache.

    핵심: asyncio.Lock으로 event loop 블로킹 없이 직렬화.
    모델 로드/언로드만 to_thread로 실행.
    """
    _gpu_lock: asyncio.Lock          # 전역 공유
    _active_model: str | None        # 전역 공유

    _name: str
    _model: Any | None
    _last_used: float
    _ttl: float                      # TTS=300s, Music=60s
    _device: str                     # "cuda:0" (멀티 GPU 대비)

    async def acquire(self) -> Any:
        async with self._gpu_lock:
            if _active_model and _active_model != self._name:
                await asyncio.to_thread(
                    _active_caches[_active_model].force_evict
                )
            if not self._model:
                try:
                    await asyncio.to_thread(self._load)
                    _active_model = self._name
                except Exception:
                    _active_model = None  # W-2: 에러 복구
                    raise
            self._last_used = time.monotonic()
            return self._model

    async def release(self):
        self._last_used = time.monotonic()

    def force_evict(self):
        self._unload_fn(self._model)
        self._model = None

    async def evict_if_idle(self):
        if time.monotonic() - self._last_used < self._ttl:
            return  # 1차 체크 (Lock 없이)
        async with self._gpu_lock:
            if time.monotonic() - self._last_used < self._ttl:
                return  # W-1: 2차 체크 (TOCTOU 방지)
            await asyncio.to_thread(self.force_evict)
            _active_model = None
```

**완료 기준**:
- [ ] `asyncio.Lock` 기반 GpuModelCache 구현
- [ ] `force_evict()` — 다른 모델 로드 전 기존 모델 강제 해제
- [ ] TTL 이중 체크 패턴 (W-1)
- [ ] acquire 실패 시 `_active_model` 리셋 (W-2)
- [ ] 백그라운드 eviction asyncio.Task (60초 주기)

### A-2: TTS 엔진 GpuModelCache 적용

**파일**: `audio/services/tts_engine.py` (수정)

```
Before: global _model (상시 상주, 6.8GB)
After:  _tts_cache = GpuModelCache(name="tts", ttl=300, device="cuda:0")
```

- [ ] `global _model` 제거 → GpuModelCache 전환
- [ ] `load_model()` / `get_model()` 후방 호환 (health endpoint)
- [ ] 기존 TTS 테스트 통과

### A-3: Music 엔진 GpuModelCache 적용

**파일**: `audio/services/music_engine.py` (수정)

```
Before: _load_model_to_device() + _unload_model() + _inference_lock
After:  _music_cache = GpuModelCache(name="music", ttl=60, device="cuda:0")
```

- [ ] `_inference_lock` 제거 (GpuModelCache 내부 Lock으로 대체)
- [ ] 기존 MusicGen 테스트 통과

### A-4: Audio Server GPU 제어 API

**파일**: `audio/main.py` (수정)

| 신규 API | 역할 |
|----------|------|
| `POST /gpu/unload` | 현재 로드된 모델 언로드 (VRAM 반환) |
| `GET /gpu/status` | `{active: "tts"\|"music"\|null, vram_mb: int}` |

- [ ] GpuCoordinator가 Audio 모델 제어 시 사용
- [ ] Endpoint-level `asyncio.Semaphore(1)` 게이트 (B-1 해결)

### A-5: main.py 라이프사이클

```
Before: lifespan에서 TTS eager load
After:  모델은 첫 요청 시 lazy load. eviction task만 시작.
```

- [ ] startup 모델 로드 제거 → 서버 기동 ≤ 3초
- [ ] health: `"ready"` 상태 추가 (W-4: 서버 준비, 모델 lazy)
- [ ] 기존 API 동작 변경 없음 (첫 호출 시 로드 지연만 추가)

### A-6: 테스트

**파일**: `audio/tests/test_gpu_cache.py` (신규)

| 테스트 | 검증 내용 |
|--------|---------|
| `test_lazy_load` | 첫 acquire 시 load_fn 호출 |
| `test_cache_hit` | TTL 내 재호출 시 load_fn 미호출 |
| `test_ttl_eviction` | TTL 초과 후 evict_if_idle → unload_fn 호출 |
| `test_ttl_double_check` | TTL 직전 새 요청 → 불필요 재로드 방지 (W-1) |
| `test_concurrent_acquire` | 두 요청 동시 acquire → 직렬화 |
| `test_force_evict` | force_evict 호출 시 즉시 언로드 |
| `test_cross_model_evict` | TTS acquire 중 Music acquire → TTS evict 후 Music 로드 |
| `test_acquire_failure_recovery` | load 실패 시 _active_model=None (W-2) |

---

## Sprint B: Forge 연동 — GpuCoordinator (P0)

### B-1: Forge 제어 wrapper

**파일**: `backend/services/forge_control.py` (신규)

```python
async def forge_unload() -> bool:
    """Forge checkpoint 언로드 → VRAM 반환."""
    resp = await httpx.post(f"{SD_BASE_URL}/sdapi/v1/unload-checkpoint")
    return resp.status_code == 200

async def forge_reload() -> bool:
    """Forge checkpoint 재로드."""
    resp = await httpx.post(f"{SD_BASE_URL}/sdapi/v1/reload-checkpoint")
    return resp.status_code == 200

async def forge_is_busy() -> bool:
    """Forge가 이미지 생성 중인지 확인."""
    resp = await httpx.get(f"{SD_BASE_URL}/sdapi/v1/progress")
    return resp.json().get("state", {}).get("job_count", 0) > 0
```

- [ ] Forge 기존 API 활용 (Forge 코드 무수정)
- [ ] 타임아웃 설정 (reload: 60초, unload: 10초)

### B-2: GpuCoordinator

**파일**: `backend/services/gpu_coordinator.py` (신규)

```python
class GpuCoordinator:
    """전체 GPU 순차 독점 실행 보장 (Forge + Audio)."""

    _lock: asyncio.Lock
    _active: str | None  # "forge" | "tts" | "music" | None

    async def acquire(self, model: str):
        await self._lock.acquire()
        try:
            if self._active and self._active != model:
                await self._evict(self._active)
            await self._load(model)
            self._active = model
        except Exception:
            self._active = None
            self._lock.release()
            raise

    async def release(self, model: str):
        self._lock.release()

    async def _evict(self, model: str):
        if model == "forge":
            await forge_unload()
        else:  # "tts" | "music"
            await audio_client.gpu_unload()

    async def _load(self, model: str):
        if model == "forge":
            await forge_reload()
        # tts/music: Audio Server가 첫 요청 시 lazy load

    @asynccontextmanager
    async def use(self, model: str):
        await self.acquire(model)
        try:
            yield
        finally:
            await self.release(model)

gpu = GpuCoordinator()  # 싱글턴
```

- [ ] asyncio.Lock 기반 (event loop 블로킹 없음)
- [ ] Forge/Audio 양쪽 evict 지원
- [ ] context manager (`async with gpu.use("forge"):`)
- [ ] config.py에 `GPU_COORDINATOR_TIMEOUT` 상수

### B-3: Backend 통합

**수정 파일**:

| 파일 | 변경 |
|------|------|
| `services/generation.py` | Forge 호출을 `gpu.use("forge")`로 래핑 |
| `services/characters/reference.py` | Forge 호출 래핑 |
| `services/audio_client.py` | TTS/Music 호출을 `gpu.use("tts/music")`로 래핑 |
| `services/video/builder.py` | 렌더 파이프라인 단계별 acquire/release |

```python
# generation.py 예시
async with gpu.use("forge"):
    result = await httpx.post(forge_url + "/txt2img", ...)

# audio_client.py 예시
async with gpu.use("tts"):
    result = await httpx.post(audio_url + "/tts/synthesize", ...)
```

- [ ] 모든 Forge 호출 지점에 GpuCoordinator 적용
- [ ] 모든 Audio GPU 호출 지점에 GpuCoordinator 적용
- [ ] 기존 테스트 통과

### B-4: Frontend UI 가드 (W-3)

**수정 파일**: Frontend Studio 컴포넌트

- [ ] 이미지 생성 중(`isGenerating`) → TTS 미리듣기 버튼 비활성화
- [ ] TTS 생성 중 → 이미지 생성 버튼 비활성화
- [ ] 진행 상태 표시: "GPU 전환 중..." 스피너

### B-5: 테스트

| 테스트 | 검증 내용 |
|--------|---------|
| `test_forge_unload_reload` | Forge API 호출 정상 |
| `test_coordinator_sequential` | acquire → release 순차 보장 |
| `test_coordinator_evict_forge` | TTS acquire 시 Forge unload |
| `test_coordinator_evict_audio` | Forge acquire 시 Audio unload |
| `test_coordinator_error_recovery` | load 실패 시 lock 해제 + active 리셋 |

---

## Sprint C: ACE-Step 교체 (P1)

**선행**: Sprint A 완료 (GpuModelCache로 VRAM 안전 보장)

### C-1: 의존성 교체

**파일**: `audio/pyproject.toml` — ACE-Step + diffusers 추가, MusicGen 전용 의존성 제거 검토

### C-2: ACE-Step 엔진 구현

**파일**: `audio/services/acestep_engine.py` (신규)

- MusicGen과 동일 인터페이스: `generate_music(prompt, duration, seed) → (wav_bytes, sample_rate, seed, cache_hit)`
- 44.1kHz 스테레오 WAV 출력
- SHA256 캐시 (기존 패턴 유지)
- Blackwell 호환: FlashAttention 실패 시 자동 fallback

### C-3: config.py 상수

**Audio Server `config.py`**:
```python
MUSIC_ENGINE = os.getenv("MUSIC_ENGINE", "acestep")  # "acestep" | "musicgen"
ACESTEP_MODEL_NAME = os.getenv("ACESTEP_MODEL_NAME", "ACE-Step/ACE-Step-v1")
ACESTEP_SAMPLE_RATE = 44100
ACESTEP_MAX_DURATION = float(os.getenv("ACESTEP_MAX_DURATION", "240.0"))
```

**Backend `config.py`** 동기화:
```python
MUSIC_SAMPLE_RATE = int(os.getenv("MUSIC_SAMPLE_RATE", "44100"))
MUSIC_MAX_DURATION = float(os.getenv("MUSIC_MAX_DURATION", "240.0"))
```

### C-4: main.py 엔진 선택

```python
if MUSIC_ENGINE == "acestep":
    from services import acestep_engine as music_mod
else:
    from services import music_engine as music_mod
```

### C-5: Backend 동기화

- `MUSICGEN_SAMPLE_RATE` → `MUSIC_SAMPLE_RATE` (44100)
- `audio_client.generate_music()` — HTTP 계약 변경 없음

### C-6: 테스트

| 테스트 | 검증 내용 |
|--------|---------|
| `test_generate_returns_wav` | WAV bytes + 44100Hz + seed 반환 |
| `test_stereo_output` | 스테레오 (2채널) 확인 |
| `test_cache_hit` | 동일 prompt+duration+seed → 캐시 재사용 |
| `test_duration_clamped` | MAX_DURATION 초과 시 클램핑 |
| `test_blackwell_fallback` | FlashAttention 실패 시 graceful fallback |

---

## 영향 범위

### 변경 파일

| 파일 | 변경 유형 | Sprint |
|------|---------|--------|
| `audio/services/gpu_cache.py` | **신규** | A |
| `audio/services/tts_engine.py` | 수정 | A |
| `audio/services/music_engine.py` | 수정 | A |
| `audio/main.py` | 수정 (GPU API + lifespan + 엔진 선택) | A, C |
| `audio/config.py` | 수정 | A, C |
| `audio/tests/test_gpu_cache.py` | **신규** | A |
| `backend/services/forge_control.py` | **신규** | B |
| `backend/services/gpu_coordinator.py` | **신규** | B |
| `backend/services/generation.py` | 수정 (GpuCoordinator 래핑) | B |
| `backend/services/characters/reference.py` | 수정 | B |
| `backend/services/audio_client.py` | 수정 (GpuCoordinator 래핑) | B |
| `backend/config.py` | 수정 (GPU_COORDINATOR_*, MUSIC_* 상수) | B, C |
| `audio/services/acestep_engine.py` | **신규** | C |
| `audio/pyproject.toml` | 수정 | C |
| Frontend Studio 컴포넌트 | 수정 (UI 가드) | B |

### 변경 없는 파일 (후방 호환)

- `audio/schemas.py` — Request/Response 모델 동일
- `backend/services/video/effects.py` — BGM 믹싱 로직 무관
- `backend/services/video/builder.py` — WAV 입력만 받음 (단, GpuCoordinator 래핑 추가)

---

## 비기능 요구사항

| 항목 | 기준 |
|------|------|
| **GPU 동시 점유** | **1개 모델만** (Forge 포함 전체 순차) |
| 피크 VRAM | ≤ 16GB (단일 모델 독점) |
| TTS 첫 호출 (cold) | ≤ 30초 (Forge unload + TTS 로드) |
| TTS 연속 호출 (warm) | ≤ 2초 (cache hit) |
| Forge reload | ≤ 30초 |
| BGM 30초 생성 | ≤ 15초 (ACE-Step, 27 steps) |
| 서버 기동 시간 | ≤ 3초 (eager load 제거) |
| Blackwell 호환 | FlashAttention 실패 시 자동 fallback |

---

## 완료 기준 (DoD)

- [ ] Sprint A: Audio Server 내 TTS/Music asyncio.Lock 기반 순차 실행
- [ ] Sprint B: Backend GpuCoordinator로 Forge ↔ Audio 전체 순차 보장
- [ ] Sprint C: ACE-Step 44.1kHz 스테레오 BGM 생성 정상 동작
- [ ] 기존 TTS/BGM/이미지 생성 테스트 전체 통과
- [ ] 신규 테스트 18개 이상 추가 (A: 8 + B: 5 + C: 5)
- [ ] Backend `audio_client.py` HTTP 계약 유지
- [ ] `MUSIC_ENGINE=musicgen` 환경 변수로 MusicGen fallback 가능
- [ ] Frontend UI 가드: 동시 GPU 호출 방지
