/**
 * QA Patrol 순찰 설정
 *
 * 페이지 개편 시 이 파일만 수정하면 됩니다.
 * 테스트 로직(qa-patrol.spec.ts)은 변경 불필요.
 */

export const PATROL_TIMEOUT = 15000;

// ── 순찰 대상 페이지 (Extended + Random에서 사용) ──
export interface PatrolPage {
  name: string;
  path: string;
  /** CSS 셀렉터 — 페이지 로드 확인용 */
  selector: string;
}

export const PATROL_PAGES: PatrolPage[] = [
  { name: "홈", path: "/", selector: "h1, h2" },
  { name: "Studio 칸반", path: "/studio", selector: "h1, h2, button" },
  { name: "새 영상", path: "/studio?new=true", selector: "button" },
  { name: "Settings", path: "/settings", selector: "a" },
  { name: "Library", path: "/library", selector: "h1, h2" },
  { name: "Characters", path: "/library/characters", selector: "h1, h2, [data-testid]" },
  { name: "Voices", path: "/library/voices", selector: "h1, h2" },
  { name: "Styles", path: "/library/styles", selector: "h1, h2" },
  { name: "LoRA", path: "/library/loras", selector: "h1, h2" },
  { name: "Scripts", path: "/scripts", selector: "h1, h2" },
  { name: "Storyboards", path: "/storyboards", selector: "h1, h2" },
];

// ── Core 순찰 (고정 4개) — 각 페이지별 세부 검증 ──
export const CORE_CHECKS = {
  home: {
    path: "/",
    navLinks: [/홈/i, /스튜디오/i],
    contentSelector: "h1, h2",
  },
  studio: {
    path: "/studio",
    contentTexts: ["영상 목록", "채널이 필요합니다", "시리즈를 만들어야"],
  },
  newVideo: {
    path: "/studio?new=true",
    buttons: [
      { name: "채널", exact: false },
      { name: /시리즈/, exact: false },
      { name: "대본", exact: true },
    ],
  },
  settings: {
    path: "/settings",
    links: [/렌더 설정/i, /연동/i],
  },
} as const;

// ── Extended 순찰 — 개별 페이지 셀렉터 오버라이드 ──
export interface ExtendedCheck {
  name: string;
  path: string;
  selector: string;
  /** 셀렉터 외 추가 텍스트 매치 (or 조건) */
  fallbackTexts?: string[];
}

export const EXTENDED_CHECKS: ExtendedCheck[] = [
  { name: "Library 메인", path: "/library", selector: "h1, h2" },
  { name: "Characters 목록", path: "/library/characters", selector: "h1, h2, [data-testid]" },
  { name: "Voices 목록", path: "/library/voices", selector: "h1, h2" },
  {
    name: "Styles 목록",
    path: "/library/styles",
    selector: "h1, h2",
    fallbackTexts: ["Style Profiles"],
  },
  { name: "LoRA 목록", path: "/library/loras", selector: "h1, h2" },
  { name: "Scripts 페이지", path: "/scripts", selector: "h1, h2" },
  { name: "Storyboards 목록", path: "/storyboards", selector: "h1, h2" },
];

// ── Studio 탭 전환 순찰 ──
export const STUDIO_TABS = ["대본", "준비", "이미지", "게시"];
