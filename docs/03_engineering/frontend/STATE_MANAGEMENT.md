# Frontend State Management

## Abstract
본 문서는 Shorts Producer 프론트엔드(Next.js)의 상태 관리 전략을 설명합니다. 주로 Zustand를 이용한 전역 데이터 흐름과 커스텀 훅을 통한 서버 데이터 연동 방식을 다룹니다.

## 1. 전역 상태 관리 (Zustand)
애플리케이션의 핵심 도메인 상태는 `app/store` 하위의 모듈화된 Zustand Store로 관리됩니다.

### Modular Store Structure (`useStudioStore`)
-   **`planSlice`**: 전략적 설정 (Character, Style Profile, LoRA 가중치 등).
-   **`scenesSlice`**: 현재 작업 중인 스토리보드의 모든 씬 데이터 및 편집 상태.
-   **`metaSlice`**: UI 상태 (Tab 선택, Modal 열림 여부, 전역 로딩 상태 등).
-   **`outputSlice`**: 렌더링 결과물 링크 및 로컬 히스토리.
-   **`profileSlice`**: 화풍 및 모델 설정 프로필 관리.

### Persistence
-   `persist` 미들웨어를 사용하여 `localStorage`에 자동 저장되며, 페이지 새로고침 후에도 작업 상태가 유지됩니다 (`useDraftPersistence` 훅 연동).

## 2. 서버 데이터 연동 (Custom Hooks & Axios)
React Query 대신, 도메인별 커스텀 훅을 통해 `axios`로 데이터를 페칭하고 로컬 상태(`useState`)로 관리하는 패턴을 사용합니다.

-   **`useTags`**: 태그 목록 조회 및 그룹화.
-   **`useCharacters`**: 캐릭터 목록 및 선택 관리.
-   **`useAutopilot`**: 복합적인 생성 시퀀스(Compose -> Generate -> Validate)의 워크플로우 제어.

## 3. 데이터 흐름 패턴
1.  **Backend Fetch**: 커스텀 훅에서 API 호출.
2.  **Global Sync**: 로드된 데이터 중 영속화가 필요한 핵심 정보(예: 선택된 캐릭터 ID)를 Zustand Store에 저장.
3.  **Action Dispatch**: 사용자의 입력은 `app/store/actions` 폴더의 비동기 액션을 통해 Backend 요청과 Store 업데이트를 동시에 처리.
