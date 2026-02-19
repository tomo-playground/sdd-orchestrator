/** QC 분석 한국어 레이블 (QCSummaryCard + StepReviewPanel 공용) */

export const RATING_LABELS: Record<string, string> = {
  good: "우수",
  needs_revision: "수정 필요",
  poor: "미흡",
};

export const SEVERITY_LABELS: Record<string, string> = {
  critical: "심각",
  warning: "주의",
  suggestion: "제안",
};

export const CATEGORY_LABELS: Record<string, string> = {
  readability: "가독성",
  hook_strength: "훅 강도",
  emotional_arc: "감정 흐름",
  tts_naturalness: "TTS 자연스러움",
  expression_diversity: "표현 다양성",
  consistency: "일관성",
};
