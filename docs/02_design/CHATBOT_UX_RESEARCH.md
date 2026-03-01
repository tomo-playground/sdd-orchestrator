# 챗봇형 AI 생성 도구 UX 패턴 연구

> 조사일: 2026-03-01
> 조사 대상: 10개 AI 콘텐츠 생성 도구
> 목적: Shorts Producer 챗봇형 UX 개선을 위한 경쟁 분석
> 전 조사 문서: `AI_SHORTS_TOOL_UX_RESEARCH.md` (AI 영상 편집 도구 10종)

---

## 1. 도구별 UX 분석

### 1.1 ChatGPT Canvas — 채팅 + 사이드 에디터

**카테고리**: 대화형 문서/코드 편집기

**레이아웃 패턴**: 2-pane (좌: 채팅, 우: 에디터)
- 채팅 사이드바에서 대화하면서, 우측 에디터에서 결과물을 직접 편집
- 에디터가 열리면 채팅창은 좌측으로 축소 (약 35% 너비)
- 에디터 영역이 주 작업 공간 (약 65% 너비)

**초기 입력 → 생성 흐름**:
1. 채팅에서 "X를 작성해줘" 프롬프트 입력
2. Canvas 모드 자동 활성화 (또는 Canvas 버튼 클릭)
3. 문서/코드가 우측 에디터에 스트리밍으로 표시
4. 생성 완료 후 인라인 수정 또는 채팅으로 재지시

**스트리밍/진행 표시**:
- 타이핑 커서로 실시간 텍스트 생성 표시
- 별도 프로그레스 바 없음 — 스트리밍 자체가 피드백
- "ChatGPT is thinking..." 라벨 표시 (생성 전 단계)

**Human-in-the-Loop 개입 포인트**:
- **하이라이트 to 편집**: 특정 단락/코드 블록을 선택 → "이 부분을 수정해줘" 지시
- **숏컷 메뉴**: 우측 에디터 하단에 자주 쓰는 액션 버튼
  - 글쓰기: 길이 조정, 읽기 수준 변경, 최종 다듬기, 편집 제안
  - 코딩: 버그 수정, 로그 추가, 포트 변경, 코드 리뷰
- **버전 히스토리**: 뒤로 가기 버튼으로 이전 버전 복원 가능
- **"변경사항 표시"**: diff 하이라이트 모드

**대화형 수정 루프**:
- 채팅에서 지시 → 에디터에서 해당 부분만 업데이트 (전체 재생성 X)
- "이 함수를 리팩터링해줘" → 해당 함수만 인라인 수정
- 컨텍스트 유지: 채팅 히스토리 + 에디터 내용이 연결된 상태

**특징적 UX 결정**:
- 에디터와 채팅이 분리되어 있지만 컨텍스트 공유
- 사용자는 에디터에서 직접 타이핑도 가능 (AI 전용 에디터 X)
- 학습 곡선 낮음: Google Docs + 채팅 친숙한 UI

**한계**:
- 에디터와 채팅 간 스크롤 위치 연동 없음
- 멀티 문서 동시 편집 불가 (1 Canvas = 1 문서)

---

### 1.2 v0.dev (Vercel) — 프로토타입 생성 + 반복 대화

**카테고리**: AI UI 코드 생성기

**레이아웃 패턴**: 3-pane (좌: 채팅, 중: 프리뷰, 우: 코드)
- 채팅 입력 → 중앙 Live Preview + 우측 코드 에디터 동시 업데이트
- 탭 전환: Preview / Code / 파일 트리 (모바일에서는 스택)
- VS Code 스타일 내장 에디터 포함 (에이전트 + 프리뷰 + 설정 통합)

**초기 입력 → 생성 흐름**:
1. 자연어로 UI 설명 ("대시보드 컴포넌트 만들어줘, 사이드바 + 카드 레이아웃")
2. 스트리밍으로 React/Tailwind 코드 생성
3. 중앙 프리뷰에서 실시간 렌더링 확인
4. 채팅에서 "이 버튼 색상 파란색으로 바꿔줘" → 해당 부분만 재생성

**스트리밍/진행 표시**:
- 코드 스트리밍 중 프리뷰 동시 업데이트 (점진적 렌더링)
- 생성 중 스피너 + 코드 토큰 순차 출력
- **Design Mode**: 재프롬프팅 없이 슬라이더로 레이아웃/타이포그래피 조정

**Human-in-the-Loop 개입 포인트**:
- **인라인 피드백**: 프리뷰에서 특정 컴포넌트 클릭 → 채팅에 자동 컨텍스트 삽입
- **Design Mode 슬라이더**: 코드 생성 없이 시각적 파라미터 직접 조정
- **파일 트리 편집**: 특정 파일만 수동 편집 가능
- **Deploy 원클릭**: Vercel 배포 직행 (코드 리뷰 없이)

**대화형 수정 루프**:
- 이전 생성 결과를 컨텍스트로 유지한 채 "V3" 방식으로 버전 누적
- "이전 버전 되돌리기" 기능 (채팅 히스토리 기반)
- 특정 컴포넌트만 재생성 가능 (전체 리빌드 X)

