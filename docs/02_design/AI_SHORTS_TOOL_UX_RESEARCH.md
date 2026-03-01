# AI Shorts/Short-Form Video Tool UX Pattern Research

> 조사일: 2026-02-28
> 조사 대상: 10개 AI 영상 제작 도구
> 목적: Shorts Producer UX 개선을 위한 경쟁 분석

---

## 1. 도구별 UX 분석

### 1.1 Opus Clip — AI 쇼츠 리퍼포징

**카테고리**: 긴 영상 -> 짧은 클립 자동 추출

**핵심 워크플로우**: Link Paste -> AI 분석 -> 클립 생성/점수화 -> 편집 -> 게시
- 영상 URL 입력 또는 파일 업로드 (드래그앤드롭)
- AI가 자동으로 하이라이트 구간 감지 + Virality Score 부여
- 캡션 자동 생성 (97%+ 정확도, 20개 언어)
- 원클릭 소셜 미디어 게시 (TikTok, YouTube Shorts, Instagram)

**설정 패널**: 업로드 직후 인라인 설정
- Credit Saver 슬라이더 (처리 구간 제한)
- 클립 길이 선택기
- 토픽 필터 (AI 집중 주제 지정)
- 캡션 템플릿 선택기 (폰트, 색상, 애니메이션)

**온보딩**: 2스텝 (가입 -> URL 붙여넣기)
- 가입 즉시 메인 대시보드 진입
- 히어로 영역에 "Drop a video link" 입력 필드가 바로 노출
- 데모 옵션 3개 (Vlog, Sports, Podcast) 제공

**에러 처리**: 업로드 실패 시 재시도 메커니즘
- 파일 포맷 제한 안내 (MP4, MOV, WEBM)

**특징적 UX 패턴**:
- Virality Score 대시보드: 데이터 기반 의사결정 지원
- 자동 리프레이밍 (가로 -> 세로 자동 변환)
- 예상 시간 표시기를 통한 처리 진행 상황 제공

---

### 1.2 Submagic — AI 숏폼 편집

**카테고리**: 숏폼 전용 AI 편집기

**핵심 워크플로우**: Upload -> AI 자동 편집 -> 커스터마이즈 -> Export
- 영상 업로드 후 AI가 하이라이트 감지, 캡션 추가, 포맷 조정
- 텍스트 기반 편집: 트랜스크립트를 편집하면 영상이 자동 변경
- 비트 감지 + 음악 싱크 자동화

**설정 패널**: 인라인 (편집기 내장)
- 캡션 스타일 프리셋 선택
- 감정 키워드 자동 하이라이트 (수동 조정 불필요)
- 톤 변화/화자 전환 자동 감지

**온보딩**: 1스텝 (업로드)
- "3-click process" 표방
- 템플릿 라이브러리에서 시작 가능

**에러 처리**: 상세 불명 (웹 기반 플랫폼 표준 패턴 추정)

**특징적 UX 패턴**:
- 타임라인 제거: 트랜스크립트가 곧 편집 인터페이스
- 자동 무음 구간 제거
- 4K/60fps 고품질 출력

---

### 1.3 Vizard AI — AI 쇼츠 제작

**카테고리**: 긴 영상 -> 소셜 클립 변환

**핵심 워크플로우**: Upload -> AI Scene Detection -> Clip 생성 -> 협업 편집 -> 게시
- AI 씬 감지로 자동 하이라이트 추출
- 실시간 협업 기능 (팀 워크플로우)
- 직접 소셜 미디어 스케줄링 (TikTok, YouTube, LinkedIn)

**설정 패널**: 탭 기반 대시보드
- 업로드, 프로젝트, 협업 도구, 튜토리얼 가이드 탭
- 깔끔한 구조화된 대시보드

**온보딩**: 3스텝 이하 (가입 -> 업로드 -> 자동 클립)
- ease-of-use 평점 4.9/5.0

**에러 처리**: 상세 불명

**특징적 UX 패턴**:
- AI Studio: 텍스트 -> 비디오 + 이미지 생성을 편집기 내에서 통합
- 씬 감지 자동화로 수동 리뷰 불필요
- 화면 녹화 기능 내장 (튜토리얼 제작용)

