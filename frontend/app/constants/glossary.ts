export const GLOSSARY = {
  controlnet: "포즈/구도를 참조 이미지에서 추출해 동일한 자세로 생성합니다.",
  "ip-adapter": "참조 이미지의 스타일/외형을 새 이미지에 반영합니다.",
  steps: "노이즈 제거 반복 횟수. 높을수록 정밀하지만 느려집니다.",
  "cfg-scale": "프롬프트 반영 강도. 높으면 충실하지만 부자연스러울 수 있습니다.",
  sampler: "이미지 생성 알고리즘. DPM++ 2M Karras가 범용적입니다.",
  "clip-skip": "텍스트 인코더 레이어 건너뛰기. 애니메이션 스타일은 2 권장.",
  checkpoint: "이미지 생성 베이스 모델. 화풍과 품질을 결정합니다.",
  "hi-res": "저해상도로 구도 잡은 뒤 고해상도로 업스케일합니다.",
  lora: "소량 학습된 보조 모델. 특정 캐릭터/스타일을 재현합니다.",
  "ken-burns": "정지 이미지에 줌/팬 모션을 적용해 영상감을 더합니다.",
} as const;

export type GlossaryTerm = keyof typeof GLOSSARY;