**특징적 UX 결정**:
- 프로덕션 환경과 동일한 실행 프리뷰 (서버 사이드 API 포함)
- Next.js + Tailwind + shadcn/ui 표준화로 결과 예측성 높음
- 설계 → 코드 → 배포 파이프라인을 단일 인터페이스에서 완결

---

### 1.3 Cursor Composer — 스트리밍 diff + 승인 패턴

**카테고리**: AI 코드 에디터 (IDE 통합)

**레이아웃 패턴**: IDE 통합형 (에디터 + 우측 Composer 패널)
- VSCode 기반 에디터 전체가 주 화면
- 우측에 Composer 채팅 패널 (독립 분리 가능)
- diff는 에디터 인라인에서 직접 표시 (별도 diff 뷰어 X)

**초기 입력 → 생성 흐름**:
1. Composer 패널에서 자연어 요구사항 입력 + 파일/컨텍스트 첨부
2. AI가 멀티파일 수정 계획을 먼저 제시 (Plan 단계)
3. 각 파일에 diff (초록=추가, 빨강=삭제) 스트리밍 표시
4. 파일별 "Accept" / "Reject" 버튼으로 선택적 승인

**스트리밍/진행 표시**:
- 초당 약 250 토큰 속도로 코드 스트리밍 (기존 대비 4배 빠름)
- 멀티파일 작업 시 "파일 1/5 처리 중..." 진행 표시
- 에이전트 모드: 터미널 명령 실행 → 테스트 결과 → 자동 수정 루프 표시
- 실패 시 에러 메시지 + 자동 재시도 (최대 N회) 표시

**Human-in-the-Loop 개입 포인트**:
- **파일별 Accept/Reject**: 개별 파일 단위로 변경 수락/거부
- **Accept All / Reject All**: 전체 일괄 처리 버튼
- **부분 수락**: diff 뷰에서 특정 헝크(hunk)만 선택 적용
- **에이전트 승인 게이트**: 터미널 명령 실행 전 확인 요청
- **Undo per agent**: 에이전트별 독립 되돌리기

**대화형 수정 루프**:
- 승인 후 "이 함수 테스트도 추가해줘" → Composer가 변경 컨텍스트 유지한 채 추가 작업
- 에이전트 모드: 테스트 실패 → 자동 분석 → 수정 → 재테스트 루프 (사용자 개입 없이)
- Review Mode: 변경 사항 전체를 한 화면에서 페이지네이션으로 검토

**특징적 UX 결정**:
- diff가 실제 코드 에디터에 인라인으로 표시 (외부 도구 불필요)
- 변경 전 "확인" 없이는 코드 수정 없음 — 신뢰 기반 개입 모델
- Plan → Execute → Review 3단계 구조의 명확한 분리

---

### 1.4 Midjourney — 생성 → 선택 → 변형 분기형

**카테고리**: AI 이미지 생성기

**레이아웃 패턴**: 갤러리 기반 (Discord → 독립 웹앱으로 전환 중)
- Discord: 채팅 채널 내 그리드 이미지 출력
- 웹앱(2025): 좌측 사이드바 + 중앙 갤러리 + 우측 파라미터 패널

**초기 입력 → 생성 흐름**:
1. 텍스트 프롬프트 입력 (+ 파라미터: --ar, --style, --v, --exp)
2. 약 30-60초 후 4개 이미지 그리드 동시 생성
3. 각 이미지 하단에 U1~U4 (업스케일), V1~V4 (변형) 버튼
4. 선택 후 후속 처리 (업스케일 → 세부 조정 / 변형 → 새 그리드)

**스트리밍/진행 표시**:
- 생성 중 흐릿한 이미지가 점진적으로 선명해지는 애니메이션
- 진행률 퍼센트 표시 (Discord: "Processing... 45%")
- 웹앱: 로딩 애니메이션 + 예상 잔여 시간

**Human-in-the-Loop 개입 포인트**:
- **4-grid 선택**: 4개 중 마음에 드는 이미지 선택 (U 버튼)
- **변형 분기**: V 버튼으로 선택 이미지 기반 새 그리드 생성
- **Vary Region**: 이미지 특정 영역만 인페인팅 수정
- **웹앱 슬라이더**: Stylization(0-1000), Weirdness(0-3000) 실시간 조정
- **Omni-Reference**: 참조 이미지로 캐릭터/오브젝트 일관성 제어

**대화형 수정 루프**:
- 프롬프트 수정 → 재생성 (전통적 루프)
- **Remix Mode**: 변형 생성 시 프롬프트도 함께 수정 가능 (프롬프트 + 이미지 동시 변경)
- **Describe**: 이미지를 업로드하면 해당 이미지의 프롬프트를 역생성

**특징적 UX 결정**:
- 4-grid 모델: 한 번에 4개 옵션 제시 → 탐색 비용 감소
- 분기형 워크플로우: 하나의 생성에서 여러 방향으로 탐색 가능
- 파라미터를 프롬프트에 인라인으로 삽입 (`--ar 9:16 --v 6.1`)
- 2025년 공식 API 출시로 외부 앱 통합 가능

---

### 1.5 Runway ML — AI 영상 생성 UI