---

### 1.4 InVideo AI — 채팅 기반 AI 영상 제작

**카테고리**: 프롬프트 -> 완성 영상 (올인원)

**핵심 워크플로우**: Prompt 입력 -> AI 스크립트/영상 자동 생성 -> Magic Edit -> Export
- 자연어 프롬프트로 영상 생성 (스크립트, 음성, 미디어, 자막 포함)
- "Magic Box" 채팅 기반 편집: "이 씬 삭제해줘", "악센트 바꿔줘"
- OpenAI Sora 2 + Google VEO 3.1 통합

**대본 생성 UX**: **채팅 기반** (핵심 차별점)
- 프롬프트에 workflow, topic, duration, style, voice, article link 포함
- AI가 스크립트 자동 생성 -> 유저가 자연어로 수정 지시
- "Edit like you think" 철학

**설정 패널**: 프롬프트 입력 후 인라인 커스터마이즈
- 배경 음악, 보이스오버 유형/악센트 선택
- 워터마크 텍스트 추가
- iStock 미디어 통합

**진행 상태 표시**: 실시간 진행 피드백
- 단계별 상태 메시지: "Replacing the cat" -> "Done 1/1"
- 멀티 스테이지 프로세스의 투명한 진행 상황

**온보딩**: 1스텝 (프롬프트 입력)
- 빈 캔버스 대신 프롬프트 입력창이 시작점
- 카테고리별 템플릿 갤러리 (Trending, Money Shot, VFX House)
- "Generate" 원클릭 버튼

**에러 처리**: 채팅 인터페이스 내 인라인 응답

**특징적 UX 패턴**:
- 채팅 = 편집기: 별도 편집기 UI 없이 대화로 수정
- 플랫폼별 최적화 옵션 (YouTube, Instagram, TikTok, Facebook)
- 월 800만 영상 생성 규모

---

### 1.5 Descript — AI 영상 편집

**카테고리**: 텍스트 기반 영상 편집기

**핵심 워크플로우**: 영상 Import -> 자동 트랜스크립트 -> 텍스트 편집 = 영상 편집
- 영상을 텍스트로 변환, 텍스트 편집이 곧 영상 편집
- 3가지 뷰 모드: 스크립트 뷰, 캔버스 뷰, 타임라인 뷰
- Underlord AI 코에디터: 자연어 지시로 자동 편집

**대본 생성 UX**: **텍스트 기반 (하이브리드)**
- 자동 트랜스크립트가 편집의 기반
- AI Underlord에 자연어 지시 가능
- 워드/슬라이드와 유사한 친숙한 인터랙션

**설정 패널**: 멀티모드 (스크립트 + 캔버스 + 타임라인)
- 스크립트 뷰: 텍스트 문서 스타일 편집
- 캔버스 뷰: 시각적 레이아웃 편집
- 타임라인 뷰: 전통적 멀티트랙 편집

**진행 상태 표시**: 글로벌 프로그레스 바 + 마커
- 드래그 가능한 프로그레스 바 (구간 이동)
- 챕터 마커, 코멘트가 프로그레스 바에 컬러 라인으로 표시
- 번역 작업 시 사이드바에 실시간 진행 인디케이터

**온보딩**: 3스텝 (가입 -> Import -> 편집)
- 6-step 비기너 튜토리얼 제공

**에러 처리**: 스마트 재시도
- 업로드 실패 시 자동 재시도 (네트워크 불안정 대응)
- 실시간 업로드 진행 표시

**특징적 UX 패턴**:
- "문서 편집하듯 영상 편집" — 학습 곡선 최소화
- 실시간 협업 (Google Docs 스타일)
- Adobe Premiere/Final Cut Pro 타임라인 내보내기
- 원클릭 필러 워드 제거 (73개 "um" 한번에 삭제)

---

### 1.6 CapCut — 틱톡 영상 편집

**카테고리**: 범용 모바일/웹 영상 편집기

