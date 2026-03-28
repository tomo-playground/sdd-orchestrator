import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ScenePropertyPanel from "../ScenePropertyPanel";
import { SceneProvider } from "../SceneContext";
import type { SceneContextValue } from "../SceneContext";
import type { Scene } from "../../../types";

// ── Mock child components ──────────────────────────────────────

vi.mock("../ScenePromptFields", () => ({
  default: () => <div data-testid="scene-prompt-fields" />,
}));
vi.mock("../SceneEnvironmentPicker", () => ({
  default: () => <div data-testid="scene-environment-picker" />,
}));
vi.mock("../SceneSettingsFields", () => ({
  default: () => <div data-testid="scene-settings-fields" />,
}));
vi.mock("../../studio/SceneToolsContent", () => ({
  default: () => <div data-testid="scene-tools-content" />,
}));
vi.mock("../../ui/Button", () => ({
  default: ({ children, ...props }: { children: React.ReactNode } & Record<string, unknown>) => (
    <button {...props}>{children}</button>
  ),
}));

// ── Mock UIStore ───────────────────────────────────────────────

let mockShowAdvanced = false;
vi.mock("../../../store/useUIStore", () => ({
  useUIStore: (selector: (s: { showAdvancedSettings: boolean }) => unknown) =>
    selector({ showAdvancedSettings: mockShowAdvanced }),
}));

// ── Helpers ────────────────────────────────────────────────────

const MOCK_SCENE: Scene = {
  id: 1,
  client_id: "test-1",
  order: 1,
  script: "Test script",
  speaker: "Narrator",
  duration: 3,
  image_prompt: "test prompt",
  image_prompt_ko: "테스트 프롬프트",
  image_url: null,
  negative_prompt: "",
  isGenerating: false,
  debug_payload: "",
};

function makeCtxValue(overrides?: {
  data?: Partial<SceneContextValue["data"]>;
  callbacks?: Partial<SceneContextValue["callbacks"]>;
}): SceneContextValue {
  return {
    data: {
      scene: MOCK_SCENE,
      loraTriggerWords: [],
      characterLoras: [],
      tagsByGroup: {},
      sceneTagGroups: [],
      isExclusiveGroup: () => false,
      basePromptA: "",
      sceneMenuOpen: false,
      sceneIndex: 0,
      isMarkingStatus: false,
      ...overrides?.data,
    },
    callbacks: {
      onUpdateScene: vi.fn(),
      onRemoveScene: vi.fn(),
      onSpeakerChange: vi.fn(),
      onImageUpload: vi.fn(),
      onGenerateImage: vi.fn(),
      onApplyMissingTags: vi.fn(),
      onImagePreview: vi.fn(),
      buildNegativePrompt: vi.fn(() => ""),
      buildScenePrompt: vi.fn(() => ""),
      showToast: vi.fn(),
      onSceneMenuToggle: vi.fn(),
      onSceneMenuClose: vi.fn(),
      ...overrides?.callbacks,
    },
  };
}

function renderPanel(ctxOverrides?: Parameters<typeof makeCtxValue>[0]) {
  const ctx = makeCtxValue(ctxOverrides);
  return render(
    <SceneProvider value={ctx}>
      <ScenePropertyPanel />
    </SceneProvider>
  );
}

// ── Tests ──────────────────────────────────────────────────────

describe("ScenePropertyPanel", () => {
  beforeEach(() => {
    mockShowAdvanced = false;
  });

  // 1. Independent rendering
  it("renders without error inside SceneProvider", () => {
    renderPanel();
    expect(screen.getByText("Customize")).toBeInTheDocument();
  });

  // 2. Basic tab: prompt fields + environment picker present
  it("shows ScenePromptFields and SceneEnvironmentPicker on basic tab", () => {
    renderPanel();
    expect(screen.getByTestId("scene-prompt-fields")).toBeInTheDocument();
    expect(screen.getByTestId("scene-environment-picker")).toBeInTheDocument();
  });

  // 3. Speaker badge shown when speaker exists
  it("shows speaker badge when scene has a speaker", () => {
    renderPanel();
    expect(screen.getByText("Narrator")).toBeInTheDocument();
    expect(screen.getByText("Speaker")).toBeInTheDocument();
  });

  // 4. Advanced tab hidden when showAdvancedSettings is false
  it("hides Advanced tab button when showAdvancedSettings is false", () => {
    mockShowAdvanced = false;
    renderPanel();
    expect(screen.queryByText("Advanced")).not.toBeInTheDocument();
  });

  // 5. Advanced tab appears when showAdvancedSettings is true
  it("shows Advanced tab button when showAdvancedSettings is true", () => {
    mockShowAdvanced = true;
    renderPanel();
    expect(screen.getByText("Advanced")).toBeInTheDocument();
  });

  // 6. Clicking Advanced tab shows SceneToolsContent
  it("shows SceneToolsContent when Advanced tab is clicked", () => {
    mockShowAdvanced = true;
    renderPanel();

    fireEvent.click(screen.getByText("Advanced"));

    expect(screen.getByTestId("scene-tools-content")).toBeInTheDocument();
    expect(screen.getByTestId("scene-settings-fields")).toBeInTheDocument();
    // Basic tab content should be hidden
    expect(screen.queryByTestId("scene-prompt-fields")).not.toBeInTheDocument();
  });

  // 7. Review buttons rendered when activity_log_id exists with callbacks
  it("shows Success/Fail buttons on Advanced tab when activity_log_id is set", () => {
    mockShowAdvanced = true;
    const onMarkSuccess = vi.fn();
    const onMarkFail = vi.fn();
    renderPanel({
      data: { scene: { ...MOCK_SCENE, activity_log_id: 42 } },
      callbacks: { onMarkSuccess, onMarkFail },
    });

    fireEvent.click(screen.getByText("Advanced"));

    expect(screen.getByText("Success")).toBeInTheDocument();
    expect(screen.getByText("Fail")).toBeInTheDocument();
  });

  // 8. Review buttons not rendered when activity_log_id is absent
  it("does not show Success/Fail buttons when activity_log_id is absent", () => {
    mockShowAdvanced = true;
    renderPanel({
      data: { scene: { ...MOCK_SCENE, activity_log_id: undefined } },
      callbacks: { onMarkSuccess: vi.fn(), onMarkFail: vi.fn() },
    });

    fireEvent.click(screen.getByText("Advanced"));

    expect(screen.queryByText("Success")).not.toBeInTheDocument();
    expect(screen.queryByText("Fail")).not.toBeInTheDocument();
  });

  // 9. Context missing → throws
  it("throws when rendered without SceneProvider", () => {
    // Suppress React error boundary output
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => render(<ScenePropertyPanel />)).toThrow(
      "useSceneContext must be used within a SceneProvider"
    );
    spy.mockRestore();
  });
});