**카테고리**: 생성형 AI 비디오 (전문 크리에이터 타겟)

**레이아웃 패턴**: 워크플로우 기반 (노드 에디터 + 싱글 패널)
- 기본 모드: 단일 패널 (프롬프트 입력 + 생성 결과)
- 고급 모드: 노드 기반 비주얼 워크플로우 에디터

**초기 입력 → 생성 흐름**:
- Text-to-Video: 텍스트 프롬프트 입력 → Gen-4 선택 → 생성 (30초-2분)
- Image-to-Video: 이미지 업로드 → Motion Brush로 움직임 영역 지정 → 생성
- 키프레임: 시작/끝 이미지 설정 → 중간 모션 자동 생성

**스트리밍/진행 표시**:
- 우측 Active Runs 패널: 병렬 생성 작업 목록 + 개별 진행률
- 완료 시 해당 노드에 결과 썸네일 표시
- 실패 시 노드별 에러 표시 + 개별 재실행 버튼

**Human-in-the-Loop 개입 포인트**:
- **Motion Brush**: 캔버스에 브러시로 움직임 방향/강도 직접 지정
- **Director Mode**: 카메라 움직임 파라미터 (패닝, 틸팅, 줌) 수동 지정
- **Camera Controls**: 분수 단위 정밀 파라미터 (Advanced Camera Controls)
- **노드별 캔슬/재실행**: 파이프라인 중 특정 단계만 교체 가능
- **Aleph**: 생성된 영상 내 특정 오브젝트를 인터랙티브하게 조작

**대화형 수정 루프**:
- 노드 기반: 결과가 마음에 들지 않으면 해당 노드만 파라미터 변경 후 재실행
- 워크플로우 저장/재사용: 성공한 파이프라인을 템플릿으로 저장
- 멀티 모델 비교: 동일 프롬프트로 Gen-4 vs Gen-4 Turbo 병렬 실행

**특징적 UX 결정**:
- 노드 색상 코딩: 텍스트(주황), 이미지(핑크), 비디오(초록)
- 심플 모드 / 고급 노드 모드 분리 (초보자와 전문가 모두 수용)
- 파이프라인 전체 vs 개별 노드 실행 분리
- 영상 생성 특성상 스트리밍 불가 → "잡 큐" 방식 + Active Runs 패널로 보상

---

### 1.6 Notion AI — 문서 내 AI 대화

**카테고리**: 문서 내장형 AI 어시스턴트

**레이아웃 패턴**: 인라인 오버레이 (문서 컨텍스트 유지)
- 채팅 전용 창 없음 — 문서 편집 중 AI가 인라인으로 등장
- 문서 전체 보기를 방해하지 않는 최소 침습적(minimally invasive) 패턴

**초기 입력 → 생성 흐름**:
1. 텍스트 선택 → AI 아이콘 클릭 (또는 `/AI` 명령)
2. 팝업 메뉴에서 액션 선택 (요약, 개선, 번역, 계속 쓰기 등)
3. AI 응답이 선택 영역 바로 아래에 인라인으로 스트리밍
4. "교체" / "삽입" / "삭제" 버튼으로 결과 적용 방식 선택

**스트리밍/진행 표시**:
- 타이핑 커서 애니메이션으로 스트리밍 표시
- 페이지 전체 재렌더링 없이 해당 블록만 업데이트
- AI 응답 생성 중 다른 블록 계속 편집 가능

**Human-in-the-Loop 개입 포인트**:
- **교체 vs 삽입**: AI 결과를 기존 텍스트와 교체하거나 아래에 삽입
- **Retry**: 결과가 마음에 들지 않으면 동일 요청 재시도
- **Tone 조정**: "더 전문적으로", "더 캐주얼하게" 후속 지시
- **AI 블록**: 특정 블록을 AI로 고정 지정 — 문서 업데이트 시 자동 갱신
- **Ask AI 채팅**: 사이드바에서 문서 전체에 대한 질의응답

**대화형 수정 루프**:
- 인라인 후속 지시: "더 짧게" → 동일 위치에서 바로 수정
- 컨텍스트 자동 감지: 선택 범위 + 주변 문서 내용을 AI가 자동 읽음
- 자율 에이전트(2025): 문서 전체를 읽고 자동 리서치/작성

**특징적 UX 결정**:
- 채팅 패러다임이 아닌 "문서 편집의 연장선"으로 AI 위치
- 최소 UI: 팝업 메뉴 크기를 최소화하여 문서 맥락 유지
- Precision Assistant 철학: 미시적 지원 (문장, 단락 수준)
- 2025년부터 Business 플랜에 통합 — 별도 구독 X

---

### 1.7 Google AI Studio — Gemini 대화형 프롬프트

**카테고리**: AI 개발자 실험/프로토타이핑 플랫폼

**레이아웃 패턴**: 개발자 도구형 4-영역 분할
- 좌측 사이드바: 히스토리, 파일, 모델 선택
- 중앙 좌측: 시스템 프롬프트(System Instruction) 편집 영역
- 중앙 우측: 채팅 대화 창
- 우측 패널: 파라미터 조정 (Temperature, Top-P, Max Tokens 등)
- 상단 탭: Prompt / Tune & Test 전환