**핵심 워크플로우**: Template 선택 또는 빈 프로젝트 -> 멀티트랙 타임라인 편집 -> Export
- 템플릿 갤러리에서 시작 (탭 -> 클립 Import -> 자동 편집)
- 멀티트랙 편집: 비디오, 오디오, 이펙트, 텍스트 레이어
- AI 비트 감지 + 자동 컷

**설정 패널**: 우측 패널 + 하단 타임라인
- 좌측 패널: Templates, AI Tools 메뉴
- 우측 패널: AI 편집 도구 (안정화, 플리커 제거, 자동 리프레임, 노이즈 감소 등)
- 하단: 색상 코딩된 멀티트랙 타임라인

**온보딩**: 2스텝 (템플릿 선택 -> 클립 Import)
- 30+ AI 템플릿 (교육, 프로모션, 튜토리얼)
- 검색 필터: "AI" 키워드로 AI 템플릿 필터링
- 템플릿 팝업: 제목, 클립 수, 길이, 사용 횟수, 비율 표시

**에러 처리**: 상세 불명

**특징적 UX 패턴**:
- 색상 코딩 타임라인: 비디오(파란색), 오디오(초록색), 이펙트(보라색), 텍스트(노란색)
- 원탭 AI 기능: 배경 제거, 자동 캡션, 비트 싱크
- 방대한 템플릿 라이브러리가 진입 장벽 낮춤
- 모바일/데스크톱/웹 크로스 플랫폼

---

### 1.7 Fliki — AI 텍스트 -> 영상

**카테고리**: 텍스트/아이디어 -> 완성 영상

**핵심 워크플로우**: Idea Input -> AI 스크립트 + 비주얼 자동 생성 -> 커스터마이즈 -> Export
- 다양한 입력 방식: 텍스트, URL, 블로그, PPT
- AI가 스크립트 생성 + 비주얼 자동 매칭
- Editor Copilot: 씬 간 음성 타이밍 자동 조정

**대본 생성 UX**: **4단계 위자드**
1. Idea Input: 아이디어 + 톤 선택
2. Voice Selection: AI 음성 + 언어/지역 선택
3. Customization: 폰트, 색상, 비주얼 조정
4. Preview & Export: MP4 출력

**설정 패널**: 좌측 사이드바 + 중앙 에디터
- 좌측 사이드바: 음성 목록, 내비게이션
- 중앙: 텍스트 에디터 (스크립트 포맷팅, 섹션 구분, 포즈/강조 마커)
- 언어 드롭다운, AI 음성 선택기

**온보딩**: 2스텝 (2개 질문)
- 질문 1: 배경/직업
- 질문 2: 콘텐츠 유형
- 이후 바로 에디터 진입

**에러 처리**: 상세 불명

**특징적 UX 패턴**:
- 최소한의 온보딩 (질문 2개)
- 자동 비주얼 매칭 (씬 기반)
- 텍스트 에디터에서 포즈/강조 직접 마킹 가능
- 다양한 입력 포맷 지원 (텍스트, URL, PPT)

---

### 1.8 Pictory — AI 영상 생성

**카테고리**: 텍스트/스크립트 -> 영상 변환

**핵심 워크플로우**: Text Input -> AI 씬 분할 -> Storyboard -> 편집 -> Export
- 텍스트, 블로그, URL, 프롬프트로 시작
- AI가 텍스트를 씬 단위로 자동 분할 + 비주얼 매칭
- 드래그앤드롭 스토리보드 편집

**설정 패널**: 우측 패널 (Scene Settings)
- 우측 패널: 씬별 설정 (AI 자동 씬 분할, 비주얼 자동 선택)
- Smart Layouts: AI가 씬 유형 분류 (Title, List, Numbers, Quotes, Emphasis, Default)
- 레이어링: 씬 내 복수 비주얼 오버레이

**진행 상태 표시**: AI 처리 진행 인디케이터
- 텍스트 -> 스토리보드 변환 시 진행 표시

**온보딩**: 2스텝 (입력 방식 선택 -> 텍스트 입력)
- 4가지 입력 방식: 스크립트, 블로그, URL, 프롬프트

**에러 처리**: 상세 불명

