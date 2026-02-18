import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  CinematographerSection,
  TtsDesignerSection,
  SoundDesignerSection,
  CopyrightReviewerSection,
} from "../ProductionSections";
import { renderSectionContent } from "../ReasoningSections";

describe("CinematographerSection", () => {
  it("씬 수 + 도구 호출 수 표시", () => {
    render(
      <CinematographerSection
        data={{
          result: {
            scenes: [
              { order: 1, camera: "close-up", environment: "kitchen", image_prompt: "1girl" },
              { order: 2, camera: "medium_shot", environment: "park" },
            ],
          },
          tool_logs: [{ tool: "validate" }, { tool: "lookup" }],
        }}
      />,
    );
    expect(screen.getByText(/2개 씬 시각 설계 완료/)).toBeTruthy();
    expect(screen.getByText(/2회 도구 호출/)).toBeTruthy();
  });

  it("카메라 + 환경 태그 표시", () => {
    render(
      <CinematographerSection
        data={{
          result: { scenes: [{ order: 1, camera: "cowboy_shot", environment: "street" }] },
          tool_logs: [],
        }}
      />,
    );
    expect(screen.getByText("cowboy_shot")).toBeTruthy();
    expect(screen.getByText("street")).toBeTruthy();
  });

  it("빈 씬일 때 fallback 표시", () => {
    render(<CinematographerSection data={{ result: { scenes: [] }, tool_logs: [] }} />);
    expect(screen.getByText("시각 설계 데이터 없음")).toBeTruthy();
  });
});

describe("TtsDesignerSection", () => {
  it("음성 설계 수 + voice prompt 표시", () => {
    render(
      <TtsDesignerSection
        data={{
          tts_designs: [
            {
              scene_id: 1,
              voice_design_prompt: "Excited, cheerful tone",
              pacing: { head_padding: 0.2, tail_padding: 0.5 },
            },
          ],
        }}
      />,
    );
    expect(screen.getByText(/1개 씬 음성 설계/)).toBeTruthy();
    expect(screen.getByText("Excited, cheerful tone")).toBeTruthy();
    expect(screen.getByText(/pad: 0.2s \/ 0.5s/)).toBeTruthy();
  });

  it("빈 designs일 때 fallback 표시", () => {
    render(<TtsDesignerSection data={{ tts_designs: [] }} />);
    expect(screen.getByText("음성 설계 데이터 없음")).toBeTruthy();
  });
});

describe("SoundDesignerSection", () => {
  it("mood + prompt + reasoning 표시", () => {
    render(
      <SoundDesignerSection
        data={{
          recommendation: {
            prompt: "Gentle acoustic guitar",
            mood: "melancholic",
            duration: 30,
            reasoning: "감정 곡선 분석 결과",
          },
        }}
      />,
    );
    expect(screen.getByText("melancholic")).toBeTruthy();
    expect(screen.getByText("30초")).toBeTruthy();
    expect(screen.getByText("Gentle acoustic guitar")).toBeTruthy();
    expect(screen.getByText("감정 곡선 분석 결과")).toBeTruthy();
  });

  it("빈 추천일 때 fallback 표시", () => {
    render(<SoundDesignerSection data={{ recommendation: { prompt: "", mood: "" } }} />);
    expect(screen.getByText("BGM 추천 데이터 없음")).toBeTruthy();
  });
});

describe("CopyrightReviewerSection", () => {
  it("PASS 상태 + 신뢰도 표시", () => {
    render(
      <CopyrightReviewerSection
        data={{
          overall: "PASS",
          confidence: 0.85,
          checks: [
            { type: "script_originality", status: "PASS", detail: null, suggestion: null },
            { type: "character_ip", status: "PASS", detail: null, suggestion: null },
          ],
        }}
      />,
    );
    expect(screen.getAllByText("PASS")).toHaveLength(3); // overall + 2 checks
    expect(screen.getByText("신뢰도 85%")).toBeTruthy();
    expect(screen.getByText("script originality")).toBeTruthy();
    expect(screen.getByText("character ip")).toBeTruthy();
  });

  it("WARN 상태 + suggestion 표시", () => {
    render(
      <CopyrightReviewerSection
        data={{
          overall: "WARN",
          confidence: 0.6,
          checks: [
            {
              type: "story_structure",
              status: "WARN",
              detail: "유사한 구조 감지",
              suggestion: "독창적 요소 추가 권장",
            },
          ],
        }}
      />,
    );
    expect(screen.getAllByText("WARN")).toHaveLength(2); // overall + check
    expect(screen.getByText("유사한 구조 감지")).toBeTruthy();
    expect(screen.getByText("독창적 요소 추가 권장")).toBeTruthy();
  });
});

describe("renderSectionContent", () => {
  it("4개 프로덕션 노드 모두 렌더러 등록됨", () => {
    for (const id of ["cinematographer", "tts_designer", "sound_designer", "copyright_reviewer"]) {
      const result = renderSectionContent(id, { result: { scenes: [] }, tts_designs: [] });
      expect(result).not.toBeNull();
    }
  });

  it("미등록 id는 null 반환", () => {
    expect(renderSectionContent("unknown_node", {})).toBeNull();
  });
});