**초기 입력 → 생성 흐름**:
1. 시스템 인스트럭션 설정 (좌측)
2. 모델 선택 (Gemini 2.0 Flash, Pro 등) + 파라미터 조정 (우측)
3. 채팅창에서 프롬프트 입력 → 스트리밍 응답
4. "Get Code" 버튼: 현재 프롬프트를 API 호출 코드로 즉시 변환

**스트리밍/진행 표시**:
- 마크다운 렌더링과 동시에 스트리밍 (코드 블록 포함)
- 멀티모달: 이미지/오디오/비디오 입력 시 파일 처리 중 인디케이터
- 함수 호출(Function Calling) 실행 시 호출 로그 인라인 표시

**Human-in-the-Loop 개입 포인트**:
- **파라미터 실시간 조정**: Temperature 슬라이더 변경 → 즉시 재생성 (실험용)
- **System Instruction 편집**: AI 성격/역할을 언제든 수정
- **Function Calling 결과 승인**: 함수 실행 결과를 직접 수정 후 계속
- **멀티턴 편집**: 특정 이전 턴을 수정 후 재실행 가능
- **"Run" vs "Stream" 토글**: 배치 실행 vs 스트리밍 선택

**대화형 수정 루프**:
- Few-shot 예시 추가 → 즉각적인 품질 변화 확인 (실험 루프)
- 멀티모달 프롬프트: 이전 생성 이미지를 다음 턴 입력으로 첨부
- Grounding with Search: AI가 실시간 웹 검색 후 근거 포함 응답

**특징적 UX 결정**:
- "개발자가 모델을 이해하고 통제하는" 철학 — 투명성 최우선
- 모든 파라미터를 화면에 노출 (일반 채팅과 차별화)
- Generative UI 실험: 프롬프트에 따라 UI 자체가 동적으로 생성
- Google Search AI Mode와 기술 공유 (Dynamic View 실험)

---

### 1.8 Gamma.app — AI 프레젠테이션 생성

**카테고리**: AI 프레젠테이션/웹페이지 생성기

**레이아웃 패턴**: 위자드 기반 → 에디터 분기
- 1단계 위자드: 주제 입력 → 아웃라인 생성 → 테마 선택 → 생성
- 2단계 에디터: 슬라이드 썸네일(좌) + 편집 캔버스(중) + AI 패널(우)

**초기 입력 → 생성 흐름**:
1. 주제 한 줄 입력 ("스타트업 IR 덱 만들어줘")
2. AI가 10-12장 아웃라인 자동 생성 → 사용자 승인/수정
3. 테마(색상, 폰트) 선택 → "Generate" 클릭
4. 약 40초 후 완성 덱 생성 (이미지, 레이아웃, 카피 포함)

**스트리밍/진행 표시**:
- 생성 중 슬라이드가 순차적으로 나타나는 애니메이션
- 각 슬라이드 생성 시 로딩 펄스 효과
- 전체 진행률 표시 없음 — "곧 완성됩니다" 메시지

**Human-in-the-Loop 개입 포인트**:
- **아웃라인 편집**: 생성 전 슬라이드 순서/제목 수정 가능
- **인라인 AI 재생성**: 특정 슬라이드 클릭 → "이 슬라이드 다시 만들어줘"
- **Gamma Agent**: 전체 덱을 한 명령으로 재설계
- **카드 레이아웃 선택**: AI가 제안한 레이아웃 중 원하는 것 선택
- **이미지 교체**: AI 생성 이미지를 Unsplash/업로드로 교체

**대화형 수정 루프**:
- 에디터 우측 AI 패널에서 자연어 지시
- "3번 슬라이드 데이터를 차트로 바꿔줘" → 해당 슬라이드만 수정
- 실시간 협업: 팀원이 동시 댓글/편집 (Google Slides 스타일)

**특징적 UX 결정**:
- 아웃라인 단계를 사용자가 반드시 거치게 설계 — 결과 예측성 향상
- "Soft UX": 생성 흐름이 "ChatGPT처럼 친숙"하게 설계
- 테마 선택이 아웃라인과 생성 사이에 배치 — 기대 형성 시간 활용
- 40초 생성 = 사용자 인식상 "빠름" (Fliki 등과 비슷한 완성도)

---

### 1.9 Suno AI — AI 음악 생성

**카테고리**: 텍스트 → 완성 음악 생성기

**레이아웃 패턴**: 심플 패널 (중앙 생성, 좌측 히스토리)
- 좌측 사이드바: 생성 히스토리, 플레이리스트
- 중앙 Create 패널: Simple / Custom 모드 탭
- 하단 플레이어: 생성된 트랙 재생 컨트롤

**초기 입력 → 생성 흐름**:
- Simple Mode: 한 줄 설명 입력 ("신나는 K-Pop 여름 노래") → Create 클릭
- Custom Mode: 가사 직접 입력 + 스타일 설명 + 제목 설정
- 30-60초 후 **동시에 2개 버전** 생성 (A/B 비교 제공)