**특징적 UX 패턴**:
- Unified Pipeline: 텍스트 -> 이미지 -> 캐릭터 일관성 -> 영상 통합
- AI 씬 유형 자동 분류 (Smart Layouts)
- 드래그앤드롭 스토리보드
- Zapier/Make.com 통합으로 자동화 워크플로우

---

### 1.9 Runway ML — AI 영상 생성

**카테고리**: 생성형 AI 영상 (텍스트/이미지 -> 비디오)

**핵심 워크플로우**: Prompt/Image Input -> Gen-4.5 -> 편집/합성 -> Export
- Text-to-Video, Image-to-Video, Video-to-Video 지원
- 노드 기반 Workflows 시스템 (2025.10 출시)
- Aleph (인비디오 오브젝트 조작), Act-Two (모션 캡처)

**설정 패널**: **노드 기반 워크플로우 에디터** (핵심 차별점)
- Input Nodes: 미디어 업로드/텍스트 입력
- Media Model Nodes: Gen-4, Gen-4 Turbo, Flash 2.5, Veo 3.1
- LLM Nodes: 프롬프트 정제/분석
- 색상 코딩: 텍스트(주황), 이미지(핑크), 비디오(초록)
- 우클릭 또는 + 버튼으로 노드 추가

**진행 상태 표시**: Active Runs 패널
- 우측 Active Runs 메뉴: 병렬 실행 노드 진행 상황 추적
- 개별 노드/전체 워크플로우 실행 모드 분리
- 노드별 캔슬 가능

**온보딩**: 2스텝 (프롬프트 입력 -> 생성)
- 심플 모드: 단일 프롬프트 생성
- 워크플로우 모드: 노드 기반 파이프라인 구축 (고급)

**에러 처리**: 노드별 독립 에러 처리
- 실패한 노드만 재실행 (전체 워크플로우 재시작 불필요)

**특징적 UX 패턴**:
- 노드 기반 비주얼 프로그래밍 (코딩 없는 파이프라인)
- 워크플로우 템플릿 저장/재사용
- 개별 노드 테스트 vs 전체 실행 분리
- 키프레이밍 + 카메라 가이던스 컨트롤

---

### 1.10 HeyGen — AI 아바타 영상

**카테고리**: AI 아바타 기반 영상 제작

**핵심 워크플로우**: Script 작성 -> Avatar 선택 -> 배경 설정 -> 생성
- 스크립트 기반 아바타 영상 생성
- Avatar IV: 사진 1장으로 아바타 생성
- 자연스러운 제스처, 표정, 톤

**대본 생성 UX**: **스크립트 패널 중심 (폼 기반)**
- 좌측 스크립트 패널: 씬 기반 스크립트 편집
- 중앙 캔버스: 아바타 + 배경 실시간 프리뷰
- AI 모놀로그 옵션: 프롬프트로 스크립트 자동 생성

**설정 패널**: 우측 Properties 패널 (통합)
- 아바타 선택/교체 (아바타 라이브러리)
- 음성 설정: 악센트, 톤, 속도, 음성 모델, 음성 엔진
- 배경 설정: 제거/단색/스톡/업로드/AI 생성
- "Max Quality" vs "Faster" 모드 선택

**진행 상태 표시**: 생성 모드 선택 가능
- Max Quality: 더 상세한 결과 (느림)
- Faster: 빠른 턴어라운드 (빠름)

**온보딩**: 3스텝 (Create -> 모드 선택 -> 스크립트)
- 좌측 메뉴 "Create" -> "Create a Video"
- 5가지 시작 옵션: Scratch, Photo-to-Video, Template, PPT/PDF, Video Agent
- Landscape/Portrait 선택

**에러 처리**: 상세 불명

**특징적 UX 패턴**:
- 3패널 레이아웃: 스크립트(좌) + 캔버스(중) + 속성(우)
- Studio 내에서 아바타 외모 생성 (별도 탭 전환 불필요)
- 통합 Properties 패널 (기존 More Options 메뉴 대체)

---

## 2. 패턴별 비교 분석

### 2.1 대본/스크립트 생성 UX

| 패턴 | 도구 | 장점 | 단점 |
|------|------|------|------|
| **채팅 기반** | InVideo AI | 진입 장벽 극히 낮음, 자연어로 수정 가능 | 정밀 제어 어려움, 결과 예측성 낮음 |
| **폼 기반** | HeyGen, Pictory | 구조화된 입력, 결과 예측 가능 | 자유도 제한, 학습 곡선 |
| **텍스트 에디터 기반** | Descript, Submagic | 친숙한 문서 편집 UX, 정밀 제어 | 기존 영상 필요 (새 생성 X) |
| **위자드 (단계별)** | Fliki | 명확한 진행 감각, 빠뜨림 방지 | 유연성 부족, 되돌아가기 번거로움 |
| **프롬프트 기반** | Runway ML | 고급 사용자에게 최대 자유도 | 프롬프트 엔지니어링 필요 |
| **하이브리드** | OpusClip, CapCut | 템플릿 + 커스텀 조합 | 복잡도 증가 가능 |

**Shorts Producer 시사점**:
- 현재 Studio는 폼 기반에 가까움 (설정 -> 생성 -> 편집)
- InVideo AI 스타일의 채팅 기반 수정 기능 도입 검토 가치 있음
- Fliki 스타일 위자드를 온보딩 전용으로 활용하는 하이브리드 접근 권장

---

### 2.2 설정 패널 위치

| 패턴 | 도구 | 설명 |
|------|------|------|
| **우측 사이드바 (Properties)** | HeyGen, Pictory, CapCut | 씬/요소 선택 시 우측에 속성 패널 표시 |
| **인라인 (업로드 직후)** | OpusClip, Submagic | 업로드와 동시에 설정 옵션 노출 |
| **좌측 사이드바** | Fliki | 음성 목록, 내비게이션 |
| **노드별 내장** | Runway ML | 각 노드가 자체 설정 메뉴 보유 |
| **채팅 인터페이스** | InVideo AI | 설정 패널 없이 대화로 모든 설정 변경 |
| **멀티모드** | Descript | 스크립트/캔버스/타임라인 뷰 전환 |

**가장 일반적 패턴**: 우측 Properties 패널 (3/10 도구)

**Shorts Producer 시사점**:
- 현재 우측 사이드바 패턴과 업계 표준 부합
- 씬 선택 시 우측 패널에 해당 씬 설정을 표시하는 HeyGen/Pictory 패턴 참고
- 시리즈 설정 등 글로벌 설정은 좌측 또는 상단에 별도 배치 권장

---

### 2.3 진행 상태 표시

| 패턴 | 도구 | 구현 방식 |
|------|------|----------|
| **단계별 텍스트 메시지** | InVideo AI | "Replacing the cat" -> "Done 1/1" |
| **글로벌 프로그레스 바 + 마커** | Descript | 드래그 가능, 챕터/코멘트 마커 표시 |
| **Active Runs 패널** | Runway ML | 우측 패널에서 병렬 실행 노드별 추적 |
| **Virality Score** | OpusClip | 결과물 품질 점수로 진행 상태 대체 |
| **사이드바 진행 인디케이터** | Descript (번역) | 번역 진행 시 섹션별 상태 표시 |
| **모드 선택 (속도/품질)** | HeyGen | 사전에 속도-품질 트레이드오프 선택 |

**업계 트렌드**:
- 단순 스피너/프로그레스 바를 넘어 "지금 무엇을 하고 있는지" 텍스트 설명 제공
- 멀티 스테이지 파이프라인은 각 단계를 개별 표시
- 취소 가능성 (Runway ML의 개별 노드 캔슬)

**Shorts Producer 시사점**:
- 현재 LangGraph 17-노드 파이프라인의 진행 상황을 InVideo AI 스타일 단계별 메시지로 표시 권장
- "Director 분석 중..." -> "Writer 스크립트 작성 중..." -> "이미지 생성 중 (3/8)..." 등
- Runway ML처럼 각 단계별 취소/재시도 기능 검토

---

### 2.4 온보딩 경험 (첫 영상까지 스텝 수)