**스트리밍/진행 표시**:
- API: Submit-then-poll 패턴 (잡 ID 반환 → 폴링으로 완료 확인)
- UI: 생성 중 웨이브폼 로딩 애니메이션 (음악 특성 반영)
- 생성 완료 즉시 자동 재생 (최초 8초 미리듣기)
- 2개 버전 중 선택: 트랙 A / 트랙 B 개별 재생 가능

**Human-in-the-Loop 개입 포인트**:
- **A/B 선택**: 2개 생성 중 마음에 드는 버전 선택
- **Extend**: 생성된 트랙 끝을 이어서 확장 (최대 8분)
- **Section Rewrite**: 특정 구간(8마디)만 재생성
- **Waveform 편집**: 핑크 웨이브폼 셀렉터로 구간 크롭
- **Stem Editing**: 보컬/드럼/신스 레이어별 분리 편집 (v4.5+)

**대화형 수정 루프**:
- 텍스트 프롬프트 수정 → 새 버전 생성 (히스토리 유지)
- Extend: 기존 트랙을 기반으로 새 섹션 추가 (연속성 유지)
- Suno Studio (DAW): 타임라인 편집, MIDI 익스포트, 레이어링

**특징적 UX 결정**:
- 2개 동시 생성: 선택지 제공으로 사용자 만족도 증가
- 웨이브폼 시각화: 음악 생성 도구 특성에 맞는 도메인 메타포
- Custom Mode는 숨겨진 탭으로 — 초보자가 Simple부터 시작하도록 유도
- 프롬프트 엔지니어링 없이도 고품질 결과 (낮은 진입 장벽)

---

### 1.10 Kling AI / Pika — AI 비디오 생성 UI

**카테고리**: 텍스트/이미지 → AI 비디오 생성기

**레이아웃 패턴**: 폼 기반 단일 패널 (Kling) / 씬 기반 (Pika)

**Kling AI**:
- 중앙 생성 패널: 텍스트 + 이미지 입력 + 파라미터
- 파라미터: Creativity/Relevance 슬라이더, 영상 길이(5/10초), 화면 비율
- 생성 결과: 갤러리 형태로 쌓임 (히스토리 관리)

**Pika Labs**:
- "Scene Ingredients": 텍스트 + 이미지 + 오디오를 씬 단위로 조합
- "PikaFrames": 시작 프레임 + 종료 프레임 설정 → 중간 모션 생성
- 초보자 친화적 인터페이스 (Kling보다 단순)

**초기 입력 → 생성 흐름**:
1. 텍스트 프롬프트 + (선택) 참조 이미지 업로드
2. 파라미터 설정 (비율, 길이, 창의성 강도)
3. "Generate" 클릭 → 잡 큐 등록
4. 30초-3분 후 영상 완성 → 자동 갤러리 추가

**스트리밍/진행 표시**:
- 큐 위치 표시 ("Processing... 3rd in queue")
- 생성 중 프레임 미리보기 (일부 도구)
- 완료 시 갤러리에 썸네일 표시 + 자동 재생

**Human-in-the-Loop 개입 포인트**:
- **Creativity 슬라이더**: AI의 자유도 실시간 조정 (Kling)
- **PikaFrames**: 첫 프레임/마지막 프레임 직접 지정 (Pika)
- **영상 편집**: 생성 후 음악 추가, 캡션 오버레이, 클립 결합
- **Style Transfer**: 생성 영상에 화풍 필터 적용

**특징적 UX 결정**:
- Kling: 제어 중심 — 파라미터를 많이 노출하여 전문 사용자 타겟
- Pika: 접근성 중심 — "씬 재료" 메타포로 직관적 조합
- 두 도구 모두 잡 큐 방식 (스트리밍 불가 특성 수용)
- AI 아바타(Kling) vs 씬 합성(Pika): 타겟 용도 분리

---

## 2. 패턴별 비교 분석

### 2.1 레이아웃 패턴 분류

| 패턴 | 도구 | 채팅 위치 | 결과 위치 | 특징 |
|------|------|----------|----------|------|
| **2-pane (채팅 + 에디터)** | ChatGPT Canvas | 좌 35% | 우 65% | 에디터가 주, 채팅이 보조 |
| **3-pane (채팅 + 프리뷰 + 코드)** | v0.dev | 좌 | 중앙 + 우 | 프로덕션 프리뷰 강조 |
| **IDE 통합형** | Cursor Composer | 우측 패널 | 에디터 인라인 | diff가 코드에 직접 표시 |
| **갤러리 기반** | Midjourney, Suno, Kling/Pika | 하단/없음 | 중앙 갤러리 | 결과 탐색이 핵심 |
| **노드 워크플로우** | Runway ML | 없음 | 노드별 출력 | 파이프라인 자체가 UI |
| **인라인 오버레이** | Notion AI | 팝업 | 문서 내 인라인 | 맥락 이탈 최소화 |
| **개발자 도구형** | Google AI Studio | 중앙 우 | 중앙 우 | 파라미터 패널 함께 노출 |
| **위자드 → 에디터** | Gamma.app | 우측 AI 패널 | 슬라이드 캔버스 | 생성 전 아웃라인 단계 강제 |

**핵심 인사이트**: 레이아웃은 "무엇이 메인인가"를 결정한다.
- 코드/문서 도구: 결과물이 메인, 채팅이 보조 (Canvas, v0, Cursor)
- 이미지/영상 도구: 갤러리/결과가 메인, 입력이 하단에 배치 (Midjourney, Suno, Kling)
- 문서 통합형: 채팅 UI 자체를 숨기고 인라인화 (Notion)

---

### 2.2 스트리밍/진행 표시 전략

| 전략 | 도구 | 구현 방식 | 적합한 생성 유형 |
|------|------|----------|----------------|
| **실시간 토큰 스트리밍** | Canvas, v0, Gemini | 타이핑 커서 + 점진적 텍스트 | 텍스트/코드 생성 |
| **점진적 렌더링** | v0.dev 프리뷰 | 코드 스트리밍과 동시에 UI 렌더 | React 컴포넌트 |
| **흐릿함 → 선명 애니메이션** | Midjourney | 이미지가 점차 디테일 생성 | 이미지 생성 |
| **웨이브폼 로딩** | Suno AI | 음악 특성 반영한 파형 애니메이션 | 오디오 생성 |
| **순차 슬라이드 표시** | Gamma.app | 슬라이드가 하나씩 등장 | 프레젠테이션 |
| **Active Runs 패널** | Runway ML | 병렬 잡 목록 + 개별 진행률 | 영상 생성 (비동기) |
| **단계별 텍스트 메시지** | Cursor Agent | "파일 분석 중", "수정 적용 중" | 코드 에이전트 |
| **잡 큐 위치** | Kling, Pika | "3rd in queue" | AI 비디오 (긴 처리) |

**핵심 인사이트**: 스트리밍 가능 여부가 UX를 결정한다.
- 텍스트/코드: 스트리밍 가능 → 진행 자체가 피드백 (별도 프로그레스 바 불필요)
- 이미지/영상: 스트리밍 불가 → 도메인 메타포로 보상 (흐릿함 → 선명, 웨이브폼)

---

### 2.3 Human-in-the-Loop 개입 패턴

| 개입 유형 | 도구 | 트리거 | UX 패턴 |
|----------|------|--------|---------|
| **선택 (n개 중 1개)** | Midjourney, Suno | 생성 완료 후 | 그리드/A-B 버튼 |
| **diff 승인** | Cursor Composer | 코드 변경 제안 시 | Accept/Reject 인라인 버튼 |
| **영역 지정** | Runway Motion Brush | 생성 전 설정 | 캔버스 브러시 도구 |
| **아웃라인 편집** | Gamma.app | 생성 전 단계 | 인라인 텍스트 편집 |
| **하이라이트 → 지시** | Canvas, Notion | 선택 후 AI 호출 | 선택 + 팝업 메뉴 |
| **파라미터 조정** | Google AI Studio, Kling | 언제든지 | 슬라이더/드롭다운 |
| **에이전트 게이트** | Cursor Agent | 위험 작업 전 | 확인 팝업 |
| **구간 지정 재생성** | Suno Section Rewrite | 편집 단계 | 웨이브폼 범위 선택 |

**핵심 인사이트**: 개입 유형은 "제어 vs 탐색"의 트레이드오프.
- **선택형** (Midjourney, Suno): AI에게 많은 자율성, 사용자는 큐레이션
- **diff 승인형** (Cursor): AI가 변경 제안, 사람이 최종 결정 — 신뢰 유지
- **파라미터형** (Google AI Studio, Kling): 전문가가 세밀하게 제어

---

### 2.4 대화형 수정 루프 비교

| 도구 | 루프 유형 | 컨텍스트 유지 | 부분 수정 가능 |
|------|----------|-------------|--------------|
| ChatGPT Canvas | 채팅 → 에디터 부분 업데이트 | 완전 유지 | 단락/코드 블록 단위 |
| v0.dev | 채팅 → 컴포넌트 재생성 | 완전 유지 | 컴포넌트 단위 |
| Cursor Composer | 채팅 → 파일별 diff | 완전 유지 | 파일/헝크 단위 |
| Midjourney | 프롬프트 수정 → 재생성 | 부분 (Remix Mode) | 이미지 영역 (Vary Region) |
| Runway ML | 노드 파라미터 수정 → 재실행 | 워크플로우 유지 | 노드 단위 |
| Notion AI | 인라인 후속 지시 | 문서 컨텍스트 | 블록 단위 |
| Gamma.app | AI 패널 지시 → 슬라이드 수정 | 덱 전체 유지 | 슬라이드 단위 |
| Suno AI | 새 프롬프트 → 새 트랙 | 히스토리 유지 | Extend/Section |

---

## 3. 핵심 설계 원칙 종합

### 3.1 "메인은 결과물, 채팅은 도구다"

생성 AI 도구에서 채팅 UI는 목적이 아닌 수단이다. 가장 성숙한 도구들은 생성 결과물(에디터, 캔버스, 갤러리)이 화면의 주인공이고, 채팅은 그것을 제어하는 도구로 위치한다.

- ChatGPT Canvas: 에디터 65%, 채팅 35%
- v0.dev: 프리뷰가 중심, 채팅은 좌측
- Notion AI: 채팅 UI 자체를 없애고 인라인화

### 3.2 "스트리밍이 가능하면 반드시 스트리밍하라"