| 도구 | 스텝 수 | 시작 방식 | 핵심 전략 |
|------|---------|----------|----------|
| **InVideo AI** | 1 | 프롬프트 입력 | 프롬프트 하나로 완성 영상 |
| **Submagic** | 1 | 영상 업로드 | 3-click philosophy |
| **OpusClip** | 2 | URL 붙여넣기 | 데모 옵션 3개 제공 |
| **Fliki** | 2 | 질문 2개 | 맞춤형 온보딩 |
| **CapCut** | 2 | 템플릿 선택 | 방대한 템플릿 |
| **Runway ML** | 2 | 프롬프트 입력 | 심플/고급 모드 분리 |
| **Pictory** | 2 | 입력 방식 선택 | 4가지 입력 포맷 |
| **Descript** | 3 | 영상 Import | 6-step 튜토리얼 |
| **HeyGen** | 3 | 모드 선택 | 5가지 시작 옵션 |
| **Vizard** | 3 | 영상 업로드 | 협업 도구 + 튜토리얼 |

**업계 트렌드**: 2스텝 이하가 대세 (6/10 도구)

**Shorts Producer 시사점**:
- 현재 Studio 진입 -> 시리즈 선택 -> 설정 -> 생성은 4+ 스텝
- "Quick Start" 모드 도입 고려: 주제 입력 -> 시리즈 자동 선택 -> 즉시 생성
- 기존 시리즈가 있는 경우 "이전 설정으로 새 영상 만들기" 원클릭 옵션

---

### 2.5 에러 표시 패턴

| 패턴 | 사용 도구 | 적합한 상황 |
|------|----------|------------|
| **인라인 채팅 응답** | InVideo AI | 비치명적 에러, 대안 제시 |
| **자동 재시도 + 상태 표시** | Descript | 네트워크 에러, 업로드 실패 |
| **노드별 에러 표시** | Runway ML | 파이프라인 특정 단계 실패 |
| **파일 포맷 사전 검증** | OpusClip | 업로드 전 포맷/크기 안내 |
| **진행 인디케이터 내 에러** | Descript (번역) | 비동기 작업 중 에러 |

**업계 Best Practice (종합)**:
- Toast는 성공 알림에만 사용, 에러는 배너/인라인으로 표시
- 에러 메시지에 해결 방법 포함 (단순 "실패" X)
- 사전 검증으로 에러 자체를 방지 (포맷/크기/길이 사전 안내)
- 자동 재시도 메커니즘 (네트워크 에러 등 일시적 문제)
- Dismiss 가능하되, 해결 필요한 에러는 persist

**Shorts Producer 시사점**:
- AI 파이프라인 에러는 Runway ML 스타일 노드별 에러 표시 적합
- SD WebUI 연결 실패 등은 상단 배너 (persist, dismiss 불가)
- 이미지 생성 실패는 해당 씬 카드에 인라인 에러 + 재시도 버튼

---

## 3. 핵심 트렌드 요약

### 3.1 AI-First Workflow
- 수동 편집 -> AI 자동화 + 사용자 수정으로 패러다임 전환
- InVideo AI/Runway ML: "AI가 먼저 만들고, 사용자가 다듬는다"
- Descript/Submagic: "텍스트가 곧 편집 인터페이스"

### 3.2 멀티 입력 포맷
- 대부분의 도구가 3가지 이상 입력 방식 지원
- 텍스트, URL, 파일, 프롬프트, PPT 등
- Shorts Producer: 현재 스크립트(텍스트) 중심 -> URL/주제 기반 자동 생성 확장 가능

### 3.3 실시간 프리뷰 + 즉시 수정
- HeyGen: 중앙 캔버스에서 아바타 실시간 프리뷰
- Pictory: 스토리보드 -> 에디터 전환 없이 인라인 편집
- Shorts Producer: 씬 카드에서 이미지 프리뷰 + 인라인 수정 기능 강화 필요

### 3.4 노드/파이프라인 시각화 (고급 사용자용)
- Runway ML Workflows: 노드 기반 파이프라인 구축
- Shorts Producer의 LangGraph 17-노드 파이프라인과 유사한 개념
- 고급 모드에서 파이프라인 시각화 제공 검토 가치

### 3.5 품질 점수화
- OpusClip: Virality Score
- Shorts Producer: 이미 Match Rate 존재 -> "품질 대시보드" 형태로 UX 강화 가능