텍스트/코드 생성에서 스트리밍은 선택이 아닌 필수다. 스트리밍 자체가 진행 피드백이며, 사용자의 인지된 대기 시간을 극적으로 감소시킨다. 스트리밍 불가능한 영역(이미지, 영상, 음악)은 도메인에 맞는 시각적 메타포로 대체한다.

### 3.3 "개입 포인트는 명확하게 설계하라"

Human-in-the-loop의 핵심은 "언제, 어디서, 어떻게" 개입할지 사용자가 예측할 수 있어야 한다는 것이다.
- Cursor: diff 제안 → Accept/Reject (명확한 결정 포인트)
- Midjourney: 4-grid → U/V 버튼 (명확한 선택 포인트)
- Notion: 텍스트 선택 → AI 팝업 (명확한 트리거)

### 3.4 "n개 선택지로 탐색 비용을 낮춰라"

단일 결과 생성보다 복수 결과 제시가 사용자 만족도를 높인다.
- Midjourney: 4개 그리드
- Suno: 2개 버전 동시 생성
- v0.dev: Design Mode로 파라미터 변형 탐색

### 3.5 "아웃라인/계획 단계를 명시하라"

복잡한 생성물(프레젠테이션, 코드 리팩터링)은 실행 전 계획 단계를 사용자가 검토하도록 설계하면 결과 예측성이 높아지고 재생성 횟수가 줄어든다.
- Gamma: 아웃라인 → 테마 → 생성
- Cursor: Plan → Execute → Review
- Runway ML: 워크플로우 설계 → 실행

---

## 4. Shorts Producer 적용 시사점

### 4.1 파이프라인 진행 표시 개선 (즉시)

현재 LangGraph 17-노드 파이프라인의 진행이 불투명하다. 다음 전략 적용 권장:

| 현재 | 개선안 | 참고 도구 |
|------|--------|----------|
| 단순 스피너 | 단계별 텍스트 메시지 스트리밍 | Cursor Agent |
| 전체 로딩 | 노드별 진행 표시 (Director → Writer → Cinematographer 등) | Runway Active Runs |
| 에러 시 전체 실패 | 실패 노드만 표시 + 재시도 버튼 | Runway ML 노드별 에러 |

제안 UX:
```
[생성 중] Director 분석 완료
[생성 중] Writer 스크립트 작성 중...
[생성 중] Cinematographer 씬 설정 중 (3/8)...
```

### 4.2 스토리보드 생성 후 수정 루프 (단기)

현재 생성 완료 후 씬별 수정이 분산되어 있다. Canvas/v0 패턴 적용:

| 현재 | 개선안 | 참고 도구 |
|------|--------|----------|
| 씬별 개별 수정 | 채팅 → 전체 스토리보드 업데이트 | ChatGPT Canvas |
| 재생성 = 전체 재실행 | 특정 씬만 재생성 가능 | v0.dev 컴포넌트 단위 |
| 텍스트 수정 + 이미지 수정 분리 | 단일 채팅 인터페이스에서 통합 수정 | Notion AI 인라인 |

### 4.3 이미지 생성 결과 선택 UX (단기)

현재 씬별 이미지 1개 생성이다. Midjourney/Suno 패턴 적용:

| 현재 | 개선안 | 참고 도구 |
|------|--------|----------|
| 단일 이미지 생성 | 2-4개 이미지 동시 생성 + 선택 | Midjourney 4-grid |
| 재생성 = 단일 결과 교체 | 이전 결과 히스토리 유지 | Suno 히스토리 |
| 이미지 진행 표시 없음 | 흐릿함 → 선명 점진 로딩 | Midjourney 프로그레스 |

### 4.4 스크립트 편집 인라인 AI (중기)

현재 스크립트 편집이 에디터 외부에서 이루어진다. Notion AI 패턴 적용:

| 현재 | 개선안 | 참고 도구 |
|------|--------|----------|
| 스크립트 수동 편집 | 텍스트 선택 → AI 개선 팝업 | Notion AI 인라인 |
| 전체 재생성 | 씬 텍스트 하이라이트 → 해당 씬만 재생성 | Canvas 하이라이트 |
| 채팅과 에디터 분리 | 스크립트 에디터 내 AI 인라인 작업 | v0.dev Design Mode |

### 4.5 레이아웃 개선 (장기)

| 현재 | 개선안 | 참고 패턴 |
|------|--------|----------|
| Studio 좌측 설정 + 우측 스토리보드 | 스토리보드 중심 + 우측 AI 채팅 패널 | Canvas 2-pane |
| 단일 생성 흐름 | 심플 모드 / 고급 모드 분리 | Runway ML, Suno |
| 설정 → 생성 → 편집 선형 흐름 | 생성 후 대화형 수정 루프 연결 | v0.dev 반복 대화 |

---

## 5. 레이아웃 와이어프레임 개념도

### 5.1 현재 Studio 레이아웃 (개념)

```
┌─────────────────────────────────────────────────────┐
│ [NavBar]                                            │
├─────────┬───────────────────────────────────────────┤
│ 설정     │ 스토리보드 씬 목록                          │
│ 패널     │ [씬1] [씬2] [씬3] ...                      │
│ (좌측)   │                                           │
│ - 시리즈  │ 씬 카드: 이미지 + 텍스트                    │
│ - 컨텍스트│                                           │
│ - AI 옵션│ [생성] [재생성] [편집]                      │
└─────────┴───────────────────────────────────────────┘
```

### 5.2 Canvas 패턴 적용 후 (제안)

```
┌─────────────────────────────────────────────────────┐
│ [NavBar]                                            │
├──────────────────┬──────────────────────────────────┤
│ AI 채팅 패널      │ 스토리보드 (메인)                   │
│ (좌 35%)         │ (우 65%)                           │
│                  │                                   │
│ > 파이프라인 로그  │ [씬1] [씬2] [씬3] ...              │
│   Director 완료   │                                   │
│   Writer 진행 중  │ ┌─────────┐ ┌─────────┐          │
│                  │ │ 이미지   │ │ 이미지   │          │
│ > 채팅 입력       │ │ [재생성] │ │ [재생성] │          │
│   "3번 씬 다시..."│ └─────────┘ └─────────┘          │
│                  │                                   │
│ [메시지 입력창]    │ [전체 재생성] [이미지 생성] [렌더]   │
└──────────────────┴──────────────────────────────────┘
```

---

## Sources

- [ChatGPT Canvas Review 2025 - Skywork](https://skywork.ai/blog/chatgpt-canvas-review-2025-features-coding-pros-cons/)
- [Introducing Canvas - OpenAI](https://openai.com/index/introducing-canvas/)
- [Critical UX Feedback on Canvas - OpenAI Community](https://community.openai.com/t/critical-ux-feedback-on-chatgpt-canvas-major-limitations-and-suggestions-for-improvement/1226867)
- [v0.dev - Vercel](https://v0.app/)
- [AI-powered prototyping with design systems - Vercel Blog](https://vercel.com/blog/ai-powered-prototyping-with-design-systems)
- [Vercel v0 Review 2025 - Skywork](https://skywork.ai/blog/vercel-v0-review-2025-ai-ui-code-generation-nextjs/)
- [Cursor 2.0 Ultimate Guide 2025 - Skywork](https://skywork.ai/blog/vibecoding/cursor-2-0-ultimate-guide-2025-ai-code-editing/)
- [Cursor Review - Docs](https://cursor.com/docs/agent/review)
- [Cursor Composer Practical Guide - Igor's Techno Club](https://igorstechnoclub.com/cursor-composer-a-practical-guide-with-best-practices/)
- [Midjourney 2026 Guide - AI Tools DevPro](https://aitoolsdevpro.com/ai-tools/midjourney-guide/)
- [UX Roundup: Midjourney Usability - UX Tigers](https://www.uxtigers.com/post/ux-roundup-20250512)
- [Runway ML Gen-3 - RunwayML](https://runwayml.com/research/introducing-gen-3-alpha)
- [RunwayML Review 2025 - Skywork](https://skywork.ai/blog/runwayml-review-2025-ai-video-controls-cost-comparison/)
- [Runway Motion Brush + Camera Control](https://academy.runwayml.com/gen2/motion-brush-camera-control)
- [Notion AI Inline Guide 2025 - Eesel](https://www.eesel.ai/blog/notion-ai-inline)
- [Where should AI sit in your UI? - UX Collective](https://uxdesign.cc/where-should-ai-sit-in-your-ui-1710a258390e)
- [Google AI Studio Quickstart - Google AI](https://ai.google.dev/gemini-api/docs/ai-studio-quickstart)
- [Google AI Studio Guide 2025 - Humai Blog](https://www.humai.blog/google-ai-studio-gemini-guide-2025/)
- [Generative UI Research - Google Research](https://research.google/blog/generative-ui-a-rich-custom-visual-interactive-user-experience-for-any-prompt/)
- [Gamma App Review 2025 - Skywork](https://skywork.ai/blog/skypage/en/Gamma-App-In-Depth-Review-2025-The-Ultimate-Guide-to-AI-Presentations/1973913493482172416)
- [Suno v4.5 Interface Guide 2025](https://www.0580rc.com/ai-chat/suno-v45-interface-guide-2025/)
- [Suno Studio Tutorial - Medium](https://medium.com/@J.S.Matkowski/suno-studio-tutorial-from-prompt-to-production-acfb31c0bcca)
- [Kling AI Review 2025 - AI Video Generators Free](https://aivideogeneratorsfree.com/review-ai-video-tools/kling-ai-review-guide)
- [Pika vs Kling 2025 - FahimAI](https://www.fahimai.com/pika-vs-kling)
- [The Shape of AI - UX Patterns](https://www.shapeof.ai/)
- [Beyond Chat: AI UI Design Patterns - Artium](https://artium.ai/insights/beyond-chat-how-ai-is-transforming-ui-design-patterns)
- [Human-in-the-Loop AI in 2025 - Ideafloats](https://blog.ideafloats.com/human-in-the-loop-ai-in-2025/)
- [Agentic AI Design Patterns - AufaitUX](https://www.aufaitux.com/blog/agentic-ai-design-patterns-enterprise-guide/)