---

## 4. Shorts Producer 적용 권장사항

### 즉시 적용 가능 (Quick Win)

| 영역 | 현재 | 제안 | 참고 도구 |
|------|------|------|----------|
| 파이프라인 진행 표시 | 스피너 | 단계별 텍스트 메시지 + 프로그레스 바 | InVideo AI, Runway ML |
| 에러 메시지 | Toast 기반 | 씬별 인라인 에러 + 재시도 버튼 | Runway ML |
| 온보딩 | 없음 | 2-step Quick Start (주제 -> 생성) | Fliki, InVideo AI |
| 씬 설정 | 별도 모달 | 우측 Properties 패널 (씬 선택 연동) | HeyGen, Pictory |

### 중기 개선 (1-2개월)

| 영역 | 제안 | 참고 도구 |
|------|------|----------|
| AI 어시스턴트 | 채팅 기반 스크립트 수정 기능 | InVideo AI |
| Smart Layout | AI 씬 유형 자동 분류 | Pictory |
| 품질 대시보드 | Match Rate + Virality 유사 점수 통합 | OpusClip |
| 템플릿 시스템 | 시리즈별 기본 템플릿 프리셋 | CapCut |

### 장기 비전 (3개월+)

| 영역 | 제안 | 참고 도구 |
|------|------|----------|
| 파이프라인 시각화 | LangGraph 노드 기반 에디터 | Runway ML Workflows |
| 텍스트 기반 편집 | 스크립트 편집 = 영상 편집 | Descript |
| 멀티 입력 | URL/블로그 -> 자동 영상 | Pictory, Fliki |
| 실시간 협업 | 팀 워크스페이스 | Descript, Vizard |

---

## Sources

- [OpusClip](https://www.opus.pro/)
- [OpusClip Review 2025](https://www.podcastvideos.com/articles/opus-clip-review-2025-ai-video-repurposing/)
- [OpusClip Review 2026](https://filmora.wondershare.com/video-editor-review/opusclip-ai.html)
- [Submagic](https://www.submagic.co)
- [SubMagic Review 2025](https://max-productive.ai/ai-tools/submagic/)
- [Vizard.ai](https://vizard.ai/)
- [Vizard Review 2025](https://quso.ai/blog/vizard-ai-review)
- [InVideo AI](https://invideo.io)
- [InVideo AI Review 2026](https://max-productive.ai/ai-tools/invideo-ai/)
- [Descript](https://www.descript.com/video-editing)
- [Descript Review 2025](https://fritz.ai/descript-ai-review/)
- [Descript Progress Bars](https://help.descript.com/hc/en-us/articles/10256392416141-Progress-bars)
- [CapCut](https://www.capcut.com/)
- [CapCut UI Review](https://cardsrealm.com/en-us/articles/reviewing-capcuts-user-interface-intuitive-design-for-seamless-editing)
- [Fliki](https://fliki.ai/)
- [Fliki Review 2026](https://max-productive.ai/ai-tools/fliki/)
- [Fliki Idea to Video](https://fliki.ai/features/idea-to-video)
- [Pictory](https://pictory.ai/)
- [Pictory Scene Settings](https://kb.pictory.ai/en/articles/8468832-how-to-adjust-scene-settings-on-the-script-page)
- [Pictory 2026 Unified Pipeline](https://blockchain.news/ainews/pictory-launches-unified-ai-video-workflow-custom-visuals-consistent-characters-and-prompt-to-video-2026-analysis)
- [Runway ML](https://runwayml.com/)
- [Runway ML Workflows](https://runwayml.com/workflows)
- [Runway Workflows Guide](https://help.runwayml.com/hc/en-us/articles/45763528999699-Introduction-to-Workflows)
- [HeyGen](https://www.heygen.com/)
- [HeyGen AI Studio](https://www.heygen.com/blog/how-to-edit-ai-videos-faster-with-ai-studio)
- [HeyGen Script Panel](https://help.heygen.com/en/articles/11381771-how-to-write-scripts-in-the-ai-studio)
- [HeyGen Getting Started](https://help.heygen.com/en/articles/11049837-create-your-first-video-in-our-studio)
